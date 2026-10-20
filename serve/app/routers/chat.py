"""小组实时聊天（WebSocket + 历史消息）。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import decode_access_token
from ..deps import get_current_user
from ..models.user import UserInDB, format_display_name
from ..services.team_chat_read import mark_team_read

logger = logging.getLogger("lulemo.chat")

router = APIRouter(prefix="/teams", tags=["小组聊天"])


# ─── 连接管理 ────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, team_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms.setdefault(team_id, []).append(ws)

    def disconnect(self, team_id: str, ws: WebSocket) -> None:
        room = self._rooms.get(team_id, [])
        if ws in room:
            room.remove(ws)
        if not room:
            self._rooms.pop(team_id, None)

    async def broadcast(self, team_id: str, payload: dict) -> None:
        text = json.dumps(payload, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in list(self._rooms.get(team_id, [])):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(team_id, ws)


manager = ConnectionManager()


# ─── 工具 ────────────────────────────────────────────────────────────────────

def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except InvalidId as exc:
        raise HTTPException(status_code=400, detail="team_id 无效") from exc


async def _assert_member(db: AsyncIOMotorDatabase, team_id: str, user_id: str) -> None:
    """验证用户是小组成员，否则抛 403。"""
    exists = await db["team_members"].count_documents(
        {"team_id": team_id, "user_id": user_id}
    )
    if not exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是该小组成员")


def _serialize_msg(doc: dict) -> dict:
    created_at = doc.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    return {
        "type": "message",
        "message_id": str(doc["_id"]),
        "team_id": doc["team_id"],
        "user_id": doc["user_id"],
        "display_name": doc.get("display_name", ""),
        "content": doc["content"],
        "created_at": created_at,
    }


# ─── REST：历史消息 ──────────────────────────────────────────────────────────

@router.get("/{team_id}/messages")
async def get_messages(
    team_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None, description="ISO 时间戳，只返回早于此时间的消息"),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    _oid(team_id)
    await _assert_member(db, team_id, current_user.id)

    filters: dict = {"team_id": team_id}
    if before:
        try:
            before_dt = datetime.fromisoformat(before)
        except ValueError:
            raise HTTPException(status_code=400, detail="before 参数格式无效，需为 ISO 8601 时间戳")
        filters["created_at"] = {"$lt": before_dt}

    cursor = (
        db["team_messages"]
        .find(filters)
        .sort("created_at", -1)
        .limit(limit + 1)  # 多取一条用于判断 has_more
    )
    docs = await cursor.to_list(length=limit + 1)
    has_more = len(docs) > limit
    if has_more:
        docs.pop()

    docs.reverse()
    return {
        "messages": [_serialize_msg(d) for d in docs],
        "has_more": has_more,
    }


@router.post("/{team_id}/messages/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_messages_read(
    team_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """将进入聊天室或主动刷新时，标记该小组消息为已读。"""
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")
    _oid(team_id)
    await _assert_member(db, team_id, current_user.id)
    await mark_team_read(db, team_id, current_user.id)


# ─── WebSocket：实时聊天 ──────────────────────────────────────────────────────

@router.websocket("/{team_id}/ws")
async def team_chat_ws(
    team_id: str,
    websocket: WebSocket,
    token: str = Query(default=""),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info("WebSocket 连接请求 | team=%s | ip=%s | token=%s", team_id, client_ip, "有" if token else "无")

    # 1. 验证 token
    user_id = decode_access_token(token) if token else None
    if not user_id:
        logger.warning("WebSocket 拒绝：token 无效 | team=%s | ip=%s", team_id, client_ip)
        await websocket.close(code=4001)
        return

    # 2. 查用户
    try:
        user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    except (InvalidId, Exception):
        logger.warning("WebSocket 拒绝：user_id 格式异常 | team=%s | user_id=%s | ip=%s", team_id, user_id, client_ip)
        await websocket.close(code=4001)
        return
    if not user_doc:
        logger.warning("WebSocket 拒绝：用户不存在 | team=%s | user_id=%s | ip=%s", team_id, user_id, client_ip)
        await websocket.close(code=4001)
        return

    display_name = format_display_name(
        user_doc.get("nickname", ""),
        user_doc.get("nickname_tag", 1),
    )

    # 3. 验证小组成员资格
    _oid(team_id)
    is_member = await db["team_members"].count_documents(
        {"team_id": team_id, "user_id": user_id}
    )
    if not is_member:
        logger.warning("WebSocket 拒绝：非小组成员 | team=%s | user=%s(%s) | ip=%s", team_id, display_name, user_id, client_ip)
        await websocket.close(code=4003)
        return

    # 4. 建立连接
    await manager.connect(team_id, websocket)
    logger.info("WebSocket 已连接 | team=%s | user=%s(%s) | ip=%s | 当前房间人数=%d",
                team_id, display_name, user_id, client_ip,
                len(manager._rooms.get(team_id, [])))
    try:
        while True:
            raw = await websocket.receive_text()
            content = raw.strip()
            if not content:
                continue
            # 过滤控制类消息（JSON 格式），只允许纯文本聊天内容
            if content.startswith("{") and content.endswith("}"):
                continue

            now = datetime.now(timezone.utc)
            doc = {
                "team_id": team_id,
                "user_id": user_id,
                "display_name": display_name,
                "content": content,
                "created_at": now,
            }
            result = await db["team_messages"].insert_one(doc)
            doc["_id"] = result.inserted_id

            await manager.broadcast(team_id, _serialize_msg(doc))

    except WebSocketDisconnect:
        manager.disconnect(team_id, websocket)
        logger.info("WebSocket 断开 | team=%s | user=%s(%s) | ip=%s | 剩余人数=%d",
                    team_id, display_name, user_id, client_ip,
                    len(manager._rooms.get(team_id, [])))
    except Exception:
        manager.disconnect(team_id, websocket)
        logger.exception("WebSocket 异常断开 | team=%s | user=%s(%s) | ip=%s",
                         team_id, display_name, user_id, client_ip)
