from datetime import datetime, timezone

from pydantic import BaseModel, Field


class RecordInDB(BaseModel):
    """MongoDB 中存储的噜记录文档结构"""

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    timestamp: datetime
    date: str  # YYYY-MM-DD，冗余存储便于日期聚合查询
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    def to_doc(self) -> dict:
        return {
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "date": self.date,
            "note": self.note,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc: dict) -> "RecordInDB":
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
