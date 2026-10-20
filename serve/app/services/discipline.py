from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.dates_cn import parse_local_date, today_local_str
from ..schemas.discipline import DisciplineResponse


WINDOW_DAYS = 30
REQUIRED_CHECK_IN_DAYS = 7
RELIABLE_CHECK_IN_DAYS = 21
STREAK_CAP_DAYS = 14


def _window_bounds(anchor: date) -> tuple[str, str]:
    start = anchor - timedelta(days=WINDOW_DAYS - 1)
    return start.isoformat(), anchor.isoformat()


def _score(
    *,
    check_in_days: int,
    none_days: int,
    current_none_streak: int,
) -> float:
    if check_in_days <= 0:
        return 0.0

    restraint_rate = none_days / check_in_days
    reliability = min(1.0, check_in_days / RELIABLE_CHECK_IN_DAYS)
    streak_bonus = min(current_none_streak, STREAK_CAP_DAYS) / STREAK_CAP_DAYS
    value = 100 * (
        0.75 * restraint_rate
        + 0.15 * reliability
        + 0.10 * streak_bonus
    )
    return round(value, 4)


async def _effective_status_by_date(
    db: AsyncIOMotorDatabase,
    user_id: str,
    *,
    start: str,
    end: str,
) -> dict[str, str]:
    status_by_date: dict[str, str] = {}

    async for d in db["check_ins"].find(
        {"user_id": user_id, "local_date": {"$gte": start, "$lte": end}},
        {"local_date": 1, "status": 1},
    ):
        status = d.get("status")
        if status in ("deer", "none"):
            status_by_date[d["local_date"]] = status

    async for d in db["records"].find(
        {"user_id": user_id, "date": {"$gte": start, "$lte": end}},
        {"date": 1},
    ):
        # Any recorded behavior makes the day deer, even if an older check-in says none.
        status_by_date[d["date"]] = "deer"

    return status_by_date


def _current_none_streak(status_by_date: dict[str, str], today: date) -> int:
    status_today = status_by_date.get(today.isoformat())
    if status_today == "deer":
        return 0

    check = today if status_today == "none" else today - timedelta(days=1)
    streak = 0
    while status_by_date.get(check.isoformat()) == "none":
        streak += 1
        check -= timedelta(days=1)
    return streak


async def recalculate_discipline_stat(
    db: AsyncIOMotorDatabase,
    user_id: str,
) -> DisciplineResponse:
    today = parse_local_date(today_local_str())
    start, end = _window_bounds(today)
    status_by_date = await _effective_status_by_date(
        db,
        user_id,
        start=start,
        end=end,
    )

    check_in_days = len(status_by_date)
    none_days = sum(1 for status in status_by_date.values() if status == "none")
    deer_days = sum(1 for status in status_by_date.values() if status == "deer")
    current_none_streak = _current_none_streak(status_by_date, today)
    eligible = check_in_days >= REQUIRED_CHECK_IN_DAYS
    calculated_at = datetime.now(timezone.utc)
    score = (
        _score(
            check_in_days=check_in_days,
            none_days=none_days,
            current_none_streak=current_none_streak,
        )
        if eligible
        else None
    )

    doc = {
        "user_id": user_id,
        "window_days": WINDOW_DAYS,
        "check_in_days": check_in_days,
        "required_check_in_days": REQUIRED_CHECK_IN_DAYS,
        "none_days": none_days,
        "deer_days": deer_days,
        "current_none_streak": current_none_streak,
        "eligible": eligible,
        "score": score,
        "percentile": None,
        "active_user_count": 0,
        "calculated_at": calculated_at,
    }
    await db["user_discipline_stats"].replace_one(
        {"user_id": user_id},
        doc,
        upsert=True,
    )

    active_user_count = await db["user_discipline_stats"].count_documents(
        {"eligible": True}
    )
    # 与「其他」活跃用户比较，分母不含自己
    peer_count = active_user_count - 1
    percentile: float | None = None
    if eligible and score is not None:
        if peer_count <= 0:
            # 全站仅自己达标：视为超过全部对比对象
            percentile = 100.0
        else:
            lower_count = await db["user_discipline_stats"].count_documents(
                {"eligible": True, "score": {"$lt": score}}
            )
            percentile = round(lower_count / peer_count * 100, 2)

    await db["user_discipline_stats"].update_one(
        {"user_id": user_id},
        {"$set": {"active_user_count": active_user_count, "percentile": percentile}},
    )

    return DisciplineResponse(
        eligible=eligible,
        window_days=WINDOW_DAYS,
        check_in_days=check_in_days,
        required_check_in_days=REQUIRED_CHECK_IN_DAYS,
        score=score,
        percentile=percentile,
        active_user_count=active_user_count,
        calculated_at=calculated_at,
    )
