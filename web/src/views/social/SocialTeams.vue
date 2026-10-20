<script setup lang="ts">
defineOptions({ name: "SocialTeams" });

import { computed, nextTick, onActivated, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiFetch, ApiError } from "../../api/client";
import TeamDetailPanel, { type TeamCard } from "../../components/TeamDetailPanel.vue";
import { useAuth } from "../../stores/auth";

const router = useRouter();
const route = useRoute();
const { user } = useAuth();
const currentUserId = computed(() => user.value?.user_id ?? "");

function showOwnerPendingTag(team: TeamCard): boolean {
  return team.owner_user_id === currentUserId.value && team.pending_count > 0;
}

/* ─── 类型 ─────────────────────────────────────────────── */
type TeamType = "public" | "password" | "private";

function formatUnreadCount(count: number): string {
  if (count > 99) return "99+";
  return String(count);
}

interface Member {
  user_id: string;
  joined_local_date: string;
}

interface Detail {
  team: TeamCard;
  members: Member[];
}

interface Stat {
  team_id: string;
  period: string;
  range_start: string;
  range_end: string;
  record_count: number;
  deer_rate: number;
  check_in_rate: number;
}

/* ─── 共享状态 ──────────────────────────────────────────── */
const currentTab = computed<"mine" | "plaza">(() =>
  route.query.teamTab === "plaza" ? "plaza" : "mine",
);
const myTeams = ref<Detail[]>([]);
const myLoading = ref(false);
const myErr = ref("");

/* ─── 我的小组 ──────────────────────────────────────────── */
async function loadMine(opts?: { silent?: boolean }) {
  const silent = opts?.silent === true && myTeams.value.length > 0;
  if (!silent) myLoading.value = true;
  myErr.value = "";
  try {
    myTeams.value = await apiFetch<Detail[]>("/teams/mine");
    loadYesterdayStats(myTeams.value.map((d) => d.team));
  } catch (e) {
    myErr.value = e instanceof ApiError ? e.detail : "加载失败";
  } finally {
    myLoading.value = false;
  }
}

/* ─── 小组详情弹框 ─────────────────────────────────────── */
const detailTeam = ref<TeamCard | null>(null);

function openDetail(team: TeamCard) {
  detailTeam.value = team;
}

function closeDetail() {
  detailTeam.value = null;
}

function onDetailLeft() {
  closeDetail();
  loadMine();
  loadPlaza();
}

function onDetailJoined() {
  loadMine();
  loadPlaza();
}

/* ─── 创建小组弹层 ──────────────────────────────────────── */
const showCreate = ref(false);
const createName = ref("");
const createDesc = ref("");
const createKick = ref(10);
const createType = ref<TeamType>("public");
const createPassword = ref("");
const createSubmitting = ref(false);
const createErr = ref("");
const createNameRef = ref<HTMLInputElement | null>(null);

const typeOptions: { value: TeamType; label: string; hint: string }[] = [
  { value: "public", label: "公开", hint: "所有人可直接加入，无需审核" },
  { value: "password", label: "口令", hint: "输入正确口令后可直接加入" },
  { value: "private", label: "私有", hint: "需提交申请，由队长审核通过后加入" },
];

function openCreate() {
  createName.value = "";
  createDesc.value = "";
  createKick.value = 10;
  createType.value = "public";
  createPassword.value = "";
  createErr.value = "";
  showCreate.value = true;
  nextTick(() => createNameRef.value?.focus());
}
function closeCreate() { showCreate.value = false; }

async function submitCreate() {
  const n = createName.value.trim();
  if (!n || createSubmitting.value) return;
  if (createType.value === "password" && !createPassword.value.trim()) {
    createErr.value = "请设置口令";
    return;
  }
  createSubmitting.value = true;
  createErr.value = "";
  try {
    await apiFetch("/teams", {
      method: "POST",
      body: {
        name: n,
        description: createDesc.value.trim(),
        auto_kick_miss_gt: createKick.value,
        team_type: createType.value,
        password: createType.value === "password" ? createPassword.value.trim() : "",
      },
    });
    closeCreate();
    await loadMine();
    await loadPlaza();
  } catch (e) {
    createErr.value = e instanceof ApiError ? e.detail : "创建失败";
  } finally {
    createSubmitting.value = false;
  }
}

/* ─── 小组广场 ──────────────────────────────────────────── */
const plazaList = ref<TeamCard[]>([]);
const plazaLoading = ref(false);
const plazaErr = ref("");
const searchQ = ref("");
let searchTimer: ReturnType<typeof setTimeout> | null = null;

/** 昨日（上海时间近似）YYYY-MM-DD */
function yesterdayStr(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

const yesterdayStats = ref<Record<string, Stat>>({});

async function loadYesterdayStats(teams: TeamCard[]) {
  const yest = yesterdayStr();
  await Promise.allSettled(
    teams.map(async (t) => {
      try {
        const s = await apiFetch<Stat>(`/teams/${t.team_id}/stats?period=day&anchor=${yest}`);
        yesterdayStats.value[t.team_id] = s;
      } catch { /* 静默失败 */ }
    })
  );
}

async function loadPlaza(q = searchQ.value, opts?: { silent?: boolean }) {
  const silent = opts?.silent === true && plazaList.value.length > 0;
  if (!silent) plazaLoading.value = true;
  plazaErr.value = "";
  try {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    plazaList.value = await apiFetch<TeamCard[]>(`/teams?${params.toString()}`);
    loadYesterdayStats(plazaList.value); // 异步加载昨日统计，不阻塞渲染
  } catch (e) {
    plazaErr.value = e instanceof ApiError ? e.detail : "加载失败";
  } finally {
    plazaLoading.value = false;
  }
}

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadPlaza(), 320);
}

function refreshCurrentTab(silent = true) {
  if (currentTab.value === "plaza") {
    void loadPlaza(searchQ.value, { silent });
  } else {
    void loadMine({ silent });
  }
}

/* ─── 切换 tab：有缓存则静默拉取 ─────────────────────────── */
watch(currentTab, () => refreshCurrentTab(true));

function onVisibilityChange() {
  if (document.visibilityState === "visible") refreshCurrentTab(true);
}

let activatedOnce = false;

onMounted(() => {
  refreshCurrentTab(false);
  document.addEventListener("visibilitychange", onVisibilityChange);
});

onActivated(() => {
  if (!activatedOnce) {
    activatedOnce = true;
    return;
  }
  refreshCurrentTab(true);
});

onUnmounted(() => {
  document.removeEventListener("visibilitychange", onVisibilityChange);
});
</script>

<template>
  <div class="teams">
    <!-- ══════════ 我的小组 ══════════ -->
    <template v-if="currentTab === 'mine'">
      <p v-if="myErr" class="err">{{ myErr }}</p>
      <p v-if="myLoading && myTeams.length === 0" class="muted center">载入中…</p>

      <!-- 已加入小组列表 -->
      <ul v-if="myTeams.length > 0" class="plaza-list">
        <li v-for="detail in myTeams" :key="detail.team.team_id" class="plaza-card">
          <div class="plaza-info">
            <div class="plaza-name-row">
              <span class="plaza-name-wrap">
                <p class="plaza-name">{{ detail.team.name }}</p>
                <span
                  v-if="detail.team.unread_count > 0"
                  class="unread-dot"
                  :aria-label="`${detail.team.unread_count} 条未读消息`"
                >
                  {{ formatUnreadCount(detail.team.unread_count) }}
                </span>
              </span>
            </div>
            <div class="plaza-meta">
              <span class="tag">{{ detail.team.member_count }} 人</span>
              <span class="type-tag" :class="`type-tag--${detail.team.team_type}`">
                {{ detail.team.team_type === 'public' ? '公开' : detail.team.team_type === 'password' ? '口令' : '私有' }}
              </span>
              <span v-if="showOwnerPendingTag(detail.team)" class="tag tag-pending">申请待处理</span>
            </div>
            <div class="plaza-yest">
              <template v-if="yesterdayStats[detail.team.team_id]">
                <span class="yest-item">
                  <span class="yest-label">昨日噜数</span>
                  <span class="yest-val">{{ yesterdayStats[detail.team.team_id].record_count }}</span>
                </span>
                <span class="yest-sep">·</span>
                <span class="yest-item">
                  <span class="yest-label">昨日噜率</span>
                  <span class="yest-val">{{ (yesterdayStats[detail.team.team_id].deer_rate * 100).toFixed(1) }}%</span>
                </span>
                <span class="yest-sep">·</span>
                <span class="yest-item">
                  <span class="yest-label">昨日打卡率</span>
                  <span class="yest-val">{{ (yesterdayStats[detail.team.team_id].check_in_rate * 100).toFixed(1) }}%</span>
                </span>
              </template>
              <span v-else class="yest-busy muted">—</span>
            </div>
          </div>
          <div class="plaza-action">
            <button
              type="button"
              class="card-arrow-btn"
              aria-label="进入聊天室"
              @click="router.push({ name: 'team-chat', params: { teamId: detail.team.team_id } })"
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">
                <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </li>
      </ul>

      <!-- 未加入任何小组 -->
      <section v-if="!myLoading && myTeams.length === 0" class="card empty-card">
        <div class="empty-icon">👥</div>
        <p class="empty-title">还没有加入小组</p>
        <p class="muted">点击右下角 + 创建小组，或前往小组广场搜索并申请加入</p>
      </section>

      <!-- FAB 创建按钮 -->
      <button type="button" class="fab" aria-label="创建小组" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" width="26" height="26" aria-hidden="true">
          <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
        </svg>
      </button>
    </template>

    <!-- ══════════ 小组广场 ══════════ -->
    <template v-if="currentTab === 'plaza'">
      <!-- 搜索框 -->
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 20 20" fill="none" width="16" height="16" aria-hidden="true">
          <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" stroke-width="1.6"/>
          <path d="M13.5 13.5L17 17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
        <input
          v-model="searchQ"
          type="search"
          class="search-input"
          placeholder="搜索小组名称"
          autocomplete="off"
          @input="onSearch"
        />
      </div>

      <p v-if="plazaErr" class="err">{{ plazaErr }}</p>
      <p v-if="plazaLoading && plazaList.length === 0" class="muted center">载入中…</p>
      <p v-if="!plazaLoading && plazaList.length === 0 && !plazaErr" class="muted center">暂无小组</p>

      <!-- 小组卡片列表 -->
      <ul class="plaza-list">
        <li v-for="t in plazaList" :key="t.team_id" class="plaza-card">
          <div class="plaza-info">
            <div class="plaza-name-row">
              <p class="plaza-name">{{ t.name }}</p>
            </div>
            <div class="plaza-meta">
              <span class="tag">{{ t.member_count }} 人</span>
              <span class="type-tag" :class="`type-tag--${t.team_type}`">
                {{ t.team_type === 'public' ? '公开' : t.team_type === 'password' ? '口令' : '私有' }}
              </span>
              <span v-if="showOwnerPendingTag(t)" class="tag tag-pending">申请待处理</span>
            </div>
            <!-- 昨日统计 -->
            <div class="plaza-yest">
              <template v-if="yesterdayStats[t.team_id]">
                <span class="yest-item">
                  <span class="yest-label">昨日噜数</span>
                  <span class="yest-val">{{ yesterdayStats[t.team_id].record_count }}</span>
                </span>
                <span class="yest-sep">·</span>
                <span class="yest-item">
                  <span class="yest-label">昨日噜率</span>
                  <span class="yest-val">{{ (yesterdayStats[t.team_id].deer_rate * 100).toFixed(1) }}%</span>
                </span>
                <span class="yest-sep">·</span>
                <span class="yest-item">
                  <span class="yest-label">昨日打卡率</span>
                  <span class="yest-val">{{ (yesterdayStats[t.team_id].check_in_rate * 100).toFixed(1) }}%</span>
                </span>
              </template>
              <span v-else class="yest-busy muted">—</span>
            </div>
          </div>
          <div class="plaza-action">
            <button
              type="button"
              class="card-arrow-btn"
              aria-label="查看详情"
              @click="openDetail(t)"
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">
                <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </li>
      </ul>
    </template>
  </div>

  <!-- ══════════ 小组详情弹框（居中） ══════════ -->
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="detailTeam" class="dialog-overlay" @click.self="closeDetail">
        <div class="dialog" role="dialog" aria-modal="true">
          <!-- 弹框头 -->
          <div class="dialog-header">
            <div class="dialog-title-row">
              <span class="dialog-title">{{ detailTeam.name }}</span>
              <span class="type-tag" :class="`type-tag--${detailTeam.team_type}`">
                {{ detailTeam.team_type === 'public' ? '公开' : detailTeam.team_type === 'password' ? '口令' : '私有' }}
              </span>
            </div>
            <button type="button" class="dialog-close" aria-label="关闭" @click="closeDetail">
              <svg viewBox="0 0 20 20" fill="none" width="18" height="18"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
            </button>
          </div>

          <div class="dialog-body">
            <TeamDetailPanel
              v-if="detailTeam"
              :key="detailTeam.team_id"
              :team-id="detailTeam.team_id"
              :team="detailTeam"
              embedded
              @team-updated="detailTeam = $event"
              @joined="onDetailJoined"
              @left="onDetailLeft"
            />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- ══════════ 创建小组弹层 ══════════ -->
  <Teleport to="body">
    <Transition name="sheet-fade">
      <div v-if="showCreate" class="sheet-overlay" @click.self="closeCreate">
        <div class="sheet" role="dialog" aria-modal="true" aria-label="创建小组">
          <div class="sheet-header">
            <button type="button" class="sheet-cancel" @click="closeCreate">取消</button>
            <span class="sheet-title">创建小组</span>
            <button
              type="button"
              class="sheet-submit"
              :disabled="createSubmitting || !createName.trim()"
              @click="submitCreate"
            >
              {{ createSubmitting ? "…" : "创建" }}
            </button>
          </div>
          <div class="sheet-body">
            <div class="field-block">
              <label class="field-label" for="create-name">小组名称</label>
              <input
                id="create-name"
                ref="createNameRef"
                v-model="createName"
                class="field-input"
                maxlength="32"
                placeholder="给你的小组起个名字"
                autocomplete="off"
              />
            </div>
            <div class="field-block">
              <label class="field-label" for="create-desc">小组简介</label>
              <textarea
                id="create-desc"
                v-model="createDesc"
                class="field-textarea"
                maxlength="200"
                rows="3"
                placeholder="介绍一下这个小组（可选）"
                autocomplete="off"
              />
            </div>
            <div class="field-block">
              <label class="field-label">小组类型</label>
              <div class="type-pills">
                <button
                  v-for="opt in typeOptions"
                  :key="opt.value"
                  type="button"
                  class="type-pill"
                  :class="{ active: createType === opt.value }"
                  @click="createType = opt.value"
                >
                  {{ opt.label }}
                </button>
              </div>
              <p class="type-hint muted">
                {{ typeOptions.find(o => o.value === createType)?.hint }}
              </p>
              <input
                v-if="createType === 'password'"
                v-model="createPassword"
                class="field-input"
                maxlength="32"
                placeholder="设置加入口令"
                autocomplete="off"
              />
            </div>
            <div class="field-block">
              <label class="field-label" for="create-kick">自然月缺卡天数上限</label>
              <div class="kick-row">
                <input
                  id="create-kick"
                  v-model.number="createKick"
                  class="field-input kick-input"
                  type="number"
                  min="0"
                  max="31"
                  autocomplete="off"
                />
                <span class="kick-unit muted">天（超出自动移出成员）</span>
              </div>
            </div>
            <p class="hint muted">小组榜仅统计 ≥10 人的队伍。</p>
            <p v-if="createErr" class="err">{{ createErr }}</p>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.teams {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-bottom: 80px;
}

/* ─── 通用 ─── */
.card {
  border-radius: var(--radius-lg);
  background: var(--card);
  border: 1px solid var(--card-border);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.muted {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.center {
  text-align: center;
  padding: 24px 0;
}

.err {
  color: var(--danger);
  font-size: 13px;
  margin: 0;
}

.mono-id {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: var(--muted);
  margin: 0;
}

.team-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text);
  white-space: pre-wrap;
}

.sm {
  font-size: 11px;
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

.btn.sm {
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 8px;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ─── 我的小组卡片 ─── */
.team-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.team-name {
  margin: 0 0 2px;
  font-size: 18px;
  font-weight: 800;
}

.info-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.label {
  display: inline-block;
  font-size: 11px;
  color: var(--muted);
  background: rgba(0, 0, 0, 0.05);
  border-radius: 6px;
  padding: 3px 8px;
}

/* ─── 统计 ─── */
.stat-section {
  border-top: 1px solid var(--card-border);
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.period-sel {
  width: 90px;
  flex-shrink: 0;
}

.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.stat-box {
  background: var(--bg);
  border-radius: 10px;
  padding: 10px 12px;
}

.stat-box.full {
  grid-column: 1 / -1;
}

.stat-label {
  margin: 0;
  font-size: 11px;
  color: var(--muted);
}

.stat-num {
  margin: 4px 0 0;
  font-size: 24px;
  font-weight: 900;
  color: var(--accent-b);
}

/* ─── 空状态 ─── */
.empty-card {
  align-items: center;
  text-align: center;
  padding: 32px 20px;
  gap: 8px;
}

.empty-icon {
  font-size: 40px;
  line-height: 1;
}

.empty-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

/* ─── FAB ─── */
.fab {
  position: fixed;
  right: 20px;
  bottom: calc(88px + var(--safe-bottom, 0px));
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--accent-a);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  transition: transform 0.15s, background 0.15s;
  z-index: 50;
  -webkit-tap-highlight-color: transparent;
}

.fab:active {
  transform: scale(0.93);
}

/* ─── 广场搜索 ─── */
.search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 0 12px;
}

.search-icon {
  flex-shrink: 0;
  color: var(--muted);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 11px 0;
  font-size: 14px;
  color: var(--text);
  outline: none;
}

.search-input::placeholder {
  color: var(--muted);
}

/* ─── 广场卡片列表 ─── */
.plaza-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.plaza-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
}

.plaza-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plaza-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plaza-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--muted);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.plaza-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.tag {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 6px;
  padding: 2px 7px;
}

.tag.muted {
  color: var(--muted);
  background: transparent;
  padding-left: 0;
}

.tag.tag-pending {
  font-weight: 700;
  color: #16a34a;
  background: rgba(22, 163, 74, 0.12);
}

.plaza-action {
  flex-shrink: 0;
}

.card-arrow-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--muted);
  border-radius: 8px;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
  transition: color 0.15s, background 0.15s;
}

.card-arrow-btn:active {
  background: rgba(0, 0, 0, 0.06);
  color: var(--text);
}

.joined-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-a);
  background: rgba(22, 163, 74, 0.1);
  border-radius: 8px;
  padding: 5px 10px;
}

.join-err {
  margin: 0;
  font-size: 11px;
  color: var(--danger);
}

/* ─── 小组类型标签（广场卡片 & 弹框） ─── */
.plaza-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}

.plaza-name-wrap {
  position: relative;
  display: inline-block;
  max-width: 100%;
}

.unread-dot {
  position: absolute;
  top: -10px;
  right: -25px;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ff4d72 0%, #ff2d55 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  line-height: 22px;
  text-align: center;
  white-space: nowrap;
  box-sizing: border-box;
  pointer-events: none;
  box-shadow:
    0 2px 6px rgba(255, 45, 85, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.28);
}

.type-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

.type-tag--public  { background: rgba(22, 163, 74, 0.12); color: #16a34a; }
.type-tag--password { background: rgba(234, 179, 8, 0.15); color: #b45309; }
.type-tag--private { background: rgba(139, 92, 246, 0.12); color: #7c3aed; }

/* 类型标签（我的小组） */
.label-public { color: #16a34a; background: rgba(22, 163, 74, 0.12); }
.label-password { color: #b45309; background: rgba(234, 179, 8, 0.15); }
.label-private { color: #7c3aed; background: rgba(139, 92, 246, 0.12); }

.pending-tag {
  font-size: 12px;
  font-weight: 700;
  color: #7c3aed;
  background: rgba(139, 92, 246, 0.12);
  border-radius: 8px;
  padding: 5px 10px;
}

/* ─── 广场卡片昨日统计 ─── */
.plaza-yest {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.yest-item {
  display: flex;
  align-items: center;
  gap: 3px;
}

.yest-label {
  font-size: 10px;
  color: var(--muted);
}

.yest-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--accent-b);
}

.yest-sep {
  font-size: 11px;
  color: var(--muted);
}

/* ─── 小组详情居中弹框 ─── */
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

.dialog {
  width: 100%;
  max-width: 460px;
  max-height: calc(100vh - 40px);
  max-height: calc(100dvh - 40px);
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
  gap: 10px;
}

.dialog-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.dialog-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-close {
  border: none;
  background: rgba(0,0,0,0.06);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  flex-shrink: 0;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.dialog-body {
  padding: 16px 18px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.dialog-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dialog-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  white-space: pre-wrap;
}

/* ─── 图表区 ─── */
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

/* ─── 柱状图 ─── */
.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 120px;
  padding-bottom: 24px; /* 日期标签空间 */
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

/* ─── 弹框底部操作区 ─── */
.dialog-action-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--card-border);
  padding-top: 14px;
}

.full-btn {
  width: 100%;
  padding: 13px;
  font-size: 15px;
  border-radius: 12px;
  text-align: center;
}

.full-label {
  display: block;
  text-align: center;
  padding: 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
}

/* ─── 弹框过渡动画 ─── */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-active .dialog,
.dialog-fade-leave-active .dialog,
.dialog-fade-enter-active .confirm-dialog,
.dialog-fade-leave-active .confirm-dialog {
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-from .dialog,
.dialog-fade-leave-to .dialog,
.dialog-fade-enter-from .confirm-dialog,
.dialog-fade-leave-to .confirm-dialog {
  transform: scale(0.92);
}

/* ─── 退出 / 解散确认弹框 ─── */
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

/* ─── 创建弹层类型选择 ─── */
.type-pills {
  display: flex;
  gap: 8px;
}

.type-pill {
  flex: 1;
  padding: 9px 4px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.type-pill.active {
  color: var(--accent-a);
  border-color: rgba(2, 132, 199, 0.5);
  background: rgba(2, 132, 199, 0.08);
}

.type-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
}

/* ─── 创建弹层 ─── */
.sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: var(--safe-bottom, 0);
}

.sheet {
  width: 100%;
  max-width: 480px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-bottom: none;
  border-radius: 22px 22px 0 0;
  display: flex;
  flex-direction: column;
  max-height: 88vh;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.10);
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}

.sheet-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
}

.sheet-cancel {
  border: none;
  background: none;
  font-size: 15px;
  font-weight: 600;
  color: var(--muted);
  padding: 4px 0;
  min-width: 44px;
  text-align: left;
}

.sheet-submit {
  border: none;
  background: none;
  font-size: 15px;
  font-weight: 700;
  color: var(--accent-a);
  padding: 4px 0;
  min-width: 44px;
  text-align: right;
  transition: opacity 0.15s;
}

.sheet-submit:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.sheet-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.field-input {
  width: 100%;
  padding: 11px 14px;
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  font-size: 15px;
  outline: none;
  transition: border-color 0.18s;
  box-sizing: border-box;
}

.field-input:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.field-textarea {
  width: 100%;
  padding: 11px 14px;
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  font-size: 15px;
  line-height: 1.55;
  resize: none;
  outline: none;
  transition: border-color 0.18s;
  box-sizing: border-box;
}

.field-textarea:focus {
  border-color: rgba(2, 132, 199, 0.4);
}

.kick-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kick-input {
  width: 80px;
}

.kick-unit {
  font-size: 13px;
}

.hint {
  font-size: 12px;
  line-height: 1.6;
}

/* ─── 动画 ─── */
.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.22s ease;
}

.sheet-fade-enter-active .sheet,
.sheet-fade-leave-active .sheet {
  transition: transform 0.22s cubic-bezier(0.32, 0.72, 0, 1);
}

.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
}

.sheet-fade-enter-from .sheet,
.sheet-fade-leave-to .sheet {
  transform: translateY(100%);
}
</style>
