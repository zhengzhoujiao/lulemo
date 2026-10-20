"""昵称 #编号：按同名昵称递增（第 2 个 aaa 为 #2，非全局用户数）。"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


def _counter_id(nickname: str) -> str:
    return f"nickname_seq:{nickname.strip()}"


async def allocate_nickname_tag(db: AsyncIOMotorDatabase, nickname: str) -> int:
    """为 nickname 分配下一个同名序号（从 1 开始）。"""
    nick = nickname.strip()
    if not nick:
        raise ValueError("nickname 不能为空")

    doc = await db["counters"].find_one_and_update(
        {"_id": _counter_id(nick)},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])
