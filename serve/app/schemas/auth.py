from pydantic import BaseModel, Field, field_validator

from ..core.user_validation import validate_account, validate_nickname, validate_password
from ..models.region import UserRegion


class RegisterRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=20, description="账号，3-20位")
    nickname: str = Field(..., min_length=1, max_length=24, description="昵称，1-24位")
    password: str = Field(..., min_length=8, max_length=64, description="密码，至少 8 位")
    region: UserRegion = Field(..., description="注册必填省市区")

    @field_validator("account")
    @classmethod
    def account_format(cls, v: str) -> str:
        return validate_account(v)

    @field_validator("nickname")
    @classmethod
    def nickname_format(cls, v: str) -> str:
        return validate_nickname(v)

    @field_validator("password")
    @classmethod
    def password_format(cls, v: str) -> str:
        return validate_password(v)


class LoginRequest(BaseModel):
    account: str = Field(..., description="账号")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    account: str
    nickname: str
    nickname_tag: int
    register_seq: int
    display_name: str
    role: int
    identity_role: str
