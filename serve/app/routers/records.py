from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.dates_cn import datetime_to_local_date, parse_local_date, today_local_str
from ..deps import get_current_user
from ..models.record import RecordInDB
from ..models.user import UserInDB
from ..services.discipline import recalculate_discipline_stat
from ..services.team_kick import run_auto_kicks_for_user
from ..schemas.record import (
    CreateRecordRequest,
    UpdateRecordRequest,
    RecordResponse,
    StatsResponse,
    DayStatItem,
    WeekStatItem,
    MonthStatItem,
)

router = APIRouter(prefix="/records", tags=["噜记录"])


def _date_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


async def _ensure_deer_check_in(
    db: AsyncIOMotorDatabase,
    *,
    user_id: str,
    local_date: str,
) -> None:
    existing = await db["check_ins"].find_one(
        {"user_id": user_id, "local_date": local_date},
    )
    created_at = existing["created_at"] if existing else datetime.now(timezone.utc)
    await db["check_ins"].replace_one(
        {"user_id": user_id, "local_date": local_date},
        {
            "user_id": user_id,
            "local_date": local_date,
            "status": "deer",
            "is_backfill": local_date < today_local_str(),
            "created_at": created_at,
        },
        upsert=True,
    )


@router.get(
    "",
    response_model=list[RecordResponse],
    summary="获取噜记录列表",
)
async def list_records(
    limit: int = Query(default=50, ge=1, le=1000, description="每次返回最多条数"),
    offset: int = Query(default=0, ge=0, description="跳过条数（分页用）"),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[RecordResponse]:
    cursor = (
        db["records"]
        .find({"user_id": current_user.id})
        .sort("timestamp", -1)
        .skip(offset)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return [
        RecordResponse(
            record_id=str(d["_id"]),
            user_id=d["user_id"],
            timestamp=d["timestamp"],
            date=d["date"],
            note=d.get("note", ""),
            created_at=d["created_at"],
        )
        for d in docs
    ]


@router.post(
    "",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增一条噜记录",
)
async def create_record(
    body: CreateRecordRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> RecordResponse:
    record = RecordInDB(
        user_id=current_user.id,
        timestamp=body.timestamp,
        date=_date_str(body.timestamp),
        note=body.note,
    )
    result = await db["records"].insert_one(record.to_doc())
    await _ensure_deer_check_in(db, user_id=current_user.id, local_date=record.date)
    await run_auto_kicks_for_user(db, current_user.id)
    await recalculate_discipline_stat(db, current_user.id)
    record_id = str(result.inserted_id)
    return RecordResponse(
        record_id=record_id,
        user_id=record.user_id,
        timestamp=record.timestamp,
        date=record.date,
        note=record.note,
        created_at=record.created_at,
    )


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除一条噜记录",
)
async def delete_record(
    record_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    try:
        oid = ObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="record_id 格式错误")

    result = await db["records"].delete_one(
        {"_id": oid, "user_id": current_user.id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在或无权删除")
    await recalculate_discipline_stat(db, current_user.id)


@router.patch(
    "/{record_id}",
    response_model=RecordResponse,
    summary="更新记录备注",
)
async def update_record(
    record_id: str,
    body: UpdateRecordRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> RecordResponse:
    try:
        oid = ObjectId(record_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="record_id 格式错误")

    doc = await db["records"].find_one({"_id": oid, "user_id": current_user.id})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在或无权修改")

    await db["records"].update_one({"_id": oid}, {"$set": {"note": body.note}})
    return RecordResponse(
        record_id=str(doc["_id"]),
        user_id=doc["user_id"],
        timestamp=doc["timestamp"],
        date=doc["date"],
        note=body.note,
        created_at=doc["created_at"],
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="获取统计数据",
    description="返回连续未噜天数、今日次数、近7天频率及按天/周/月聚合",
)
async def get_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> StatsResponse:
    today_str = today_local_str()
    join_date = parse_local_date(datetime_to_local_date(current_user.created_at))

    # 拉取近 90 天的记录用于统计（覆盖所有聚合维度）
    since = datetime.now(timezone.utc) - timedelta(days=90)
    cursor = db["records"].find(
        {"user_id": current_user.id, "timestamp": {"$gte": since}},
        {"date": 1, "timestamp": 1},
    )
    docs = await cursor.to_list(length=10000)

    date_set: set[str] = {d["date"] for d in docs}
    date_count: dict[str, int] = {}
    for d in docs:
        date_count[d["date"]] = date_count.get(d["date"], 0) + 1

    # 连续未噜天数：从昨天往前数无记录日，不早于账号注册日（上海日历）
    streak = 0
    if today_str not in date_set:
        check = parse_local_date(today_str) - timedelta(days=1)
        while check >= join_date:
            if check.isoformat() in date_set:
                break
            streak += 1
            check -= timedelta(days=1)

    today_count = date_count.get(today_str, 0)

    # 近7天频率（0~1，只计算有无记录，不计次数）
    recent_days = [
        _date_str(datetime.now(timezone.utc) - timedelta(days=i))
        for i in range(7)
    ]
    recent_frequency = sum(1 for d in recent_days if d in date_set) / 7

    # 按天（最近7天）
    by_day = [
        DayStatItem(date=d, count=date_count.get(d, 0))
        for d in reversed(recent_days)
    ]

    # 按周（最近6周，每周 Mon~Sun 或滚动7天窗口）
    by_week: list[WeekStatItem] = []
    for i in range(5, -1, -1):
        end = datetime.now(timezone.utc) - timedelta(days=i * 7)
        start = end - timedelta(days=6)
        count = sum(
            date_count.get(_date_str(start + timedelta(days=j)), 0)
            for j in range(7)
        )
        label = f"{start.month}/{start.day}"
        by_week.append(WeekStatItem(label=label, count=count))

    # 按月（最近6个月）
    by_month: list[MonthStatItem] = []
    now = datetime.now(timezone.utc)
    for i in range(5, -1, -1):
        month = (now.month - i - 1) % 12 + 1
        year = now.year + ((now.month - i - 1) // 12)
        prefix = f"{year}-{str(month).zfill(2)}"
        count = sum(v for k, v in date_count.items() if k.startswith(prefix))
        by_month.append(MonthStatItem(label=f"{month}月", count=count))

    return StatsResponse(
        streak_days=streak,
        today_count=today_count,
        recent_frequency=round(recent_frequency, 4),
        by_day=by_day,
        by_week=by_week,
        by_month=by_month,
    )
