from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CheckInUpsertRequest(BaseModel):
    """local_date 用 YYYY-MM-DD（上海日历）。缺省表示今天。"""

    local_date: str | None = Field(None, description="不传则默认为上海当天")
    status: Literal["deer", "none"]


class CheckInResponse(BaseModel):
    check_in_id: str | None = None
    user_id: str
    local_date: str
    status: str
    is_backfill: bool
    created_at: datetime


class CheckInCalendarResponse(BaseModel):
    year: int
    month: int
    days: dict[str, str]
    """local_date -> status（无键表示未打卡）"""
