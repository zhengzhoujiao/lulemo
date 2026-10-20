from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.dates_cn import parse_local_date, today_local_str
from ..deps import get_current_user
from ..models.user import UserInDB
from ..services.ranking import RankingsResponse, rankings_service

router = APIRouter(prefix="/rankings", tags=["排行"])


@router.get(
    "",
    response_model=RankingsResponse,
    summary="省/市/区或小队维度排行",
)
async def get_rankings(
    scope: Literal["province", "city", "district", "team"] = Query(...),
    period: Literal["day", "week", "month", "year"] = Query(...),
    metric: Literal["rate", "count", "check_in"] = Query(
        ..., description="噜率(rate)、噜数目(count)或打卡率(check_in)"
    ),
    anchor: str | None = Query(
        None,
        description="锚定日历日 YYYY-MM-DD（上海）；默认今天",
    ),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> RankingsResponse:
    day_s = (anchor or "").strip() or today_local_str()
    try:
        anchor_d = parse_local_date(day_s)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="anchor 须为 YYYY-MM-DD") from e

    return await rankings_service(
        db,
        scope=scope,
        metric=metric,
        period=period,
        anchor_day=anchor_d,
    )
