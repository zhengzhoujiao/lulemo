from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import hash_password, verify_password, create_access_token
from ..models.user import UserInDB
from ..schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from ..schemas.user import UserResponse, user_to_response
from ..deps import get_current_user
from ..services.display_name import resolve_display_name_for_user
from ..services.nickname_tag import allocate_nickname_tag
from ..services.register_seq import allocate_register_seq

router = APIRouter(prefix="/auth", tags=["认证"])


def _token_response(
    user_id: str,
    user: UserInDB,
    token: str,
    *,
    display_name: str | None = None,
) -> TokenResponse:
    return TokenResponse(
        access_token=token,
        user_id=user_id,
        account=user.account,
        nickname=user.nickname,
        nickname_tag=user.nickname_tag,
        register_seq=user.register_seq,
        display_name=display_name if display_name is not None else user.display_name,
        role=user.role,
        identity_role=user.identity_role,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册账号",
)
async def register(
    body: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    existing = await db["users"].find_one(
        {"$or": [{"account": body.account}, {"username": body.account}]}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="账号已被占用",
        )

    tag = await allocate_nickname_tag(db, body.nickname)
    register_seq = await allocate_register_seq(db)
    user = UserInDB(
        account=body.account,
        nickname=body.nickname,
        nickname_tag=tag,
        register_seq=register_seq,
        password_hash=hash_password(body.password),
        region=body.region,
    )
    result = await db["users"].insert_one(user.to_doc())
    user_id = str(result.inserted_id)

    token = create_access_token(subject=user_id)
    display_name = await resolve_display_name_for_user(db, user)
    return _token_response(user_id, user, token, display_name=display_name)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="账号登录",
)
async def login(
    body: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    doc = await db["users"].find_one({"account": body.account})
    if doc is None:
        doc = await db["users"].find_one({"username": body.account})
    if doc is None or not verify_password(body.password, doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )

    user = UserInDB.from_doc(doc)
    user_id = user.id or str(doc["_id"])
    token = create_access_token(subject=user_id)
    display_name = await resolve_display_name_for_user(db, user)
    return _token_response(user_id, user, token, display_name=display_name)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前登录用户信息",
)
async def get_me(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserResponse:
    display_name = await resolve_display_name_for_user(db, current_user)
    return user_to_response(current_user, display_name=display_name)
