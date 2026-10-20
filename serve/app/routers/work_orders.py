from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..deps import get_current_user
from ..models.user import UserInDB
from ..schemas.work_order import (
    CreateWorkOrderReplyRequest,
    CreateWorkOrderRequest,
    WorkOrderReplyResponse,
    WorkOrderResponse,
)

router = APIRouter(prefix="/work-orders", tags=["工单"])


def _is_admin(user: UserInDB) -> bool:
    return user.role == 1


def _format_order_doc(doc: dict) -> WorkOrderResponse:
    return WorkOrderResponse(
        work_order_id=str(doc["_id"]),
        user_id=doc["user_id"],
        user_display_name=doc.get("user_display_name", "用户"),
        subject=doc["subject"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        last_reply_by=doc["last_reply_by"],
        latest_reply_preview=doc.get("latest_reply_preview", ""),
        latest_reply_at=doc.get("latest_reply_at", doc["updated_at"]),
    )


@router.get("/me", response_model=dict, summary="获取当前用户工单页数据")
async def get_my_work_orders(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    is_admin = _is_admin(current_user)
    mine_cursor = (
        db["work_orders"]
        .find({"user_id": current_user.id})
        .sort("updated_at", -1)
        .limit(100)
    )
    mine_docs = await mine_cursor.to_list(length=100)
    mine = [_format_order_doc(d) for d in mine_docs]

    if not is_admin:
        return {"is_admin": False, "mine": mine, "pending": [], "processed": []}

    admin_cursor = db["work_orders"].find({}).sort("updated_at", -1).limit(300)
    admin_docs = await admin_cursor.to_list(length=300)
    pending: list[WorkOrderResponse] = []
    processed: list[WorkOrderResponse] = []
    for d in admin_docs:
        item = _format_order_doc(d)
        if item.last_reply_by == "user":
            pending.append(item)
        else:
            processed.append(item)

    return {
        "is_admin": True,
        "mine": mine,
        "pending": pending,
        "processed": processed,
    }


@router.post(
    "",
    response_model=WorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建工单",
)
async def create_work_order(
    body: CreateWorkOrderRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> WorkOrderResponse:
    now = datetime.now(timezone.utc)
    subject = body.subject.strip()
    content = body.content.strip()
    if not subject:
        raise HTTPException(status_code=400, detail="工单主题不能为空")
    if not content:
        raise HTTPException(status_code=400, detail="工单内容不能为空")

    order_doc = {
        "user_id": current_user.id,
        "user_display_name": current_user.display_name,
        "subject": subject,
        "created_at": now,
        "updated_at": now,
        "last_reply_by": "user",
        "latest_reply_preview": content[:80],
        "latest_reply_at": now,
    }
    order_result = await db["work_orders"].insert_one(order_doc)
    work_order_id = str(order_result.inserted_id)

    reply_doc = {
        "work_order_id": work_order_id,
        "sender_role": "user",
        "sender_user_id": current_user.id,
        "sender_display_name": current_user.display_name,
        "content": content,
        "created_at": now,
    }
    await db["work_order_replies"].insert_one(reply_doc)
    order_doc["_id"] = order_result.inserted_id
    return _format_order_doc(order_doc)


@router.get("/{work_order_id}/replies", response_model=list[WorkOrderReplyResponse], summary="获取工单回复")
async def list_work_order_replies(
    work_order_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[WorkOrderReplyResponse]:
    try:
        oid = ObjectId(work_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="工单 ID 格式错误")

    doc = await db["work_orders"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="工单不存在")

    if (not _is_admin(current_user)) and doc["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该工单")

    cursor = db["work_order_replies"].find({"work_order_id": work_order_id}).sort("created_at", 1)
    replies = await cursor.to_list(length=500)
    return [
        WorkOrderReplyResponse(
            reply_id=str(r["_id"]),
            work_order_id=r["work_order_id"],
            sender_role=r["sender_role"],
            sender_user_id=r["sender_user_id"],
            sender_display_name=r.get("sender_display_name", "用户"),
            content=r["content"],
            created_at=r["created_at"],
        )
        for r in replies
    ]


@router.post("/{work_order_id}/replies", response_model=WorkOrderReplyResponse, summary="回复工单")
async def create_work_order_reply(
    work_order_id: str,
    body: CreateWorkOrderReplyRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> WorkOrderReplyResponse:
    try:
        oid = ObjectId(work_order_id)
    except Exception:
        raise HTTPException(status_code=400, detail="工单 ID 格式错误")

    doc = await db["work_orders"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="工单不存在")

    is_admin = _is_admin(current_user)
    if (not is_admin) and doc["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="无权回复该工单")

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="回复内容不能为空")

    now = datetime.now(timezone.utc)
    sender_role = "admin" if is_admin else "user"
    reply_doc = {
        "work_order_id": work_order_id,
        "sender_role": sender_role,
        "sender_user_id": current_user.id,
        "sender_display_name": current_user.display_name,
        "content": content,
        "created_at": now,
    }
    result = await db["work_order_replies"].insert_one(reply_doc)

    await db["work_orders"].update_one(
        {"_id": oid},
        {
            "$set": {
                "updated_at": now,
                "last_reply_by": sender_role,
                "latest_reply_preview": content[:80],
                "latest_reply_at": now,
            }
        },
    )

    return WorkOrderReplyResponse(
        reply_id=str(result.inserted_id),
        work_order_id=work_order_id,
        sender_role=sender_role,
        sender_user_id=current_user.id,
        sender_display_name=current_user.display_name,
        content=content,
        created_at=now,
    )
