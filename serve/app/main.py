import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import connect_db, close_db, get_db
from .routers import auth, users, records, check_ins, rankings, social_posts, teams, chat, work_orders, discipline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await _ensure_indexes()
    yield
    await close_db()


async def _ensure_indexes() -> None:
    """启动时创建必要的 MongoDB 索引"""
    db = get_db()
    await db["users"].create_index("account", unique=True)
    try:
        await db["users"].drop_index("nickname_tag_1")
    except Exception:
        pass
    await db["users"].create_index([("nickname", 1), ("nickname_tag", 1)], unique=True)
    await db["users"].create_index("register_seq", unique=True, sparse=True)
    try:
        await db["users"].drop_index("username_1")
    except Exception:
        pass
    await db["records"].create_index([("user_id", 1), ("date", 1)])
    await db["records"].create_index([("user_id", 1), ("timestamp", -1)])
    await db["check_ins"].create_index([("user_id", 1), ("local_date", 1)], unique=True)
    await db["user_discipline_stats"].create_index("user_id", unique=True)
    await db["user_discipline_stats"].create_index([("eligible", 1), ("score", 1)])
    await db["teams"].create_index("owner_user_id")
    await db["team_members"].create_index([("team_id", 1), ("user_id", 1)], unique=True)
    # 允许同一用户加入多个小队：移除 user_id 全局唯一约束
    try:
        await db["team_members"].drop_index("user_id_1")
    except Exception:
        pass
    await db["team_members"].create_index("user_id")
    await db["posts"].create_index([("created_at", -1)])
    await db["comments"].create_index([("post_id", 1), ("created_at", 1)])
    # 嵌套评论：按父评论 ID 查子回复
    await db["comments"].create_index([("parent_comment_id", 1), ("created_at", 1)])
    # 顶层热评查询：post_id + parent_comment_id 过滤
    await db["comments"].create_index([("post_id", 1), ("parent_comment_id", 1), ("created_at", 1)])
    await db["users"].create_index([("region.province_code", 1)], sparse=True)
    await db["team_join_requests"].create_index([("team_id", 1), ("user_id", 1), ("status", 1)])
    await db["team_join_requests"].create_index([("team_id", 1), ("status", 1)])
    await db["team_messages"].create_index([("team_id", 1), ("created_at", -1)])
    await db["team_chat_reads"].create_index(
        [("team_id", 1), ("user_id", 1)],
        unique=True,
    )
    await db["work_orders"].create_index([("user_id", 1), ("updated_at", -1)])
    await db["work_orders"].create_index([("last_reply_by", 1), ("updated_at", -1)])
    await db["work_order_replies"].create_index([("work_order_id", 1), ("created_at", 1)])


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="噜了么 —— 男性健康自我管理工具后端 API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(records.router, prefix="/api/v1")
    app.include_router(check_ins.router, prefix="/api/v1")
    app.include_router(rankings.router, prefix="/api/v1")
    app.include_router(discipline.router, prefix="/api/v1")
    app.include_router(social_posts.router, prefix="/api/v1")
    app.include_router(teams.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(work_orders.router, prefix="/api/v1")

    @app.get("/", tags=["健康检查"])
    async def root():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

    return app


app = create_app()
