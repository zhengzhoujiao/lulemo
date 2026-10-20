from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import calendar

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.dates_cn import BACKFILL_MAX_DAYS, parse_local_date, today_local_str
from ..deps import get_current_user
from ..models.user import UserInDB
from ..schemas.check_in import CheckInUpsertRequest, CheckInResponse, CheckInCalendarResponse
from ..services.discipline import recalculate_discipline_stat
from ..services.team_kick import run_auto_kicks_for_user

router = APIRouter(prefix="/check-ins", tags=["打卡"])


@router.post(
    "",
    response_model=CheckInResponse,
    summary="写入或覆盖某日打卡（支持补卡）",
)
async def upsert_check_in(
    body: CheckInUpsertRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CheckInResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    local_s = (body.local_date or "").strip() or today_local_str()
    try:
        ld = parse_local_date(local_s)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="local_date 须为 YYYY-MM-DD") from e

    today_d = parse_local_date(today_local_str())
    if ld > today_d:
        raise HTTPException(status_code=400, detail="不能为未来日期打卡")

    earliest = today_d - timedelta(days=BACKFILL_MAX_DAYS)
    if ld < earliest:
        raise HTTPException(
            status_code=400,
            detail=f"只允许补最近 {BACKFILL_MAX_DAYS} 天内",
        )

    local_str = ld.isoformat()
    is_backfill = ld < today_d

    existing = await db["check_ins"].find_one(
        {"user_id": current_user.id, "local_date": local_str},
    )
    created_at = existing["created_at"] if existing else datetime.now(timezone.utc)

    doc = {
        "user_id": current_user.id,
        "local_date": local_str,
        "status": body.status,
        "is_backfill": is_backfill,
        "created_at": created_at,
    }
    await db["check_ins"].replace_one(
        {"user_id": current_user.id, "local_date": local_str},
        doc,
        upsert=True,
    )

    inserted = await db["check_ins"].find_one({"user_id": current_user.id, "local_date": local_str})
    cid = inserted.get("_id") if inserted else None

    await run_auto_kicks_for_user(db, current_user.id)
    await recalculate_discipline_stat(db, current_user.id)

    return CheckInResponse(
        check_in_id=str(cid) if cid else None,
        user_id=current_user.id,
        local_date=local_str,
        status=body.status,
        is_backfill=is_backfill,
        created_at=created_at,
    )


@router.get(
    "/month",
    response_model=CheckInCalendarResponse,
    summary="按月返回打卡日历",
)
async def month_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CheckInCalendarResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    start_d = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_d = date(year, month, last_day)

    cursor = db["check_ins"].find(
        {
            "user_id": current_user.id,
            "local_date": {"$gte": start_d.isoformat(), "$lte": end_d.isoformat()},
        },
        {"local_date": 1, "status": 1},
    )
    docs = await cursor.to_list(length=366)
    days = {d["local_date"]: d["status"] for d in docs}

    return CheckInCalendarResponse(year=year, month=month, days=days)
