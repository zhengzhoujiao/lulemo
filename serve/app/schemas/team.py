from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    auto_kick_miss_gt: int = Field(default=10, ge=0, le=31)
    description: str = Field(default="", max_length=200)
    team_type: Literal["public", "password", "private"] = "public"
    password: str = Field(default="", max_length=32)


class JoinTeamRequest(BaseModel):
    password: str = ""


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    auto_kick_miss_gt: int | None = Field(default=None, ge=0, le=31)
    description: str | None = Field(default=None, max_length=200)
    team_type: Literal["public", "password", "private"] | None = None
    password: str | None = Field(default=None, max_length=32)


class TeamResponse(BaseModel):
    team_id: str
    name: str
    owner_user_id: str
    auto_kick_miss_gt: int
    description: str = ""
    team_type: Literal["public", "password", "private"] = "public"
    member_count: int
    created_at: datetime
    is_mine: bool = False
    has_pending_request: bool = False  # 当前用户是否有待审核的申请
    pending_count: int = 0  # 私有小组待审核申请数（仅队长可见）
    unread_count: int = 0  # 未读聊天消息数（仅已加入成员）


class JoinRequestItem(BaseModel):
    request_id: str
    user_id: str
    nickname: str
    created_at: datetime


class JoinRequestsResponse(BaseModel):
    requests: list[JoinRequestItem]


class TeamMemberItem(BaseModel):
    user_id: str
    joined_local_date: str


class MemberWithProfile(BaseModel):
    user_id: str
    display_name: str
    joined_local_date: str
    is_owner: bool = False
    weekly_rate: str | None = None


class MembersResponse(BaseModel):
    members: list[MemberWithProfile]


class TeamDetailResponse(BaseModel):
    team: TeamResponse
    members: list[TeamMemberItem]


class TeamStatResponse(BaseModel):
    team_id: str
    period: str
    anchor: str
    range_start: str
    range_end: str
    record_count: int
    deer_rate: float
    check_in_rate: float


class DailyStatPoint(BaseModel):
    date: str
    record_count: int
    deer_rate: float
    check_in_rate: float


class TeamDailyStatsResponse(BaseModel):
    team_id: str
    period: str
    points: list[DailyStatPoint]
