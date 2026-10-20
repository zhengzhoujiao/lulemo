from datetime import datetime

from pydantic import BaseModel, Field


class CreateRecordRequest(BaseModel):
    timestamp: datetime = Field(..., description="噜的发生时间（ISO8601）")
    note: str = Field(default="", max_length=500, description="备注（可选）")


class UpdateRecordRequest(BaseModel):
    note: str = Field(..., max_length=500, description="备注内容")


class RecordResponse(BaseModel):
    record_id: str
    user_id: str
    timestamp: datetime
    date: str
    note: str
    created_at: datetime


class DayStatItem(BaseModel):
    date: str   # YYYY-MM-DD
    count: int


class WeekStatItem(BaseModel):
    label: str  # 如 "5/8"
    count: int


class MonthStatItem(BaseModel):
    label: str  # 如 "5月"
    count: int


class StatsResponse(BaseModel):
    streak_days: int
    today_count: int
    recent_frequency: float  # 近7天平均（0~1）
    by_day: list[DayStatItem]
    by_week: list[WeekStatItem]
    by_month: list[MonthStatItem]
