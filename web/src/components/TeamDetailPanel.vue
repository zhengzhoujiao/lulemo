<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { apiFetch, ApiError } from "../api/client";
import { useAuth } from "../stores/auth";

// ─── 抽屉状态 ────────────────────────────────────────────────────────────────
const nameDrawerOpen = ref(false);
const nameInput = ref("");
const nameSaving = ref(false);
const nameErr = ref("");

function openNameDrawer() {
  if (!team.value) return;
  nameInput.value = team.value.name;
  nameErr.value = "";
  nameDrawerOpen.value = true;
}

async function saveName() {
  if (!team.value || nameSaving.value) return;
  const n = nameInput.value.trim();
  if (!n) { nameErr.value = "名称不能为空"; return; }
  nameSaving.value = true; nameErr.value = "";
  try {
    const data = await apiFetch<{ team: TeamCard }>(
      `/teams/${team.value.team_id}`,
      { method: "PATCH", body: { name: n } }
    );
    team.value = data.team;
    emit("team-updated", data.team);
    nameDrawerOpen.value = false;
  } catch (e) {
    nameErr.value = e instanceof ApiError ? e.detail : "保存失败";
  } finally {
    nameSaving.value = false;
  }
}

// ─── 小组类型 ────────────────────────────────────────────────────────────────
const typeDrawerOpen = ref(false);
const typeSelected = ref<"public" | "password" | "private">("public");
const typePwInput = ref("");
const typeSaving = ref(false);
const typeErr = ref("");

function openTypeDrawer() {
  if (!team.value) return;
  typeSelected.value = team.value.team_type;
  typePwInput.value = "";
  typeErr.value = "";
  typeDrawerOpen.value = true;
}

async function saveType() {
  if (!team.value || typeSaving.value) return;
  if (typeSelected.value === "password" && !typePwInput.value.trim()) {
    typeErr.value = "口令不能为空"; return;
  }
  typeSaving.value = true; typeErr.value = "";
  try {
    const body: Record<string, unknown> = { team_type: typeSelected.value };
    if (typeSelected.value === "password") body.password = typePwInput.value.trim();
    const data = await apiFetch<{ team: TeamCard }>(
      `/teams/${team.value.team_id}`, { method: "PATCH", body }
    );
    team.value = data.team;
    emit("team-updated", data.team);
    typeDrawerOpen.value = false;
  } catch (e) {
    typeErr.value = e instanceof ApiError ? e.detail : "保存失败";
  } finally {
    typeSaving.value = false;
  }
}

// ─── 缺卡规则 ────────────────────────────────────────────────────────────────
const kickDrawerOpen = ref(false);
const kickInput = ref(10);
const kickSaving = ref(false);
const kickErr = ref("");

function openKickDrawer() {
  if (!team.value) return;
  kickInput.value = team.value.auto_kick_miss_gt;
  kickErr.value = "";
  kickDrawerOpen.value = true;
}

async function saveKick() {
  if (!team.value || kickSaving.value) return;
  const v = Number(kickInput.value);
  if (isNaN(v) || v < 0 || v > 31) { kickErr.value = "请输入 0–31 之间的数字"; return; }
  kickSaving.value = true; kickErr.value = "";
  try {
    const data = await apiFetch<{ team: TeamCard }>(
      `/teams/${team.value.team_id}`, { method: "PATCH", body: { auto_kick_miss_gt: v } }
    );
    team.value = data.team;
    emit("team-updated", data.team);
    kickDrawerOpen.value = false;
  } catch (e) {
    kickErr.value = e instanceof ApiError ? e.detail : "保存失败";
  } finally {
    kickSaving.value = false;
  }
}

// ─── 群公告 ────────────────────────────────────────────────────────────────
const descDrawerOpen = ref(false);
const descInput = ref("");
const descSaving = ref(false);
const descErr = ref("");

function openDescDrawer() {
  if (!team.value) return;
  descInput.value = team.value.description;
  descErr.value = "";
  descDrawerOpen.value = true;
}

async function saveDesc() {
  if (!team.value || descSaving.value) return;
  descSaving.value = true;
  descErr.value = "";
  try {
    const data = await apiFetch<{ team: TeamCard }>(
      `/teams/${team.value.team_id}`, { method: "PATCH", body: { description: descInput.value.trim() } }
    );
    team.value = data.team;
    emit("team-updated", data.team);
    descDrawerOpen.value = false;
  } catch (e) {
    descErr.value = e instanceof ApiError ? e.detail : "保存失败";
  } finally {
    descSaving.value = false;
  }
}

// ─── 群成员 ────────────────────────────────────────────────────────────────
interface MemberItem {
  user_id: string;
  display_name: string;
  joined_local_date: string;
  is_owner: boolean;
  weekly_rate?: string;
}
const membersDrawerOpen = ref(false);
const membersList = ref<MemberItem[]>([]);
const membersSearch = ref("");
const membersLoading = ref(false);
const kickSubmitting = ref<Record<string, boolean>>({});

async function openMembersDrawer() {
  membersSearch.value = "";
  membersDrawerOpen.value = true;
  await fetchMembers();
}

async function fetchMembers() {
  if (!team.value) return;
  membersLoading.value = true;
  try {
    const query = membersSearch.value.trim();
    const url = `/teams/${team.value.team_id}/members` + (query ? `?q=${encodeURIComponent(query)}` : "");
    const data = await apiFetch<{ members: MemberItem[] }>(url);
    membersList.value = data.members;
  } catch {
    membersList.value = [];
  } finally {
    membersLoading.value = false;
  }
}

async function handleKick(userId: string) {
  if (!team.value || kickSubmitting.value[userId]) return;
  if (!confirm("确认将该成员移出小组吗？")) return;
  kickSubmitting.value[userId] = true;
  try {
    await apiFetch(`/teams/${team.value.team_id}/members/${userId}`, { method: "DELETE" });
    // Remove from local list
    membersList.value = membersList.value.filter(m => m.user_id !== userId);
    // Update team member count
    if (team.value) {
      team.value.member_count = Math.max(1, team.value.member_count - 1);
      emit("team-updated", team.value);
    }
  } catch (e) {
    alert(e instanceof ApiError ? e.detail : "操作失败");
  } finally {
    kickSubmitting.value[userId] = false;
  }
}

watch(membersSearch, () => {
  fetchMembers();
});

// ─── 入群申请 ────────────────────────────────────────────────────────────────
interface RequestItem {
  request_id: string;
  user_id: string;
  nickname: string;
  created_at: string;
}
const requestsDrawerOpen = ref(false);
const requestsList = ref<RequestItem[]>([]);
const requestsLoading = ref(false);
const requestSubmitting = ref<Record<string, 'approve' | 'reject' | null>>({});

async function openRequestsDrawer() {
  requestsDrawerOpen.value = true;
  await fetchRequests();
}

async function fetchRequests() {
  if (!team.value) return;
  requestsLoading.value = true;
  try {
    const data = await apiFetch<{ requests: RequestItem[] }>(`/teams/${team.value.team_id}/join-requests`);
    requestsList.value = data.requests;
  } catch {
    requestsList.value = [];
  } finally {
    requestsLoading.value = false;
  }
}

async function handleApprove(req: RequestItem) {
  if (!team.value || requestSubmitting.value[req.request_id]) return;
  requestSubmitting.value[req.request_id] = 'approve';
  try {
    await apiFetch(`/teams/${team.value.team_id}/join-requests/${req.request_id}/approve`, { method: "POST" });
    // Remove from local list
    requestsList.value = requestsList.value.filter(r => r.request_id !== req.request_id);
    // Refresh team info to update member_count and pending_count
    await loadTeam();
  } catch (e) {
    alert(e instanceof ApiError ? e.detail : "操作失败");
  } finally {
    requestSubmitting.value[req.request_id] = null;
  }
}

async function handleReject(req: RequestItem) {
  if (!team.value || requestSubmitting.value[req.request_id]) return;
  requestSubmitting.value[req.request_id] = 'reject';
  try {
    await apiFetch(`/teams/${team.value.team_id}/join-requests/${req.request_id}/reject`, { method: "POST" });
    // Remove from local list
    requestsList.value = requestsList.value.filter(r => r.request_id !== req.request_id);
    // Refresh team info to update pending_count
    await loadTeam();
  } catch (e) {
    alert(e instanceof ApiError ? e.detail : "操作失败");
  } finally {
    requestSubmitting.value[req.request_id] = null;
  }
}

type TeamType = "public" | "password" | "private";

export interface TeamCard {
  team_id: string;
  name: string;
  owner_user_id: string;
  auto_kick_miss_gt: number;
  description: string;
  team_type: TeamType;
  member_count: number;
  created_at: string;
  is_mine: boolean;
  has_pending_request: boolean;
  pending_count: number;
  unread_count: number;
}

interface DailyPoint {
  date: string;
  record_count: number;
  deer_rate: number;
  check_in_rate: number;
}

interface DailySeries {
  team_id: string;
  period: string;
  points: DailyPoint[];
}

const props = withDefaults(
  defineProps<{
    teamId: string;
    team?: TeamCard | null;
    embedded?: boolean;
    variant?: "panel" | "menu";
  }>(),
  { team: null, embedded: false, variant: "panel" },
);

const emit = defineEmits<{
  "team-loaded": [team: TeamCard];
  "team-updated": [team: TeamCard];
  left: [];
  joined: [];
}>();

const { user: authUser } = useAuth();
const currentUserId = computed(() => authUser.value?.user_id ?? "");

const team = ref<TeamCard | null>(props.team);
const period = ref<"day" | "week" | "month">("week");
const dimension = ref<"count" | "rate" | "check_in">("count");
const series = ref<DailySeries | null>(null);
const seriesLoading = ref(false);
const joinPw = ref("");
const joinErr = ref("");
const joining = ref(false);

type ConfirmAction = { type: "leave" | "disband"; teamId: string; teamName: string };
const confirmAction = ref<ConfirmAction | null>(null);
const confirmSubmitting = ref(false);

const chartMax = computed(() => {
  if (!series.value) return 1;
  const pts = series.value.points;
  if (dimension.value === "count") {
    return Math.max(1, ...pts.map((p) => p.record_count));
  }
  return 1;
});

function isTeamOwner(t: TeamCard): boolean {
  return t.owner_user_id === currentUserId.value;
}

function teamTypeLabel(type: TeamType): string {
  if (type === "public") return "公开";
  if (type === "password") return "口令";
  return "私有";
}



function myIdentityLabel(t: TeamCard): string {
  if (t.is_mine) return isTeamOwner(t) ? "队长" : "成员";
  if (t.has_pending_request) return "申请中";
  return "未加入";
}

async function loadTeam() {
  if (!props.teamId) return;
  try {
    const data = await apiFetch<{ team: TeamCard }>(`/teams/${props.teamId}`);
    team.value = data.team;
    emit("team-loaded", data.team);
    await loadSeries();
  } catch {
    team.value = props.team ?? null;
  }
}

async function loadSeries() {
  if (!team.value) return;
  seriesLoading.value = true;
  try {
    series.value = await apiFetch<DailySeries>(
      `/teams/${team.value.team_id}/stats/daily?period=${period.value}`,
    );
  } catch {
    series.value = null;
  } finally {
    seriesLoading.value = false;
  }
}

watch(period, () => {
  if (team.value) loadSeries();
});

watch(
  () => props.team,
  (t) => {
    if (t) {
      team.value = t;
      loadSeries();
    }
  },
);

function openLeaveConfirm() {
  if (!team.value) return;
  confirmAction.value = {
    type: isTeamOwner(team.value) ? "disband" : "leave",
    teamId: team.value.team_id,
    teamName: team.value.name,
  };
}

function closeConfirm() {
  if (confirmSubmitting.value) return;
  confirmAction.value = null;
}

async function executeConfirm() {
  const act = confirmAction.value;
  if (!act || confirmSubmitting.value) return;
  confirmSubmitting.value = true;
  try {
    const path = act.type === "disband" ? `/teams/${act.teamId}/disband` : `/teams/${act.teamId}/leave`;
    await apiFetch(path, { method: "POST" });
    confirmAction.value = null;
    emit("left");
  } catch (e) {
    alert(e instanceof ApiError ? e.detail : "操作失败");
  } finally {
    confirmSubmitting.value = false;
  }
}

async function joinTeam() {
  if (!team.value || joining.value) return;
  const t = team.value;
  if (t.team_type === "password" && !joinPw.value.trim()) {
    joinErr.value = "请输入口令";
    return;
  }
  joining.value = true;
  joinErr.value = "";
  try {
    const body = t.team_type === "password" ? { password: joinPw.value.trim() } : {};
    const updated = await apiFetch<TeamCard>(`/teams/${t.team_id}/join`, { method: "POST", body });
    team.value = updated;
    emit("team-updated", updated);
    emit("joined");
    await loadSeries();
  } catch (e) {
    joinErr.value = e instanceof ApiError ? e.detail : "操作失败";
  } finally {
    joining.value = false;
  }
}

function fmtChartDate(s: string): string {
  if (period.value === "month") return `${s.slice(5, 7)}月`;
  return s.slice(5);
}

function barHeight(pt: DailyPoint): number {
  if (dimension.value === "count") {
    return chartMax.value > 0 ? (pt.record_count / chartMax.value) * 100 : 0;
  }
  if (dimension.value === "rate") return pt.deer_rate * 100;
  return pt.check_in_rate * 100;
}

function barLabel(pt: DailyPoint): string {
  if (dimension.value === "count") return pt.record_count > 0 ? String(pt.record_count) : "";
  if (dimension.value === "rate") {
    return pt.deer_rate > 0 ? `${(pt.deer_rate * 100).toFixed(0)}%` : "";
  }
  return pt.check_in_rate > 0 ? `${(pt.check_in_rate * 100).toFixed(0)}%` : "";
}

onMounted(() => {
  if (props.team) {
    team.value = props.team;
    emit("team-loaded", props.team);
    loadSeries();
  } else {
    loadTeam();
  }
});
</script>

<template>
  <div v-if="team" class="team-detail-panel">
    <!-- 菜单/信息页风格：分行展示信息 -->
    <template v-if="props.variant === 'menu'">
      <div class="menu-info-card">
        <!-- 群聊名称 -->
        <div
          class="menu-row"
          :class="{ 'menu-row--clickable': isTeamOwner(team) }"
          @click="isTeamOwner(team) && openNameDrawer()"
        >
          <span class="menu-label">群聊名称</span>
          <span class="menu-row-right">
            <span class="menu-value">{{ team.name }}</span>
            <svg v-if="isTeamOwner(team)" class="menu-chevron" viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>

        <!-- 小组类型 -->
        <div
          class="menu-row"
          :class="{ 'menu-row--clickable': isTeamOwner(team) }"
          @click="isTeamOwner(team) && openTypeDrawer()"
        >
          <span class="menu-label">小组类型</span>
          <span class="menu-row-right">
            <span class="menu-value">
              <span class="type-tag" :class="`type-tag--${team.team_type}`">{{ teamTypeLabel(team.team_type) }}</span>
            </span>
            <svg v-if="isTeamOwner(team)" class="menu-chevron" viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>



        <!-- 成员数 -->
        <div
          class="menu-row menu-row--clickable"
          @click="openMembersDrawer"
        >
          <span class="menu-label">群成员</span>
          <span class="menu-row-right">
            <span class="menu-value">{{ team.member_count }} 人</span>
            <svg class="menu-chevron" viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>

        <!-- 缺卡规则 -->
        <div
          class="menu-row"
          :class="{ 'menu-row--clickable': isTeamOwner(team) }"
          @click="isTeamOwner(team) && openKickDrawer()"
        >
          <span class="menu-label">缺卡规则</span>
          <span class="menu-row-right">
            <span class="menu-value">缺卡 &gt; {{ team.auto_kick_miss_gt }} 天</span>
            <svg v-if="isTeamOwner(team)" class="menu-chevron" viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>

        <!-- 群公告 -->
        <div
          class="menu-row menu-row--clickable"
          @click="openDescDrawer"
        >
          <span class="menu-label">群公告</span>
          <span class="menu-row-right">
            <span class="menu-value text-ellipsis" :class="{ muted: !team.description }">
              {{ team.description ? team.description.slice(0, 15) + (team.description.length > 15 ? '…' : '') : '暂无' }}
            </span>
            <svg class="menu-chevron" viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>

        <!-- 入群申请 (仅私有小组) -->
        <div
          v-if="team.team_type === 'private'"
          class="menu-row"
          :class="{ 'menu-row--clickable': isTeamOwner(team) }"
          @click="isTeamOwner(team) && openRequestsDrawer()"
        >
          <span class="menu-label">入群申请</span>
          <span class="menu-row-right">
            <span class="menu-value" :class="{ 'warning-text': team.pending_count > 0 }">
              {{ team.pending_count > 0 ? '待处理' : '已处理' }}
            </span>
            <svg v-if="isTeamOwner(team)" class="menu-chevron" viewBox="0 0 24 24" fill="none" width="16" height="16"><path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>

        <!-- 我的身份 -->
        <div class="menu-row">
          <span class="menu-label">我的身份</span>
          <span class="menu-row-right">
            <span class="menu-value">{{ myIdentityLabel(team) }}</span>
          </span>
        </div>
      </div>

      <!-- ── 群聊名称 抽屉 ── -->
      <Teleport to="body">
        <Transition name="drawer-slide">
          <div v-if="nameDrawerOpen" class="drawer-overlay" @click.self="nameDrawerOpen = false">
            <div class="drawer-panel">
              <div class="drawer-header">
                <button class="drawer-back" @click="nameDrawerOpen = false">
                  <svg viewBox="0 0 24 24" fill="none" width="20" height="20"><path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="drawer-title">修改群聊名称</span>
                <button class="drawer-save" :disabled="nameSaving" @click="saveName">保存</button>
              </div>
              <div class="drawer-body">
                <input v-model="nameInput" class="drawer-input" maxlength="32" placeholder="请输入群聊名称" />
                <p v-if="nameErr" class="drawer-err">{{ nameErr }}</p>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- ── 小组类型 抽屉 ── -->
      <Teleport to="body">
        <Transition name="drawer-slide">
          <div v-if="typeDrawerOpen" class="drawer-overlay" @click.self="typeDrawerOpen = false">
            <div class="drawer-panel">
              <div class="drawer-header">
                <button class="drawer-back" @click="typeDrawerOpen = false">
                  <svg viewBox="0 0 24 24" fill="none" width="20" height="20"><path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="drawer-title">修改小组类型</span>
                <button class="drawer-save" :disabled="typeSaving" @click="saveType">保存</button>
              </div>
              <div class="drawer-body">
                <div class="option-list">
                  <label class="option-item" :class="{ active: typeSelected === 'public' }">
                    <input type="radio" v-model="typeSelected" value="public" class="option-radio" />
                    <div class="option-content">
                      <span class="type-tag type-tag--public">公开</span>
                      <span class="option-desc">所有人可直接加入</span>
                    </div>
                  </label>
                  <label class="option-item" :class="{ active: typeSelected === 'password' }">
                    <input type="radio" v-model="typeSelected" value="password" class="option-radio" />
                    <div class="option-content">
                      <span class="type-tag type-tag--password">口令</span>
                      <span class="option-desc">凭口令加入</span>
                    </div>
                  </label>
                  <label class="option-item" :class="{ active: typeSelected === 'private' }">
                    <input type="radio" v-model="typeSelected" value="private" class="option-radio" />
                    <div class="option-content">
                      <span class="type-tag type-tag--private">私有</span>
                      <span class="option-desc">申请后由队长审核</span>
                    </div>
                  </label>
                </div>
                <div v-if="typeSelected === 'password'" style="margin-top:16px">
                  <p class="drawer-field-label">设置口令</p>
                  <input v-model="typePwInput" class="drawer-input" maxlength="32" placeholder="请输入口令" />
                </div>
                <p v-if="typeErr" class="drawer-err">{{ typeErr }}</p>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- ── 缺卡规则 抽屉 ── -->
      <Teleport to="body">
        <Transition name="drawer-slide">
          <div v-if="kickDrawerOpen" class="drawer-overlay" @click.self="kickDrawerOpen = false">
            <div class="drawer-panel">
              <div class="drawer-header">
                <button class="drawer-back" @click="kickDrawerOpen = false">
                  <svg viewBox="0 0 24 24" fill="none" width="20" height="20"><path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="drawer-title">修改缺卡规则</span>
                <button class="drawer-save" :disabled="kickSaving" @click="saveKick">保存</button>
              </div>
              <div class="drawer-body">
                <p class="drawer-field-label">缺卡天数超过多少天自动移出（0–31）</p>
                <input v-model.number="kickInput" type="number" min="0" max="31" class="drawer-input" />
                <p v-if="kickErr" class="drawer-err">{{ kickErr }}</p>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- ── 群公告 抽屉 ── -->
      <Teleport to="body">
        <Transition name="drawer-slide">
          <div v-if="descDrawerOpen" class="drawer-overlay" @click.self="descDrawerOpen = false">
            <div class="drawer-panel">
              <div class="drawer-header">
                <button class="drawer-back" @click="descDrawerOpen = false">
                  <svg viewBox="0 0 24 24" fill="none" width="20" height="20"><path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="drawer-title">群公告</span>
                <button v-if="isTeamOwner(team)" class="drawer-save" :disabled="descSaving" @click="saveDesc">保存</button>
              </div>
              <div class="drawer-body">
                <div v-if="isTeamOwner(team)">
                  <textarea v-model="descInput" class="drawer-textarea" maxlength="200" rows="8" placeholder="请输入群公告（限200字）"></textarea>
                  <p v-if="descErr" class="drawer-err">{{ descErr }}</p>
                </div>
                <div v-else class="drawer-desc-view">
                  {{ team.description || '暂无公告' }}
                </div>
               </div>
             </div>
           </div>
         </Transition>
       </Teleport>

      <!-- ── 群成员 抽屉 ── -->
      <Teleport to="body">
        <Transition name="drawer-slide">
          <div v-if="membersDrawerOpen" class="drawer-overlay" @click.self="membersDrawerOpen = false">
            <div class="drawer-panel">
              <div class="drawer-header">
                <button class="drawer-back" @click="membersDrawerOpen = false">
                  <svg viewBox="0 0 24 24" fill="none" width="20" height="20"><path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="drawer-title">群成员 ({{ team.member_count }})</span>
              </div>
              <div class="drawer-body drawer-body--no-padding">
                <div class="drawer-search-wrap">
                  <input v-model="membersSearch" class="drawer-search-input" placeholder="搜索成员昵称..." />
                </div>
                <div v-if="membersLoading" class="drawer-busy">加载中...</div>
                <div v-else-if="membersList.length === 0" class="drawer-empty">暂无成员</div>
                <div v-else class="member-list-wrap">
                  <div v-for="m in membersList" :key="m.user_id" class="member-item">
                    <div class="member-avatar">{{ m.display_name.slice(0,1) }}</div>
                    <div class="member-info">
                      <span class="member-name">{{ m.display_name }}</span>
                      <div class="member-sub-info">
                        <span class="member-date">{{ m.joined_local_date }} 加入</span>
                        <span class="member-rate-dot">·</span>
                        <span class="member-rate" :class="{ 'member-rate--new': m.weekly_rate === '未满七天' }">
                          周打卡率: {{ m.weekly_rate || '0%' }}
                        </span>
                      </div>
                    </div>
                    <div class="member-actions">
                      <span v-if="m.is_owner" class="role-tag owner">队长</span>
                      <button
                        v-else-if="isTeamOwner(team)"
                        class="kick-btn"
                        :disabled="kickSubmitting[m.user_id]"
                        @click="handleKick(m.user_id)"
                      >
                        {{ kickSubmitting[m.user_id] ? '...' : '踢出' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- ── 入群申请 抽屉 ── -->
      <Teleport to="body">
        <Transition name="drawer-slide">
          <div v-if="requestsDrawerOpen" class="drawer-overlay" @click.self="requestsDrawerOpen = false">
            <div class="drawer-panel">
              <div class="drawer-header">
                <button class="drawer-back" @click="requestsDrawerOpen = false">
                  <svg viewBox="0 0 24 24" fill="none" width="20" height="20"><path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
                <span class="drawer-title">待审批申请</span>
              </div>
              <div class="drawer-body">
                <div v-if="requestsLoading" class="drawer-busy">加载中...</div>
                <div v-else-if="requestsList.length === 0" class="drawer-empty">暂无待处理申请</div>
                <div v-else class="request-list-wrap">
                  <div v-for="r in requestsList" :key="r.request_id" class="request-item">
                    <div class="request-info">
                      <span class="request-user">{{ r.nickname }}</span>
                      <span class="request-time">申请时间: {{ new Date(r.created_at).toLocaleDateString() }}</span>
                    </div>
                    <div class="request-actions">
                      <button
                        class="action-btn reject"
                        :disabled="!!requestSubmitting[r.request_id]"
                        @click="handleReject(r)"
                      >
                        {{ requestSubmitting[r.request_id] === 'reject' ? '...' : '拒绝' }}
                      </button>
                      <button
                        class="action-btn approve"
                        :disabled="!!requestSubmitting[r.request_id]"
                        @click="handleApprove(r)"
                      >
                        {{ requestSubmitting[r.request_id] === 'approve' ? '...' : '通过' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>
    </template>

    <!-- 默认面板风格：保留原弹框内容 -->
    <template v-else>
      <div v-if="!embedded" class="panel-head">
        <span class="type-tag" :class="`type-tag--${team.team_type}`">
          {{ teamTypeLabel(team.team_type) }}
        </span>
      </div>

      <div class="panel-meta">
        <span class="tag">{{ team.member_count }} 人</span>
        <span class="tag muted">缺卡 &gt; {{ team.auto_kick_miss_gt }} 天移出</span>
      </div>
      <p v-if="team.description" class="panel-desc">{{ team.description }}</p>
    </template>

    <div class="chart-section" :class="{ 'chart-section--menu': props.variant === 'menu' }">
      <div class="chart-controls">
        <div class="ctrl-pills">
          <button
            v-for="p in [{ v: 'day', l: '日' }, { v: 'week', l: '周' }, { v: 'month', l: '月' }]"
            :key="p.v"
            type="button"
            class="ctrl-pill"
            :class="{ active: period === p.v }"
            @click="period = (p.v as 'day' | 'week' | 'month')"
          >
            {{ p.l }}
          </button>
        </div>
        <div class="dim-toggle">
          <button type="button" class="dim-btn" :class="{ active: dimension === 'count' }" @click="dimension = 'count'">
            噜数
          </button>
          <button type="button" class="dim-btn" :class="{ active: dimension === 'rate' }" @click="dimension = 'rate'">
            噜率
          </button>
          <button
            type="button"
            class="dim-btn"
            :class="{ active: dimension === 'check_in' }"
            @click="dimension = 'check_in'"
          >
            打卡率
          </button>
        </div>
      </div>

      <div v-if="seriesLoading" class="chart-busy muted">加载中…</div>
      <div v-else-if="series && series.points.length" class="bar-chart">
        <div v-for="pt in series.points" :key="pt.date" class="bar-col">
          <span class="bar-top-label">{{ barLabel(pt) }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{ height: barHeight(pt) + '%' }" />
          </div>
          <span class="bar-date">{{ fmtChartDate(pt.date) }}</span>
        </div>
      </div>
      <p v-else class="muted center">暂无数据</p>
    </div>

    <div class="panel-action-area" :class="{ 'panel-action-area--menu': props.variant === 'menu' }">
      <template v-if="team.is_mine">
        <button
          type="button"
          class="btn danger full-btn"
          :class="{ 'menu-white-disband': isTeamOwner(team) && props.variant === 'menu' }"
          @click="openLeaveConfirm"
        >
          {{ isTeamOwner(team) ? "解散小组" : "退出小组" }}
        </button>
      </template>
      <template v-else-if="team.has_pending_request">
        <span class="pending-tag full-label">申请已提交，等待队长审核</span>
      </template>
      <template v-else>
        <input
          v-if="team.team_type === 'password'"
          v-model="joinPw"
          class="field-input"
          placeholder="输入口令"
          autocomplete="off"
          @keyup.enter="joinTeam"
        />
        <p v-if="joinErr" class="err">{{ joinErr }}</p>
        <button type="button" class="btn primary full-btn" :disabled="joining" @click="joinTeam">
          {{ joining ? "…" : team.team_type === "private" ? "申请加入" : "加入小组" }}
        </button>
      </template>
    </div>
  </div>
  <p v-else class="muted center panel-busy">加载中…</p>

  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="confirmAction" class="dialog-overlay" @click.self="closeConfirm">
        <div class="confirm-dialog" role="alertdialog" aria-modal="true">
          <h3 class="confirm-title">
            {{ confirmAction.type === "disband" ? "确认解散小组？" : "确认退出小组？" }}
          </h3>
          <p class="confirm-msg">
            <template v-if="confirmAction.type === 'disband'">
              解散「{{ confirmAction.teamName }}」后，所有成员将被移出，该操作不可撤销。
            </template>
            <template v-else>
              退出「{{ confirmAction.teamName }}」后，你将不再属于该小组。
            </template>
          </p>
          <div class="confirm-actions">
            <button type="button" class="btn sm" :disabled="confirmSubmitting" @click="closeConfirm">取消</button>
            <button type="button" class="btn danger sm" :disabled="confirmSubmitting" @click="executeConfirm">
              {{ confirmSubmitting ? "…" : confirmAction.type === "disband" ? "确认解散" : "确认退出" }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.team-detail-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-busy {
  padding: 32px 0;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

.type-tag--public { background: rgba(22, 163, 74, 0.12); color: #16a34a; }
.type-tag--password { background: rgba(234, 179, 8, 0.15); color: #b45309; }
.type-tag--private { background: rgba(139, 92, 246, 0.12); color: #7c3aed; }

.panel-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(2, 132, 199, 0.1);
  color: #0369a1;
}

.tag.muted {
  background: rgba(0, 0, 0, 0.05);
  color: var(--muted);
}

.panel-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
}

.chart-section {
  background: var(--bg);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ctrl-pills {
  display: flex;
  gap: 6px;
}

.ctrl-pill {
  padding: 5px 12px;
  border-radius: 8px;
  border: 1px solid var(--card-border);
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.ctrl-pill.active {
  color: var(--accent-a);
  border-color: rgba(2, 132, 199, 0.5);
  background: rgba(2, 132, 199, 0.1);
}

.dim-toggle {
  display: flex;
  border: 1px solid var(--card-border);
  border-radius: 8px;
  overflow: hidden;
}

.dim-btn {
  padding: 5px 10px;
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  transition: background 0.15s, color 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.dim-btn.active {
  background: var(--accent-a);
  color: #fff;
}

.chart-busy {
  text-align: center;
  padding: 24px 0;
  font-size: 13px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 120px;
  padding-bottom: 24px;
  position: relative;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  position: relative;
}

.bar-track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
}

.bar-fill {
  width: 100%;
  min-height: 2px;
  background: var(--accent-a);
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
  opacity: 0.85;
}

.bar-top-label {
  font-size: 9px;
  color: var(--muted);
  font-weight: 700;
  margin-bottom: 2px;
  min-height: 12px;
  line-height: 12px;
}

.bar-date {
  position: absolute;
  bottom: -20px;
  font-size: 9px;
  color: var(--muted);
  white-space: nowrap;
  transform: rotate(-30deg);
  transform-origin: top center;
}

.panel-action-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--card-border);
  padding-top: 14px;
}

.panel-action-area--menu {
  padding: 10px 14px 0;
  border-top: none;
}

.panel-action-area--menu .full-btn {
  font-size: 16px;
}

.chart-section--menu {
  margin-top: 10px;
  background: #fff;
  border: 1px solid var(--card-border);
  border-radius: 0;
}

/* ─── 菜单/信息页风格 ───────────────────────────────────── */
.menu-info-card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.menu-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 56px;
  height: 56px;
  padding: 0 16px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--card-border);
  transition: background 0.15s;
}

.menu-row:last-child {
  border-bottom: none;
}

.menu-row--clickable {
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.menu-row--clickable:active {
  background: rgba(0,0,0,0.04);
}

.menu-row-right {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex-shrink: 0;
  max-width: 60%;
}

.menu-chevron {
  flex-shrink: 0;
  color: var(--muted);
  opacity: 0.5;
}

.menu-row--multiline {
  align-items: center;
  height: 56px;
  min-height: 56px;
}

/* ── 抽屉 ── */
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  background: rgba(0,0,0,0.35);
}

.drawer-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  max-width: 480px;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0,0,0,0.15);
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  height: 54px;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}

.drawer-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--text);
  border-radius: 10px;
  -webkit-tap-highlight-color: transparent;
}

.drawer-title {
  flex: 1;
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}

.drawer-save {
  border: none;
  background: var(--accent-a, #0284c7);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  padding: 6px 16px;
  border-radius: 8px;
  -webkit-tap-highlight-color: transparent;
}

.drawer-save:disabled { opacity: 0.45; }

.drawer-body {
  flex: 1;
  overflow-y: auto;
}

.drawer-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: var(--card);
  color: var(--text);
  font-size: 16px;
  outline: none;
  box-sizing: border-box;
}

.drawer-input:focus {
  border-color: var(--accent-a, #0284c7);
}

.drawer-err {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--danger);
}

.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: opacity 0.22s ease;
}
.drawer-slide-enter-active .drawer-panel,
.drawer-slide-leave-active .drawer-panel {
  transition: transform 0.25s cubic-bezier(0.32,0.72,0,1);
}
.drawer-slide-enter-from .drawer-panel,
.drawer-slide-leave-to .drawer-panel {
  transform: translateX(100%);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  opacity: 0;
}

/* option-list for type picker */
.option-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1.5px solid var(--card-border);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.option-item.active {
  border-color: var(--accent-a, #0284c7);
  background: rgba(2, 132, 199, 0.06);
}

.option-radio {
  display: none;
}

.option-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.option-desc {
  font-size: 13px;
  color: var(--muted);
}

.drawer-field-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
  margin: 0 0 8px;
}

.menu-label {
  font-size: 15px;
  font-weight: 800;
  color: var(--muted);
  white-space: nowrap;
}

.menu-value {
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
  min-width: 0;
  text-align: right;
}

.menu-info-card .type-tag {
  font-size: 12px;
  padding: 3px 8px;
}

.menu-desc {
  font-size: 15px;
  line-height: 1.4;
  color: var(--text);
  text-align: right;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

.pending-tag {
  font-size: 12px;
  font-weight: 700;
  color: #7c3aed;
  background: rgba(139, 92, 246, 0.12);
  border-radius: 8px;
  padding: 5px 10px;
}

.full-label {
  display: block;
  text-align: center;
  padding: 10px;
}

.btn {
  border-radius: 10px;
  border: 1px solid var(--card-border);
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.05);
  color: var(--text);
  transition: opacity 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.btn.primary {
  border: none;
  background: var(--accent-a);
  color: #fff;
}

.btn.danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: transparent;
  color: var(--danger);
}

.menu-white-disband {
  background: #fff !important;
  width: 100%;
  box-sizing: border-box;
}

.btn.sm {
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 8px;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.full-btn {
  width: 100%;
  padding: 12px;
  font-size: 14px;
}

.field-input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  outline: none;
}

.field-input:focus {
  border-color: rgba(2, 132, 199, 0.5);
}

.err {
  margin: 0;
  font-size: 12px;
  color: var(--danger);
}

.muted {
  color: var(--muted);
}

.center {
  text-align: center;
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 400;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px 16px;
}

.confirm-dialog {
  width: 100%;
  max-width: 340px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  padding: 22px 20px 18px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}

.confirm-title {
  margin: 0 0 10px;
  font-size: 17px;
  font-weight: 800;
  color: var(--text);
}

.confirm-msg {
  margin: 0 0 20px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--muted);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

/* Drawer specific custom styles */
.drawer-textarea {
  width: 100%;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: var(--card);
  color: var(--text);
  font-size: 15px;
  line-height: 1.5;
  outline: none;
  resize: vertical;
  box-sizing: border-box;
  font-family: inherit;
}
.drawer-textarea:focus {
  border-color: var(--accent-a, #0284c7);
}

.drawer-desc-view {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-all;
  padding: 8px 4px;
}

.drawer-body--no-padding {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.drawer-search-wrap {
  padding: 12px 16px;
  border-bottom: 1px solid var(--card-border);
  background: var(--bg);
}

.drawer-search-input {
  width: 100%;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--card-border);
  background: var(--card);
  color: var(--text);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.drawer-search-input:focus {
  border-color: var(--accent-a, #0284c7);
}

.drawer-busy,
.drawer-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--muted);
  font-size: 14px;
}

.member-list-wrap,
.request-list-wrap {
  display: flex;
  flex-direction: column;
}

.request-list-wrap {
  gap: 10px;
  padding: 12px 12px 16px;
}

.member-item,
.request-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}

.request-item {
  border: 1px solid var(--card-border);
  border-radius: 12px;
  background: var(--card);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
}

.member-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--accent-a, #0284c7);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  text-transform: uppercase;
}

.member-info,
.request-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.member-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.member-date,
.request-time {
  font-size: 12px;
  color: var(--muted);
}

.member-sub-info {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
}

.member-rate-dot {
  font-size: 12px;
  color: var(--muted);
}

.member-rate {
  font-size: 12px;
  color: var(--accent-a, #0284c7);
  font-weight: 700;
}

.member-rate--new {
  color: var(--muted);
  font-weight: normal;
}

.member-actions {
  display: flex;
  align-items: center;
}

.role-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
}
.role-tag.owner {
  background: rgba(2, 132, 199, 0.1);
  color: var(--accent-a, #0284c7);
}

.kick-btn {
  border: 1px solid rgba(239, 68, 68, 0.35);
  background: transparent;
  color: var(--danger, #ef4444);
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.kick-btn:active {
  background: rgba(239, 68, 68, 0.08);
}

.request-item {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.request-info {
  gap: 4px;
}

.request-user {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  word-break: break-word;
}

.request-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.action-btn {
  font-size: 12px;
  font-weight: 700;
  padding: 6px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}
.action-btn.reject {
  background: rgba(0, 0, 0, 0.05);
  color: var(--muted);
}
.action-btn.approve {
  background: var(--accent-a, #0284c7);
  color: #fff;
}
.action-btn:active {
  opacity: 0.85;
}

.warning-text {
  color: #f59e0b !important;
  font-weight: 700;
}

.text-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
