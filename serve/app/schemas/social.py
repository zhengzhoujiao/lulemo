from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=900)
    anonymous: bool = False


class CommentCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=600)
    parent_comment_id: str | None = None


class LikeToggleResponse(BaseModel):
    liked: bool
    like_count: int


class CommentResponse(BaseModel):
    comment_id: str
    post_id: str
    author_display_name: str
    content: str
    created_at: datetime
    mine: bool = False
    like_count: int = 0
    liked: bool = False
    reply_count: int = 0


class PostResponse(BaseModel):
    post_id: str
    author_display_name: str
    content: str
    created_at: datetime
    mine: bool = False
    like_count: int = 0
    liked: bool = False
    comment_count: int = 0
    hot_comment: CommentResponse | None = None
