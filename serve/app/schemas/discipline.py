from datetime import datetime

from pydantic import BaseModel, Field


class DisciplineResponse(BaseModel):
    eligible: bool
    window_days: int = Field(default=30)
    check_in_days: int
    required_check_in_days: int = Field(default=7)
    score: float | None = None
    percentile: float | None = None
    active_user_count: int
    calculated_at: datetime | None = None
