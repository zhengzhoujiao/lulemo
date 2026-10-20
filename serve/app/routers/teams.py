"""小队（无群聊）。"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.dates_cn import PeriodLiteral, get_chart_buckets, get_period_bounds, parse_local_date, today_local_str
from ..deps import get_current_user
from ..models.team import TeamInDB, TeamJoinRequestInDB, TeamMemberInDB
from ..models.user import UserInDB
from ..schemas.team import (
    DailyStatPoint,
    JoinRequestItem,
    JoinRequestsResponse,
    JoinTeamRequest,
    MembersResponse,
    MemberWithProfile,
    TeamCreateRequest,
    TeamDailyStatsResponse,
    TeamDetailResponse,
    TeamMemberItem,
    TeamResponse,
    TeamStatResponse,
    TeamUpdateRequest,
)
from ..services.team_chat_read import get_unread_count
from ..services.team_kick import run_auto_kicks_for_user


router = APIRouter(prefix="/teams", tags=["小组"])


def _oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except InvalidId as e:
        raise HTTPException(status_code=400, detail="team_id 无效") from e


async def _member_count(db: AsyncIOMotorDatabase, team_hex: str) -> int:
    return await db["team_members"].count_documents({"team_id": team_hex})


async def _build_team_card(
    db: AsyncIOMotorDatabase,
    tdoc: dict,
    current_user_id: str | None = None,
) -> TeamResponse:
    tid = str(tdoc["_id"])
    is_mine = False
    has_pending = False
    pending_count = 0
    unread_count = 0
    team_type = str(tdoc.get("team_type") or "public")
    if current_user_id:
        is_mine = await db["team_members"].count_documents(
            {"team_id": tid, "user_id": current_user_id}
        ) > 0
        if is_mine:
            unread_count = await get_unread_count(db, tid, current_user_id)
        if team_type == "private" and not is_mine:
            has_pending = await db["team_join_requests"].count_documents(
                {"team_id": tid, "user_id": current_user_id, "status": "pending"}
            ) > 0
        if team_type == "private" and str(tdoc.get("owner_user_id")) == current_user_id:
            pending_count = await db["team_join_requests"].count_documents(
                {"team_id": tid, "status": "pending"}
            )
    return TeamResponse(
        team_id=tid,
        name=tdoc["name"],
        owner_user_id=str(tdoc["owner_user_id"]),
        auto_kick_miss_gt=int(tdoc.get("auto_kick_miss_gt", 10)),
        description=str(tdoc.get("description") or ""),
        team_type=team_type,
        member_count=await _member_count(db, tid),
        created_at=tdoc["created_at"],
        is_mine=is_mine,
        has_pending_request=has_pending,
        pending_count=pending_count,
        unread_count=unread_count,
    )


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    q: str | None = Query(None, max_length=64),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[TeamResponse]:
    """列出所有小队（广场），可按名称模糊搜索。"""
    filt: dict = {}
    if q and q.strip():
        import re as _re
        filt["name"] = {"$regex": _re.escape(q.strip()), "$options": "i"}
    docs = await db["teams"].find(filt).sort("created_at", -1).to_list(length=200)
    return [await _build_team_card(db, d, current_user.id) for d in docs]


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    body: TeamCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    if body.team_type == "password" and not body.password.strip():
        raise HTTPException(status_code=422, detail="口令小组必须设置口令")

    team = TeamInDB(
        name=body.name.strip(),
        owner_user_id=current_user.id,
        auto_kick_miss_gt=body.auto_kick_miss_gt,
        description=body.description.strip(),
        team_type=body.team_type,
        password=body.password.strip() if body.team_type == "password" else "",
    )
    res = await db["teams"].insert_one(team.to_doc())
    tid = str(res.inserted_id)

    await db["team_members"].insert_one(
        TeamMemberInDB(
            team_id=tid,
            user_id=current_user.id,
            joined_local_date=today_local_str(),
        ).to_doc(),
    )

    doc = await db["teams"].find_one({"_id": res.inserted_id})
    return await _build_team_card(db, doc, current_user.id)


@router.get("/mine", response_model=list[TeamDetailResponse])
async def my_teams(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[TeamDetailResponse]:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    memberships = (
        await db["team_members"]
        .find({"user_id": current_user.id})
        .sort("joined_at", -1)
        .to_list(length=500)
    )
    if not memberships:
        return []

    out: list[TeamDetailResponse] = []
    for m in memberships:
        team_doc = await db["teams"].find_one({"_id": ObjectId(m["team_id"])})
        if team_doc is None:
            await db["team_members"].delete_one({"_id": m["_id"]})
            continue

        members_docs = (
            await db["team_members"]
            .find({"team_id": m["team_id"]})
            .sort("joined_at", 1)
            .to_list(length=500)
        )
        out.append(
            TeamDetailResponse(
                team=await _build_team_card(db, team_doc, current_user.id),
                members=[
                    TeamMemberItem(user_id=x["user_id"], joined_local_date=x["joined_local_date"])
                    for x in members_docs
                ],
            )
        )
    return out


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamDetailResponse:
    _oid(team_id)

    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")

    members_docs = (
        await db["team_members"]
        .find({"team_id": team_id})
        .sort("joined_at", 1)
        .to_list(length=500)
    )

    return TeamDetailResponse(
        team=await _build_team_card(db, doc, current_user.id),
        members=[
            TeamMemberItem(user_id=x["user_id"], joined_local_date=x["joined_local_date"])
            for x in members_docs
        ],
    )


@router.post("/{team_id}/join", response_model=TeamResponse)
async def join_team(
    team_id: str,
    body: JoinTeamRequest = JoinTeamRequest(),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamResponse:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    _oid(team_id)

    dup = await db["team_members"].find_one({"team_id": team_id, "user_id": current_user.id})
    if dup:
        raise HTTPException(status_code=409, detail="已是该小队成员")

    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")

    team_type = str(doc.get("team_type") or "public")

    if team_type == "password":
        stored_pw = str(doc.get("password") or "")
        if body.password.strip() != stored_pw:
            raise HTTPException(status_code=403, detail="口令错误")

    elif team_type == "private":
        # 检查是否已有待审核申请
        existing_req = await db["team_join_requests"].find_one(
            {"team_id": team_id, "user_id": current_user.id, "status": "pending"}
        )
        if existing_req:
            raise HTTPException(status_code=409, detail="已提交申请，等待队长审核")
        await db["team_join_requests"].insert_one(
            TeamJoinRequestInDB(
                team_id=team_id,
                user_id=current_user.id,
            ).to_doc()
        )
        refreshed = await db["teams"].find_one({"_id": ObjectId(team_id)})
        return await _build_team_card(db, refreshed, current_user.id)

    await db["team_members"].insert_one(
        TeamMemberInDB(
            team_id=team_id,
            user_id=current_user.id,
            joined_local_date=today_local_str(),
        ).to_doc(),
    )
    await run_auto_kicks_for_user(db, current_user.id)

    refreshed = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if refreshed is None:
        await db["team_members"].delete_one({"team_id": team_id, "user_id": current_user.id})
        raise HTTPException(status_code=500, detail="小队数据异常")

    return await _build_team_card(db, refreshed, current_user.id)


@router.get("/{team_id}/join-requests", response_model=JoinRequestsResponse)
async def list_join_requests(
    team_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> JoinRequestsResponse:
    """队长查看私有小组待审核申请列表。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")
    if str(doc.get("owner_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="仅队长可查看申请")

    reqs = (
        await db["team_join_requests"]
        .find({"team_id": team_id, "status": "pending"})
        .sort("created_at", 1)
        .to_list(length=200)
    )
    request_items: list[JoinRequestItem] = []
    for r in reqs:
        uid = str(r["user_id"])
        user_doc = None
        try:
            if len(uid) == 24:
                user_doc = await db["users"].find_one({"_id": ObjectId(uid)})
        except Exception:
            user_doc = None
        if user_doc is None:
            user_doc = await db["users"].find_one({"user_id": uid})

        nickname = uid
        if user_doc:
            nickname = str(user_doc.get("nickname") or user_doc.get("display_name") or uid)

        request_items.append(
            JoinRequestItem(
                request_id=str(r["_id"]),
                user_id=uid,
                nickname=nickname,
                created_at=r["created_at"],
            )
        )

    return JoinRequestsResponse(requests=request_items)


@router.post("/{team_id}/join-requests/{request_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_join_request(
    team_id: str,
    request_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """队长通过申请，将用户加入小队。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")
    if str(doc.get("owner_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="仅队长可审批")

    try:
        req_doc = await db["team_join_requests"].find_one({"_id": ObjectId(request_id), "team_id": team_id})
    except Exception:
        raise HTTPException(status_code=400, detail="申请 ID 无效")
    if req_doc is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req_doc.get("status") != "pending":
        raise HTTPException(status_code=409, detail="申请已处理")

    applicant_id = str(req_doc["user_id"])
    dup = await db["team_members"].find_one({"team_id": team_id, "user_id": applicant_id})
    if not dup:
        await db["team_members"].insert_one(
            TeamMemberInDB(
                team_id=team_id,
                user_id=applicant_id,
                joined_local_date=today_local_str(),
            ).to_doc()
        )
    await db["team_join_requests"].update_one(
        {"_id": req_doc["_id"]},
        {"$set": {"status": "approved"}},
    )


@router.post("/{team_id}/join-requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_join_request(
    team_id: str,
    request_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """队长拒绝申请。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")
    if str(doc.get("owner_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="仅队长可审批")

    try:
        req_doc = await db["team_join_requests"].find_one({"_id": ObjectId(request_id), "team_id": team_id})
    except Exception:
        raise HTTPException(status_code=400, detail="申请 ID 无效")
    if req_doc is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req_doc.get("status") != "pending":
        raise HTTPException(status_code=409, detail="申请已处理")

    await db["team_join_requests"].update_one(
        {"_id": req_doc["_id"]},
        {"$set": {"status": "rejected"}},
    )


@router.post("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    _oid(team_id)

    res = await db["team_members"].delete_one({"team_id": team_id, "user_id": current_user.id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="未加入该小队或已退出")

    remaining = await _member_count(db, team_id)
    if remaining == 0:
        await db["teams"].delete_one({"_id": ObjectId(team_id)})


@router.post("/{team_id}/disband", status_code=status.HTTP_204_NO_CONTENT)
async def disband_team(
    team_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """队长解散小队：删除所有成员、申请记录及小队本身。"""
    if not current_user.id:
        raise HTTPException(status_code=400, detail="用户状态异常")

    _oid(team_id)

    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")
    if str(doc.get("owner_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="仅队长可解散小队")

    await db["team_members"].delete_many({"team_id": team_id})
    await db["team_join_requests"].delete_many({"team_id": team_id})
    await db["teams"].delete_one({"_id": ObjectId(team_id)})


@router.patch("/{team_id}", response_model=TeamDetailResponse)
async def update_team(
    team_id: str,
    body: TeamUpdateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamDetailResponse:
    """队长更新小组基本信息。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")
    if str(doc.get("owner_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="仅队长可修改小组信息")

    upd: dict = {}
    if body.name is not None:
        upd["name"] = body.name.strip()
    if body.auto_kick_miss_gt is not None:
        upd["auto_kick_miss_gt"] = body.auto_kick_miss_gt
    if body.description is not None:
        upd["description"] = body.description.strip()
    if body.team_type is not None:
        upd["team_type"] = body.team_type
        if body.team_type == "password":
            pw = (body.password or "").strip()
            if not pw:
                raise HTTPException(status_code=422, detail="口令小组必须设置口令")
            upd["password"] = pw
        else:
            upd["password"] = ""
    elif body.password is not None:
        current_type = str(doc.get("team_type") or "public")
        if current_type == "password":
            pw = body.password.strip()
            if not pw:
                raise HTTPException(status_code=422, detail="口令不能为空")
            upd["password"] = pw

    if upd:
        await db["teams"].update_one({"_id": ObjectId(team_id)}, {"$set": upd})

    refreshed = await db["teams"].find_one({"_id": ObjectId(team_id)})
    members_docs = (
        await db["team_members"]
        .find({"team_id": team_id})
        .sort("joined_at", 1)
        .to_list(length=500)
    )
    return TeamDetailResponse(
        team=await _build_team_card(db, refreshed, current_user.id),
        members=[
            TeamMemberItem(user_id=x["user_id"], joined_local_date=x["joined_local_date"])
            for x in members_docs
        ],
    )


@router.get("/{team_id}/members", response_model=MembersResponse)
async def list_members(
    team_id: str,
    q: str | None = Query(None, max_length=64),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MembersResponse:
    """获取小组成员列表（含 display_name），支持搜索。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")

    # 必须是成员
    is_member = await db["team_members"].count_documents(
        {"team_id": team_id, "user_id": current_user.id}
    ) > 0
    if not is_member:
        raise HTTPException(status_code=403, detail="仅成员可查看成员列表")

    owner_id = str(doc.get("owner_user_id"))
    member_docs = (
        await db["team_members"]
        .find({"team_id": team_id})
        .sort("joined_at", 1)
        .to_list(length=500)
    )

    # First pass: filter by search query
    filtered_members = []
    for m in member_docs:
        uid = str(m["user_id"])
        user_doc = await db["users"].find_one({"_id": ObjectId(uid)} if len(uid) == 24 else {"user_id": uid})
        if user_doc is None:
            try:
                user_doc = await db["users"].find_one({"_id": ObjectId(uid)})
            except Exception:
                user_doc = None
        display_name = uid
        if user_doc:
            display_name = str(user_doc.get("display_name") or user_doc.get("nickname") or uid)
        if q and q.strip() and q.strip().lower() not in display_name.lower():
            continue
        filtered_members.append((m, uid, display_name))

    # Fetch check-ins for filtered members in the last 7 days
    today_str = today_local_str()
    today_d = parse_local_date(today_str)
    start_d = today_d - timedelta(days=6)
    start_str = start_d.isoformat()

    filtered_uids = [x[1] for x in filtered_members]
    user_deer_counts = defaultdict(int)
    if filtered_uids:
        cursor = db["check_ins"].find({
            "user_id": {"$in": filtered_uids},
            "local_date": {"$gte": start_str, "$lte": today_str},
            "status": "deer"
        })
        checkins = await cursor.to_list(length=len(filtered_uids) * 8)
        for c in checkins:
            user_deer_counts[c["user_id"]] += 1

    result: list[MemberWithProfile] = []
    for m, uid, display_name in filtered_members:
        joined_str = str(m.get("joined_local_date") or "")
        is_new = True
        if joined_str:
            try:
                joined_d = parse_local_date(joined_str)
                if (today_d - joined_d).days >= 6:
                    is_new = False
            except Exception:
                is_new = False
        else:
            is_new = False

        if is_new:
            weekly_rate = "未满七天"
        else:
            deer_count = user_deer_counts.get(uid, 0)
            rate_pct = int(round((deer_count / 7.0) * 100))
            weekly_rate = f"{rate_pct}%"

        result.append(
            MemberWithProfile(
                user_id=uid,
                display_name=display_name,
                joined_local_date=joined_str,
                is_owner=(uid == owner_id),
                weekly_rate=weekly_rate,
            )
        )
    return MembersResponse(members=result)


@router.delete("/{team_id}/members/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def kick_member(
    team_id: str,
    target_user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """队长踢出成员。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")
    if str(doc.get("owner_user_id")) != current_user.id:
        raise HTTPException(status_code=403, detail="仅队长可踢出成员")
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能踢出自己")

    res = await db["team_members"].delete_one({"team_id": team_id, "user_id": target_user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="该用户不是小队成员")


async def _team_stats_aggregate(
    db: AsyncIOMotorDatabase,
    team_id: str,
    period: PeriodLiteral,
    anchor_d,
) -> TeamStatResponse:
    start, end = get_period_bounds(anchor_d, period)
    rs, re = start.isoformat(), end.isoformat()

    members = (
        await db["team_members"]
        .find({"team_id": team_id}, {"user_id": 1})
        .to_list(length=500)
    )
    uids = [m["user_id"] for m in members]
    if not uids:
        return TeamStatResponse(
            team_id=team_id,
            period=period,
            anchor=anchor_d.isoformat(),
            range_start=rs,
            range_end=re,
            record_count=0,
            deer_rate=0.0,
            check_in_rate=0.0,
        )

    rec_count = 0
    async for _ in db["records"].find(
        {"user_id": {"$in": uids}, "date": {"$gte": rs, "$lte": re}},
        {"_id": 1},
    ):
        rec_count += 1

    deer = defaultdict(int)
    ci_tot = defaultdict(int)
    async for d in db["check_ins"].find(
        {"user_id": {"$in": uids}, "local_date": {"$gte": rs, "$lte": re}},
        {"user_id": 1, "status": 1},
    ):
        u = d["user_id"]
        ci_tot[u] += 1
        if d.get("status") == "deer":
            deer[u] += 1

    dsum = 0.0
    csum = 0.0
    for u in uids:
        ct = ci_tot.get(u, 0)
        if ct <= 0:
            continue
        csum += ct
        dsum += float(deer.get(u, 0))

    rate = (dsum / csum) if csum > 0 else 0.0

    total_ci = sum(ci_tot.values())
    num_days = (end - start).days + 1
    check_in_rate = (
        total_ci / (len(uids) * num_days) if len(uids) > 0 and num_days > 0 else 0.0
    )

    return TeamStatResponse(
        team_id=team_id,
        period=period,
        anchor=anchor_d.isoformat(),
        range_start=rs,
        range_end=re,
        record_count=rec_count,
        deer_rate=round(rate, 6),
        check_in_rate=round(check_in_rate, 6),
    )


@router.get("/{team_id}/stats", response_model=TeamStatResponse)
async def team_stats_endpoint(
    team_id: str,
    period: PeriodLiteral = Query("week"),
    anchor: str | None = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamStatResponse:
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")

    day_s = (anchor or "").strip() or today_local_str()
    try:
        anchor_d = parse_local_date(day_s)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="anchor 须为 YYYY-MM-DD") from e

    return await _team_stats_aggregate(db, team_id, period, anchor_d)


@router.get("/{team_id}/stats/daily", response_model=TeamDailyStatsResponse)
async def team_daily_stats_endpoint(
    team_id: str,
    period: PeriodLiteral = Query("week"),
    anchor: str | None = Query(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TeamDailyStatsResponse:
    """按图表维度返回小队统计序列：日=近7天，周=近7周，月=近6月。"""
    _oid(team_id)
    doc = await db["teams"].find_one({"_id": ObjectId(team_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="小队不存在")

    day_s = (anchor or "").strip() or today_local_str()
    try:
        anchor_d = parse_local_date(day_s)
    except ValueError as e:
        raise HTTPException(status_code=422, detail="anchor 须为 YYYY-MM-DD") from e

    if period not in ("day", "week", "month"):
        raise HTTPException(status_code=422, detail="图表仅支持 day/week/month 维度")

    buckets = get_chart_buckets(anchor_d, period)
    range_start = buckets[0][0]
    range_end = buckets[-1][1]

    members = (
        await db["team_members"]
        .find({"team_id": team_id}, {"user_id": 1, "joined_local_date": 1})
        .to_list(length=500)
    )
    parsed_members = []
    for m in members:
        uid = m["user_id"]
        joined_str = m.get("joined_local_date") or ""
        try:
            joined_d = parse_local_date(joined_str)
        except Exception:
            joined_d = parse_local_date("2020-01-01")
        parsed_members.append({"user_id": uid, "joined_date": joined_d})

    uids = [m["user_id"] for m in parsed_members]
    rs, re = range_start.isoformat(), range_end.isoformat()

    user_rec_by_day: dict[tuple[str, str], int] = defaultdict(int)
    if uids:
        async for d in db["records"].find(
            {"user_id": {"$in": uids}, "date": {"$gte": rs, "$lte": re}},
            {"user_id": 1, "date": 1},
        ):
            user_rec_by_day[(d["user_id"], d["date"])] += 1

    user_deer_by_day: dict[tuple[str, str], int] = defaultdict(int)
    user_ci_by_day: dict[tuple[str, str], int] = defaultdict(int)
    if uids:
        async for d in db["check_ins"].find(
            {"user_id": {"$in": uids}, "local_date": {"$gte": rs, "$lte": re}},
            {"user_id": 1, "local_date": 1, "status": 1},
        ):
            uid = d["user_id"]
            day_key = d["local_date"]
            user_ci_by_day[(uid, day_key)] += 1
            if d.get("status") == "deer":
                user_deer_by_day[(uid, day_key)] += 1

    points: list[DailyStatPoint] = []
    for start, end, label in buckets:
        eligible_members = [m for m in parsed_members if m["joined_date"] <= start]
        eligible_uids = [m["user_id"] for m in eligible_members]

        rec_count = 0
        deer_sum = 0
        ci_sum = 0

        d = start
        while d <= end:
            dk = d.isoformat()
            for uid in eligible_uids:
                rec_count += user_rec_by_day.get((uid, dk), 0)
                deer_sum += user_deer_by_day.get((uid, dk), 0)
                ci_sum += user_ci_by_day.get((uid, dk), 0)
            d += timedelta(days=1)

        rate = (deer_sum / ci_sum) if ci_sum > 0 else 0.0
        num_days = (end - start).days + 1
        eligible_member_count = len(eligible_uids)
        check_in_rate = (
            ci_sum / (eligible_member_count * num_days) if eligible_member_count > 0 and num_days > 0 else 0.0
        )
        points.append(
            DailyStatPoint(
                date=label,
                record_count=rec_count,
                deer_rate=round(rate, 6),
                check_in_rate=round(check_in_rate, 6),
            )
        )

    return TeamDailyStatsResponse(team_id=team_id, period=period, points=points)
