"""根据自然月缺席打卡阈值，将用户踢出小队。"""

from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.dates_cn import (
    missed_checkins_calendar_month_naive_shanghai,
    today_local_str,
    parse_local_date,
)


async def run_auto_kicks_for_user(db: AsyncIOMotorDatabase, user_id: str) -> None:
    today_s = today_local_str()
    today_d = parse_local_date(today_s)

    memberships = (
        await db["team_members"]
        .find({"user_id": user_id})
        .to_list(length=500)
    )
    if not memberships:
        return

    cis = (
        await db["check_ins"]
        .find({"user_id": user_id}, {"local_date": 1})
        .to_list(length=366 * 5)
    )
    ci_dates = frozenset(d["local_date"] for d in cis)

    for m in memberships:
        team_oid = ObjectId(str(m["team_id"]))
        team_doc = await db["teams"].find_one({"_id": team_oid})
        if team_doc is None:
            continue
        threshold = team_doc.get("auto_kick_miss_gt", 10)

        jd = parse_local_date(m["joined_local_date"])
        missed = missed_checkins_calendar_month_naive_shanghai(jd, today_d, ci_dates)
        # 严格大于阈值才踢（missed > threshold）
        if missed > threshold and threshold >= 0:
            await db["team_members"].delete_one(
                {"_id": m["_id"]},
            )
