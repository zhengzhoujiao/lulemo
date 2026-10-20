from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..core.user_validation import validate_nickname
from ..models.region import UserRegion

IdentityRoleId = Literal[
    "balanced",
    "sigma",
    "chaos",
    "monk",
    "pure_love",
]


class UserResponse(BaseModel):
    user_id: str
    account: str
    nickname: str
    nickname_tag: int
    register_seq: int
    display_name: str
    role: int
    identity_role: IdentityRoleId
    created_at: datetime
    region: UserRegion | None = None


def user_to_response(user, *, display_name: str | None = None) -> UserResponse:
    return UserResponse(
        user_id=user.id or "",
        account=user.account,
        nickname=user.nickname,
        nickname_tag=user.nickname_tag,
        register_seq=user.register_seq,
        display_name=display_name if display_name is not None else user.display_name,
        role=user.role,
        identity_role=user.identity_role,
        created_at=user.created_at,
        region=user.region,
    )


class UpdateIdentityRequest(BaseModel):
    identity_role: IdentityRoleId


class UpdateNicknameRequest(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=24)

    @field_validator("nickname")
    @classmethod
    def nickname_format(cls, v: str) -> str:
        return validate_nickname(v)
