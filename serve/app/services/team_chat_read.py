"""小组聊天已读 / 未读计数。"""
from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_unread_count(db: AsyncIOMotorDatabase, team_id: str, user_id: str) -> int:
    """统计他人发送、且晚于上次已读时间的消息数。"""
    read_doc = await db["team_chat_reads"].find_one({"team_id": team_id, "user_id": user_id})
    filt: dict = {"team_id": team_id, "user_id": {"$ne": user_id}}
    if read_doc and read_doc.get("last_read_at"):
        filt["created_at"] = {"$gt": read_doc["last_read_at"]}
    return await db["team_messages"].count_documents(filt)


async def mark_team_read(db: AsyncIOMotorDatabase, team_id: str, user_id: str) -> None:
    await db["team_chat_reads"].update_one(
        {"team_id": team_id, "user_id": user_id},
        {"$set": {"last_read_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
