from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..deps import get_current_user
from ..models.user import UserInDB
from ..schemas.user import (
    UpdateIdentityRequest,
    UpdateNicknameRequest,
    UserResponse,
    user_to_response,
)
from ..services.display_name import resolve_display_name_for_user
from ..services.nickname_tag import allocate_nickname_tag

router = APIRouter(prefix="/users", tags=["用户"])


def _is_admin(user: UserInDB) -> bool:
    return user.role == 1


@router.put(
    "/me/identity",
    response_model=UserResponse,
    summary="更新身份角色",
)
async def update_identity(
    body: UpdateIdentityRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    now = datetime.now(timezone.utc)
    await db["users"].update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"identity_role": body.identity_role, "updated_at": now}},
    )
    current_user.identity_role = body.identity_role
    display_name = await resolve_display_name_for_user(db, current_user)
    return user_to_response(current_user, display_name=display_name)


@router.patch(
    "/me/nickname",
    response_model=UserResponse,
    summary="修改昵称（按新昵称重新分配同名编号）",
)
async def update_nickname(
    body: UpdateNicknameRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    now = datetime.now(timezone.utc)
    new_tag = await allocate_nickname_tag(db, body.nickname)
    await db["users"].update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"nickname": body.nickname, "nickname_tag": new_tag, "updated_at": now}},
    )
    updated = UserInDB.from_doc(
        await db["users"].find_one({"_id": ObjectId(current_user.id)})
    )
    display_name = await resolve_display_name_for_user(db, updated)
    return user_to_response(updated, display_name=display_name)


@router.get("", response_model=list[UserResponse], summary="管理端获取所有用户列表")
async def list_all_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[UserResponse]:
    if not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问")
    cursor = db["users"].find().sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    results: list[UserResponse] = []
    for doc in docs:
        u = UserInDB.from_doc(doc)
        dn = await resolve_display_name_for_user(db, u)
        results.append(user_to_response(u, display_name=dn))
    return results
