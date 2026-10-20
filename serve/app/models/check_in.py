from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

CheckInStatus = Literal["deer", "none"]


class CheckInInDB(BaseModel):
    """每日打卡一条（噜了 / 没噜），按上海日历日."""

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    local_date: str
    status: CheckInStatus
    is_backfill: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    def to_doc(self) -> dict:
        return {
            "user_id": self.user_id,
            "local_date": self.local_date,
            "status": self.status,
            "is_backfill": self.is_backfill,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: dict) -> "CheckInInDB":
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
