from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..deps import get_current_user
from ..models.comment import CommentInDB
from ..models.post import PostInDB
from ..models.user import UserInDB
from ..schemas.social import (
    CommentCreateRequest,
    CommentResponse,
    LikeToggleResponse,
    PostCreateRequest,
    PostResponse,
)

from ..services.display_name import ANONYMOUS_DISPLAY_NAME, resolve_display_name_from_doc

router = APIRouter(prefix="/social", tags=["七嘴八舌"])


async def _author_display_name(db: AsyncIOMotorDatabase, author: dict, *, anonymous: bool) -> str:
    if anonymous:
        return ANONYMOUS_DISPLAY_NAME
    return await resolve_display_name_from_doc(db, author)


async def _build_comment_responses(
    docs: list[dict],
    user_id: str,
    db: AsyncIOMotorDatabase,
) -> list[CommentResponse]:
    """将评论文档列表转为 CommentResponse，附带 like_count/liked/reply_count。"""
    if not docs:
        return []
    comment_ids = [str(d["_id"]) for d in docs]

    # 批量统计每条评论的子回复数
    pipeline = [
        {"$match": {"parent_comment_id": {"$in": comment_ids}}},
        {"$group": {"_id": "$parent_comment_id", "count": {"$sum": 1}}},
    ]
    reply_count_docs = await db["comments"].aggregate(pipeline).to_list(length=None)
    reply_counts: dict[str, int] = {r["_id"]: r["count"] for r in reply_count_docs}

    result: list[CommentResponse] = []
    for d in docs:
        liked_by: list[str] = d.get("liked_by", [])
        result.append(
            CommentResponse(
                comment_id=str(d["_id"]),
                post_id=d["post_id"],
                author_display_name=d.get("author_display_name", "路人"),
                content=d["content"],
                created_at=d["created_at"],
                mine=str(d.get("author_user_id")) == user_id,
                like_count=len(liked_by),
                liked=user_id in liked_by,
                reply_count=reply_counts.get(str(d["_id"]), 0),
            )
        )
    return result


# ---------------------------------------------------------------------------
# 帖子 CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    body: PostCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> PostResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    author = await db["users"].find_one({"_id": ObjectId(current_user.id)})
    if author is None:
        raise HTTPException(status_code=400, detail="用户不存在")

    post = PostInDB(
        author_user_id=current_user.id,
        author_display_name=await _author_display_name(db, author, anonymous=body.anonymous),
        content=body.content.strip(),
    )
    res = await db["posts"].insert_one(post.to_doc())
    return PostResponse(
        post_id=str(res.inserted_id),
        author_display_name=post.author_display_name,
        content=post.content,
        created_at=post.created_at,
        mine=True,
    )


@router.get("/posts", response_model=list[PostResponse])
async def list_posts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[PostResponse]:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    cursor = db["posts"].find({}).sort("created_at", -1).skip(offset).limit(limit)
    docs = await cursor.to_list(length=limit)
    if not docs:
        return []

    post_ids = [str(d["_id"]) for d in docs]

    # 一次性取出这批帖子的所有顶层评论
    cmt_docs = await db["comments"].find(
        {
            "post_id": {"$in": post_ids},
            "$or": [
                {"parent_comment_id": None},
                {"parent_comment_id": {"$exists": False}},
            ],
        }
    ).to_list(length=None)

    # 按 post_id 分组
    comments_by_post: dict[str, list[dict]] = defaultdict(list)
    for c in cmt_docs:
        comments_by_post[c["post_id"]].append(c)

    out: list[PostResponse] = []
    for d in docs:
        pid = str(d["_id"])
        liked_by: list[str] = d.get("liked_by", [])
        post_cmts = comments_by_post.get(pid, [])

        # 热评：点赞最多，时间最旧
        hot_cmt: CommentResponse | None = None
        if post_cmts:
            sorted_cmts = sorted(
                post_cmts,
                key=lambda c: (-len(c.get("liked_by", [])), c["created_at"]),
            )
            hc = sorted_cmts[0]
            hc_liked_by: list[str] = hc.get("liked_by", [])
            hot_cmt = CommentResponse(
                comment_id=str(hc["_id"]),
                post_id=pid,
                author_display_name=hc.get("author_display_name", "路人"),
                content=hc["content"],
                created_at=hc["created_at"],
                mine=str(hc.get("author_user_id")) == current_user.id,
                like_count=len(hc_liked_by),
                liked=current_user.id in hc_liked_by,
                reply_count=0,
            )

        out.append(
            PostResponse(
                post_id=pid,
                author_display_name=d.get("author_display_name", "路人"),
                content=d.get("content", ""),
                created_at=d["created_at"],
                mine=str(d.get("author_user_id")) == current_user.id,
                like_count=len(liked_by),
                liked=current_user.id in liked_by,
                comment_count=len(post_cmts),
                hot_comment=hot_cmt,
            )
        )
    return out


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")
    try:
        oid = ObjectId(post_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="post_id 无效") from e

    doc = await db["posts"].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if str(doc.get("author_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的帖子")

    await db["posts"].delete_one({"_id": oid})
    await db["comments"].delete_many({"post_id": post_id})


# ---------------------------------------------------------------------------
# 帖子点赞
# ---------------------------------------------------------------------------


@router.post("/posts/{post_id}/like", response_model=LikeToggleResponse)
async def toggle_post_like(
    post_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> LikeToggleResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")
    try:
        oid = ObjectId(post_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="post_id 无效") from e

    doc = await db["posts"].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="帖子不存在")

    liked_by: list[str] = doc.get("liked_by", [])
    if current_user.id in liked_by:
        await db["posts"].update_one({"_id": oid}, {"$pull": {"liked_by": current_user.id}})
        new_liked_by = [x for x in liked_by if x != current_user.id]
        return LikeToggleResponse(liked=False, like_count=len(new_liked_by))
    else:
        await db["posts"].update_one({"_id": oid}, {"$addToSet": {"liked_by": current_user.id}})
        return LikeToggleResponse(liked=True, like_count=len(liked_by) + 1)


# ---------------------------------------------------------------------------
# 评论 CRUD
# ---------------------------------------------------------------------------


@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    post_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[CommentResponse]:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    try:
        oid = ObjectId(post_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="post_id 无效") from e
    exists = await db["posts"].count_documents({"_id": oid})
    if exists == 0:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 只取顶层评论
    cmt_docs = await db["comments"].find(
        {
            "post_id": post_id,
            "$or": [
                {"parent_comment_id": None},
                {"parent_comment_id": {"$exists": False}},
            ],
        }
    ).to_list(length=500)

    # 按热度排序（点赞多 → 时间早）
    cmt_docs.sort(key=lambda c: (-len(c.get("liked_by", [])), c["created_at"]))

    return await _build_comment_responses(cmt_docs, current_user.id, db)


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_comment(
    post_id: str,
    body: CommentCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> CommentResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")
    try:
        oid = ObjectId(post_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="post_id 无效") from e

    p = await db["posts"].find_one({"_id": oid})
    if p is None:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 若有父评论，校验其存在性
    if body.parent_comment_id:
        try:
            parent_oid = ObjectId(body.parent_comment_id)
        except InvalidId as e:
            raise HTTPException(status_code=400, detail="parent_comment_id 无效") from e
        parent = await db["comments"].find_one({"_id": parent_oid})
        if parent is None:
            raise HTTPException(status_code=404, detail="父评论不存在")

    author = await db["users"].find_one({"_id": ObjectId(current_user.id)})
    if author is None:
        raise HTTPException(status_code=400)

    cm = CommentInDB(
        post_id=post_id,
        author_user_id=current_user.id,
        author_display_name=await _author_display_name(db, author, anonymous=False),
        content=body.content.strip(),
        parent_comment_id=body.parent_comment_id,
    )
    cm_doc = cm.to_doc()
    res = await db["comments"].insert_one(cm_doc)
    return CommentResponse(
        comment_id=str(res.inserted_id),
        post_id=post_id,
        author_display_name=cm.author_display_name,
        content=cm.content,
        created_at=cm.created_at or datetime.now(timezone.utc),
        mine=True,
        reply_count=0,
    )


# ---------------------------------------------------------------------------
# 评论点赞
# ---------------------------------------------------------------------------


@router.post("/comments/{comment_id}/like", response_model=LikeToggleResponse)
async def toggle_comment_like(
    comment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> LikeToggleResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")
    try:
        oid = ObjectId(comment_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="comment_id 无效") from e

    doc = await db["comments"].find_one({"_id": oid})
    if doc is None:
        raise HTTPException(status_code=404, detail="评论不存在")

    liked_by: list[str] = doc.get("liked_by", [])
    if current_user.id in liked_by:
        await db["comments"].update_one({"_id": oid}, {"$pull": {"liked_by": current_user.id}})
        new_liked_by = [x for x in liked_by if x != current_user.id]
        return LikeToggleResponse(liked=False, like_count=len(new_liked_by))
    else:
        await db["comments"].update_one({"_id": oid}, {"$addToSet": {"liked_by": current_user.id}})
        return LikeToggleResponse(liked=True, like_count=len(liked_by) + 1)


# ---------------------------------------------------------------------------
# 子回复列表
# ---------------------------------------------------------------------------


@router.get("/comments/{comment_id}/replies", response_model=list[CommentResponse])
async def get_replies(
    comment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[CommentResponse]:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")
    try:
        oid = ObjectId(comment_id)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="comment_id 无效") from e

    parent = await db["comments"].find_one({"_id": oid})
    if parent is None:
        raise HTTPException(status_code=404, detail="评论不存在")

    reply_docs = (
        await db["comments"]
        .find({"parent_comment_id": comment_id})
        .sort("created_at", 1)
        .to_list(length=500)
    )

    return await _build_comment_responses(reply_docs, current_user.id, db)
