from datetime import datetime, timezone

from pydantic import BaseModel, Field


class PostInDB(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    author_user_id: str
    author_display_name: str
    content: str
    liked_by: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    def to_doc(self) -> dict:
        return {
            "author_user_id": self.author_user_id,
            "author_display_name": self.author_display_name,
            "content": self.content,
            "liked_by": self.liked_by,
            "created_at": self.created_at,
        }
