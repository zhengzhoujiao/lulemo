"""地区 / 小队排行聚合。"""
from __future__ import annotations

from collections import defaultdict

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, ValidationError

from ..core.dates_cn import MetricLiteral, PeriodLiteral, ScopeLiteral, get_period_bounds
from ..models.region import UserRegion


TEAM_RANK_MIN_MEMBERS = 10


class RankRow(BaseModel):
    rank: int
    bucket_code: str
    bucket_label: str
    value: float


class RankingsResponse(BaseModel):
    scope: ScopeLiteral | str
    period: PeriodLiteral | str
    metric: MetricLiteral | str
    anchor: str = Field(description="锚定上海日历日的 YYYY-MM-DD")
    range_start: str
    range_end: str
    rows: list[RankRow]
    note: str | None = None


def _bucket_code(region_data: dict, scope: str) -> str | None:
    r = UserRegion(**region_data)
    if scope == "province":
        return r.province_code
    if scope == "city":
        return r.city_code
    if scope == "district":
        return r.district_code
    return None


def _bucket_label_from_region(region_data: dict, scope: str) -> str:
    r = UserRegion(**region_data)
    pn = r.province_name.strip() if isinstance(r.province_name, str) else ""
    cn = r.city_name.strip() if isinstance(r.city_name, str) else ""
    dn = r.district_name.strip() if isinstance(r.district_name, str) else ""
    if scope == "province":
        return pn or r.province_code
    if scope == "city":
        parts = [p for p in (pn, cn or r.city_code) if p]
        return " ".join(parts) if parts else r.city_code
    inner = cn or pn
    parts = [p for p in (inner, dn or r.district_code) if p]
    return " ".join(parts) if parts else r.district_code


async def geographic_rank(
    db: AsyncIOMotorDatabase,
    *,
    scope: ScopeLiteral,
    metric: MetricLiteral,
    period: PeriodLiteral,
    anchor_day,
) -> RankingsResponse:
    start, end = get_period_bounds(anchor_day, period)
    rs, re = start.isoformat(), end.isoformat()

    users = await db["users"].find(
        {
            "$and": [
                {"region": {"$exists": True}},
                {"region.province_code": {"$nin": ["", None]}},
                {"region.city_code": {"$nin": ["", None]}},
                {"region.district_code": {"$nin": ["", None]}},
            ]
        },
        {"region": 1},
    ).to_list(length=500_000)

    uid_to_bucket: dict[str, str] = {}
    bucket_label: dict[str, str] = {}

    for u in users:
        uid = str(u["_id"])
        reg = u.get("region") or {}
        try:
            bc = _bucket_code(reg, scope)
        except ValidationError:
            continue
        if not bc:
            continue
        try:
            label = _bucket_label_from_region(reg, scope)
        except ValidationError:
            label = bc
        uid_to_bucket[uid] = bc
        bucket_label.setdefault(bc, label)

    if not uid_to_bucket:
        return RankingsResponse(
            scope=scope,
            period=period,
            metric=metric,
            anchor=anchor_day.isoformat(),
            range_start=rs,
            range_end=re,
            rows=[],
            note="暂无带完整 region 的用户",
        )

    uid_list = list(uid_to_bucket.keys())
    uid_set = frozenset(uid_list)

    rec_counts_bucket: defaultdict[str, int] = defaultdict(int)
    async for d in db["records"].find(
        {"user_id": {"$in": uid_list}, "date": {"$gte": rs, "$lte": re}},
        {"user_id": 1},
    ):
        uid = d["user_id"]
        bcode = uid_to_bucket.get(uid)
        if not bcode:
            continue
        rec_counts_bucket[bcode] += 1

    deer_by_user: defaultdict[str, int] = defaultdict(int)
    total_ci_by_user: defaultdict[str, int] = defaultdict(int)
    async for d in db["check_ins"].find(
        {"user_id": {"$in": uid_list}, "local_date": {"$gte": rs, "$lte": re}},
        {"user_id": 1, "status": 1},
    ):
        uid = d["user_id"]
        if uid not in uid_set:
            continue
        total_ci_by_user[uid] += 1
        if d.get("status") == "deer":
            deer_by_user[uid] += 1

    bucket_deer_sum = defaultdict(float)
    bucket_ci_sum = defaultdict(float)
    bucket_user_count: defaultdict[str, int] = defaultdict(int)
    for uid, bcode in uid_to_bucket.items():
        bucket_user_count[bcode] += 1
        td = total_ci_by_user.get(uid, 0)
        if td <= 0:
            continue
        bucket_ci_sum[bcode] += td
        bucket_deer_sum[bcode] += float(deer_by_user.get(uid, 0))

    bucket_label_keys = sorted(bucket_label.keys())
    num_days = (end - start).days + 1

    if metric == "count":
        values = {b: float(rec_counts_bucket.get(b, 0)) for b in bucket_label_keys}
    elif metric == "check_in":
        values = {}
        for bcode in bucket_label_keys:
            users = bucket_user_count[bcode]
            ci = bucket_ci_sum[bcode]
            values[bcode] = ci / (users * num_days) if users > 0 and num_days > 0 else 0.0
    else:
        values = {}
        for bcode in bucket_label_keys:
            den = bucket_ci_sum[bcode]
            values[bcode] = (bucket_deer_sum[bcode] / den) if den > 0 else 0.0

    merged_codes = sorted(
        bucket_label_keys,
        key=lambda code: (-values.get(code, 0), code),
    )

    rows = [
        RankRow(
            rank=i + 1,
            bucket_code=c,
            bucket_label=bucket_label.get(c, c),
            value=round(values[c], 6),
        )
        for i, c in enumerate(merged_codes)
    ]

    rows = rows[:120]

    return RankingsResponse(
        scope=scope,
        period=period,
        metric=metric,
        anchor=anchor_day.isoformat(),
        range_start=rs,
        range_end=re,
        rows=rows,
        note=None,
    )


async def team_rank(
    db: AsyncIOMotorDatabase,
    *,
    metric: MetricLiteral,
    period: PeriodLiteral,
    anchor_day,
) -> RankingsResponse:
    start, end = get_period_bounds(anchor_day, period)
    rs, re = start.isoformat(), end.isoformat()

    memberships_by_team: dict[str, list[str]] = defaultdict(list)
    for m in await db["team_members"].find({}).to_list(length=500_000):
        memberships_by_team[str(m["team_id"])].append(m["user_id"])

    qualifying: dict[str, str] = {}
    teams = await db["teams"].find({}).to_list(length=50_000)
    for t in teams:
        tid = str(t["_id"])
        if len(memberships_by_team.get(tid, [])) >= TEAM_RANK_MIN_MEMBERS:
            qualifying[tid] = str(t["name"])

    if not qualifying:
        return RankingsResponse(
            scope="team",
            period=period,
            metric=metric,
            anchor=anchor_day.isoformat(),
            range_start=rs,
            range_end=re,
            rows=[],
            note=(
                f"小队榜仅统计成员不少于 {TEAM_RANK_MIN_MEMBERS} "
                "的队伍（当前暂无满足条件的队伍）"
            ),
        )

    uid_to_teams: dict[str, list[str]] = defaultdict(list)
    valid_uids = set()
    for tid, mids in memberships_by_team.items():
        if tid not in qualifying:
            continue
        for uid in mids:
            uid_to_teams[uid].append(tid)
            valid_uids.add(uid)

    valid_list = list(valid_uids)

    rec_by_team: defaultdict[str, int] = defaultdict(int)

    deer_by_uid: defaultdict[str, int] = defaultdict(int)
    ci_by_uid: defaultdict[str, int] = defaultdict(int)

    async for d in db["records"].find(
        {"user_id": {"$in": valid_list}, "date": {"$gte": rs, "$lte": re}},
        {"user_id": 1},
    ):
        uid = d["user_id"]
        for tid in uid_to_teams.get(uid, []):
            rec_by_team[tid] += 1

    async for d in db["check_ins"].find(
        {"user_id": {"$in": valid_list}, "local_date": {"$gte": rs, "$lte": re}},
        {"user_id": 1, "status": 1},
    ):
        uid = d["user_id"]
        ci_by_uid[uid] += 1
        if d.get("status") == "deer":
            deer_by_uid[uid] += 1

    team_deer = defaultdict(float)
    team_ci = defaultdict(float)
    for uid, tids in uid_to_teams.items():
        tci = ci_by_uid.get(uid, 0)
        if tci <= 0:
            continue
        dcnt = float(deer_by_uid.get(uid, 0))
        for tid in tids:
            team_ci[tid] += tci
            team_deer[tid] += dcnt

    num_days = (end - start).days + 1
    metric_values: dict[str, float] = {}
    for tid in qualifying:
        if metric == "count":
            metric_values[tid] = float(rec_by_team.get(tid, 0))
        elif metric == "check_in":
            member_count = len(memberships_by_team.get(tid, []))
            ci = team_ci[tid]
            metric_values[tid] = (
                ci / (member_count * num_days) if member_count > 0 and num_days > 0 else 0.0
            )
        else:
            dn = team_ci[tid]
            metric_values[tid] = (team_deer[tid] / dn) if dn > 0 else 0.0

    merged = sorted(metric_values.keys(), key=lambda tid: (-metric_values[tid], tid))

    rows = [
        RankRow(
            rank=i + 1,
            bucket_code=tid,
            bucket_label=qualifying[tid],
            value=round(metric_values[tid], 6),
        )
        for i, tid in enumerate(merged)
    ]

    rows = rows[:120]

    return RankingsResponse(
        scope="team",
        period=period,
        metric=metric,
        anchor=anchor_day.isoformat(),
        range_start=rs,
        range_end=re,
        rows=rows,
        note=f"仅统计成员不少于 {TEAM_RANK_MIN_MEMBERS} 的队伍",
    )


async def rankings_service(
    db: AsyncIOMotorDatabase,
    *,
    scope: ScopeLiteral | str,
    metric: MetricLiteral,
    period: PeriodLiteral,
    anchor_day,
) -> RankingsResponse:
    scope_s = scope  # noqa
    if scope_s in ("province", "city", "district"):
        return await geographic_rank(
            db,
            scope=scope_s,  # type: ignore[arg-type]
            metric=metric,
            period=period,
            anchor_day=anchor_day,
        )
    return await team_rank(
        db,
        metric=metric,
        period=period,
        anchor_day=anchor_day,
    )
