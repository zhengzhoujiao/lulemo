"""用户展示名解析（昵称 / 昵称#编号）。"""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.user import UserInDB, format_display_name

ANONYMOUS_DISPLAY_NAME = "momo"


def resolve_display_name_for_user_sync(user: UserInDB) -> str:
    nickname = (user.nickname or "").strip()
    tag = user.nickname_tag
    if nickname and isinstance(tag, int) and tag > 0:
        return format_display_name(nickname, tag)
    return nickname or "用户"


async def resolve_display_name_for_user(db: AsyncIOMotorDatabase, user: UserInDB) -> str:
    del db
    return resolve_display_name_for_user_sync(user)


def resolve_display_name_from_doc_sync(doc: dict) -> str:
    nickname = doc.get("nickname")
    tag = doc.get("nickname_tag")
    if isinstance(nickname, str) and nickname.strip() and isinstance(tag, int) and tag > 0:
        return format_display_name(nickname.strip(), tag)
    legacy = doc.get("plaza_display_name")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    oid = str(doc.get("_id", ""))
    return f"路人{oid[-4:]}"


async def resolve_display_name_from_doc(db: AsyncIOMotorDatabase, doc: dict) -> str:
    del db
    return resolve_display_name_from_doc_sync(doc)
