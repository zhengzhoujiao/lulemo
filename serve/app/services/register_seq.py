"""全站注册序号（第几位注册用户，从 1 开始）。"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

_COUNTER_ID = "user_register_seq"


async def allocate_register_seq(db: AsyncIOMotorDatabase) -> int:
    doc = await db["counters"].find_one_and_update(
        {"_id": _COUNTER_ID},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])
