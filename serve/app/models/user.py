from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .region import UserRegion

IdentityRoleId = Literal[
    "balanced",
    "sigma",
    "chaos",
    "monk",
    "pure_love",
]

VALID_IDENTITY_ROLES = frozenset(
    {"balanced", "sigma", "chaos", "monk", "pure_love"}
)


def format_display_name(nickname: str, tag: int) -> str:
    """展示名：nickname_tag 为 1 时仅昵称，大于 1 时追加 #编号（不补零）。"""
    nick = nickname.strip()
    if tag <= 1:
        return nick
    return f"{nick}#{tag}"


class UserInDB(BaseModel):
    """MongoDB 中存储的用户文档结构"""

    id: str | None = Field(default=None, alias="_id")
    account: str
    nickname: str
    nickname_tag: int
    register_seq: int = 0
    password_hash: str
    role: int = 0  # 0=普通用户，1=管理员
    identity_role: IdentityRoleId = "balanced"
    region: UserRegion | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    @property
    def display_name(self) -> str:
        return format_display_name(self.nickname, self.nickname_tag)

    def to_doc(self) -> dict:
        d: dict = {
            "account": self.account,
            "nickname": self.nickname,
            "nickname_tag": self.nickname_tag,
            "register_seq": self.register_seq,
            "password_hash": self.password_hash,
            "role": self.role,
            "identity_role": self.identity_role,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.region is not None:
            d["region"] = self.region.mongo_dict()
        return d

    @classmethod
    def from_doc(cls, doc: dict) -> "UserInDB":
        if doc:
            oid = doc.get("_id")
            if oid is not None:
                doc["_id"] = str(oid)
            if "account" not in doc and "username" in doc:
                doc["account"] = doc["username"]
            if "nickname" not in doc:
                legacy = doc.get("plaza_display_name") or doc.get("username") or doc.get("account")
                doc["nickname"] = str(legacy or "用户")
            if "nickname_tag" not in doc:
                doc["nickname_tag"] = 0
            if "register_seq" not in doc:
                doc["register_seq"] = 0
            if "role" not in doc:
                doc["role"] = 0
            try:
                doc["role"] = 1 if int(doc.get("role", 0)) == 1 else 0
            except Exception:
                doc["role"] = 0
            rg = doc.get("region")
            if rg and isinstance(rg, dict):
                try:
                    doc["region"] = UserRegion(**rg)
                except ValidationError:
                    doc["region"] = None
            elif rg is None:
                doc.pop("region", None)
            else:
                doc["region"] = None
            role = doc.get("identity_role")
            if role not in VALID_IDENTITY_ROLES:
                doc["identity_role"] = "balanced"
        return cls(**doc)
