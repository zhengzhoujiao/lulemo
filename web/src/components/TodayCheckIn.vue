<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ApiError } from "../api/client";
import { useRecords } from "../stores/records";
import {
  refreshTodayStatus,
  todayCheckInStatus,
  todayShanghai,
  upsertCheckIn,
  fetchCheckInMonth,
  type CheckInStatus,
  type CheckInMonth,
} from "../stores/checkIns";

const emit = defineEmits<{ deerDone: []; backfillDone: [] }>();

const { addRecord, addRecordForDate, todayCount } = useRecords();

const chkBusy = ref(false);
const chkMsg = ref("");
const bfMsg = ref("");
const justRecorded = ref(false);
/** 点击过噜+1 后隐藏「没噜」 */
const hideNoneBtn = ref(false);

/* ── 今日状态 ── */
const hasDeer = computed(() => todayCheckInStatus.value === "deer");
const hasNone = computed(() => todayCheckInStatus.value === "none");
const hasPunched = computed(() => hasDeer.value || hasNone.value);
const showNoneBtn = computed(() => !hideNoneBtn.value && !hasDeer.value);

onMounted(async () => {
  await refreshTodayStatus().catch(() => {});
  if (hasDeer.value) hideNoneBtn.value = true;
});

async function punchTodayDeer() {
  if (chkBusy.value) return;
  hideNoneBtn.value = true;
  chkBusy.value = true;
  chkMsg.value = "";
  try {
    if (!hasDeer.value) {
      await upsertCheckIn("deer", null);
      await refreshTodayStatus();
    }
    await addRecord();
    justRecorded.value = true;
    setTimeout(() => (justRecorded.value = false), 1800);
    emit("deerDone");
  } catch (e) {
    chkMsg.value = e instanceof ApiError ? e.detail : "记录失败，请稍后重试";
  } finally {
    chkBusy.value = false;
  }
}

async function punchTodayNone() {
  if (chkBusy.value || hasPunched.value) return;
  chkBusy.value = true;
  chkMsg.value = "";
  try {
    await upsertCheckIn("none", null);
    await refreshTodayStatus();
  } catch (e) {
    chkMsg.value = e instanceof ApiError ? e.detail : "打卡失败，请稍后重试";
  } finally {
    chkBusy.value = false;
  }
}

/* ─────────────────────────────────────────────
   补卡弹层 + 日历
───────────────────────────────────────────── */
const showBfModal = ref(false);

/** 当前展示年月 */
const bfYear = ref(0);
const bfMonth = ref(0); // 1-12

/** 补卡已选日期 YYYY-MM-DD */
const bfSelected = ref("");

/** 当前展示月的打卡记录 */
const bfCalData = ref<CheckInMonth | null>(null);
const bfCalLoading = ref(false);

/** 上海今日 */
const todayStr = todayShanghai();

function getShanghaiComponents(d: Date = new Date()) {
  const adjusted = new Date(d.getTime() + 8 * 60 * 60 * 1000);
  return {
    year: adjusted.getUTCFullYear(),
    month: adjusted.getUTCMonth() + 1,
    day: adjusted.getUTCDate(),
  };
}

function formatShanghaiDate(d: Date): string {
  const { year, month, day } = getShanghaiComponents(d);
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

/** 90 天前限制 */
const minDateStr = (() => {
  const d = new Date();
  d.setDate(d.getDate() - 90);
  return formatShanghaiDate(d);
})();

function openBfModal() {
  const { year, month } = getShanghaiComponents(new Date());
  bfYear.value = year;
  bfMonth.value = month;
  bfSelected.value = "";
  bfMsg.value = "";
  showBfModal.value = true;
  loadBfMonth();
}

function closeBfModal() {
  showBfModal.value = false;
}

async function loadBfMonth() {
  bfCalLoading.value = true;
  try {
    bfCalData.value = await fetchCheckInMonth(bfYear.value, bfMonth.value);
  } catch {
    bfCalData.value = null;
  } finally {
    bfCalLoading.value = false;
  }
}

function prevMonth() {
  if (bfMonth.value === 1) { bfYear.value--; bfMonth.value = 12; }
  else { bfMonth.value--; }
  bfSelected.value = "";
  loadBfMonth();
}

function nextMonth() {
  const { year: curY, month: curM } = getShanghaiComponents(new Date());
  if (bfYear.value === curY && bfMonth.value === curM) return;
  if (bfMonth.value === 12) { bfYear.value++; bfMonth.value = 1; }
  else { bfMonth.value++; }
  bfSelected.value = "";
  loadBfMonth();
}

const isAtCurrentMonth = computed(() => {
  const { year: curY, month: curM } = getShanghaiComponents(new Date());
  return bfYear.value === curY && bfMonth.value === curM;
});

interface CalDay {
  date: string;
  day: number;
  status: CheckInStatus | null;
  isToday: boolean;
  isSelected: boolean;
  /** 在 90 天内且未打卡，可补卡 */
  isPending: boolean;
  selectable: boolean;
}

const calDays = computed((): CalDay[] => {
  const year = bfYear.value;
  const month = bfMonth.value;
  if (!year || !month) return [];

  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const rows: CalDay[] = [];

  const startOffset = (firstDay + 6) % 7;
  for (let i = 0; i < startOffset; i++) {
    rows.push({
      date: "",
      day: 0,
      status: null,
      isToday: false,
      isSelected: false,
      isPending: false,
      selectable: false,
    });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const mm = String(month).padStart(2, "0");
    const dd = String(d).padStart(2, "0");
    const date = `${year}-${mm}-${dd}`;
    const inRange = date >= minDateStr && date <= todayStr;
    const rawStatus = bfCalData.value?.days[date];
    const status = rawStatus === "deer" || rawStatus === "none" ? rawStatus : null;
    const isPending = inRange && status === null;
    rows.push({
      date,
      day: d,
      status,
      isToday: date === todayStr,
      isSelected: date === bfSelected.value,
      isPending,
      selectable: isPending,
    });
  }
  return rows;
});

function selectDay(cell: CalDay) {
  if (!cell.selectable) return;
  bfSelected.value = cell.date === bfSelected.value ? "" : cell.date;
  bfMsg.value = "";
}

async function bfPunch(status: CheckInStatus) {
  if (!bfSelected.value || chkBusy.value) return;
  chkBusy.value = true;
  bfMsg.value = "";
  const picked = bfSelected.value;
  try {
    await upsertCheckIn(status, picked);
    if (status === "deer") {
      await addRecordForDate(picked);
      if (picked === todayStr) {
        hideNoneBtn.value = true;
        justRecorded.value = true;
        setTimeout(() => (justRecorded.value = false), 1800);
      }
      emit("deerDone");
    }
    await loadBfMonth();
    if (picked === todayStr) await refreshTodayStatus();
    bfSelected.value = "";
    emit("backfillDone");
  } catch (e) {
    bfMsg.value = e instanceof ApiError ? e.detail : "补卡失败，请稍后重试";
  } finally {
    chkBusy.value = false;
  }
}

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
</script>

<template>
  <div class="check-in-wrap">
    <!-- 今日打卡卡片 -->
    <div class="today-card">
      <div class="card-header">
        <span class="header-label">今日打卡</span>
        <button type="button" class="bf-trigger" @click="openBfModal">
          <svg viewBox="0 0 16 16" fill="none" width="13" height="13" aria-hidden="true">
            <rect x="1" y="2" width="14" height="13" rx="2" stroke="currentColor" stroke-width="1.3"/>
            <path d="M5 1v2M11 1v2M1 6h14" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
            <path d="M8 9v3M6.5 10.5h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          补卡
        </button>
      </div>

      <!-- 次数 -->
      <div class="count-row">
        <span class="today-count">{{ todayCount }}</span>
        <span class="today-unit">次记录</span>
      </div>

      <!-- 操作按钮：没噜为主操作，噜+1弱化 -->
      <div class="action-row">
        <button
          v-if="showNoneBtn"
          type="button"
          class="record-btn none"
          :class="{ done: hasNone }"
          :disabled="chkBusy || hasNone"
          @click="punchTodayNone"
        >
          <template v-if="hasNone">已记录</template>
          <template v-else>没噜</template>
        </button>
        <button
          type="button"
          class="record-btn deer"
          :class="{ recorded: justRecorded }"
          :disabled="chkBusy"
          @click="punchTodayDeer"
        >
          {{ chkBusy ? "…" : "噜+1" }}
        </button>
      </div>

      <p v-if="chkMsg" class="chk-msg">{{ chkMsg }}</p>
    </div>

    <!-- 补卡弹层 -->
    <Teleport to="body">
      <Transition name="modal-fade">
        <div v-if="showBfModal" class="bf-overlay" @click.self="closeBfModal">
          <div class="bf-modal" role="dialog" aria-modal="true" aria-label="补卡日历">
            <!-- 弹层头部 -->
            <div class="modal-header">
              <span class="modal-title">补卡</span>
              <button type="button" class="modal-close" @click="closeBfModal" aria-label="关闭">
                <svg viewBox="0 0 16 16" fill="none" width="16" height="16">
                  <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
              </button>
            </div>

            <p class="modal-hint">可补最近 90 天，仅「待补卡」日期可选</p>

            <!-- 月份导航 -->
            <div class="month-nav">
              <button type="button" class="nav-arrow" @click="prevMonth">
                <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
                  <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
              <span class="month-label">{{ bfYear }} 年 {{ bfMonth }} 月</span>
              <button type="button" class="nav-arrow" :disabled="isAtCurrentMonth" @click="nextMonth">
                <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
                  <path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>

            <!-- 星期头 -->
            <div class="cal-weekdays">
              <span v-for="w in WEEKDAYS" :key="w" class="wd-cell">{{ w }}</span>
            </div>

            <!-- 日历格子 -->
            <div class="cal-grid" :class="{ busy: bfCalLoading }">
              <button
                v-for="(cell, i) in calDays"
                :key="i"
                type="button"
                class="cal-cell"
                :class="{
                  'cell-empty': !cell.date,
                  'cell-today': cell.isToday,
                  'cell-selected': cell.isSelected,
                  'cell-deer': cell.status === 'deer',
                  'cell-none': cell.status === 'none',
                  'cell-pending': cell.isPending && !cell.isSelected,
                  'cell-muted': !!cell.date && !cell.isPending && !cell.status,
                }"
                :disabled="!cell.selectable"
                @click="selectDay(cell)"
              >
                <span v-if="cell.date">{{ cell.day }}</span>
              </button>
            </div>

            <!-- 图例 -->
            <div class="cal-legend">
              <span class="legend-item"><span class="dot dot-none" />没噜</span>
              <span class="legend-item"><span class="dot dot-deer" />噜了</span>
              <span class="legend-item"><span class="dot dot-pending" />待补卡</span>
            </div>

            <!-- 已选日期操作 -->
            <Transition name="confirm-slide">
              <div v-if="bfSelected" class="bf-confirm">
                <span class="confirm-date">{{ bfSelected }}</span>
                <div class="confirm-actions">
                  <button
                    type="button"
                    class="cf-btn cf-none"
                    :disabled="chkBusy"
                    @click="bfPunch('none')"
                  >没噜</button>
                  <button
                    type="button"
                    class="cf-btn cf-deer"
                    :disabled="chkBusy"
                    @click="bfPunch('deer')"
                  >噜了</button>
                </div>
              </div>
            </Transition>

            <p v-if="bfMsg" class="chk-msg">{{ bfMsg }}</p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.check-in-wrap {
  min-width: 0;
}

/* ── 今日卡片 ── */
.today-card {
  border-radius: var(--radius-lg);
  background: var(--card);
  border: 1px solid var(--card-border);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.header-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.bf-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--card-border);
  background: rgba(0,0,0,0.04);
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  transition: color 0.15s, border-color 0.15s;
}

.bf-trigger:hover {
  color: var(--text);
  border-color: rgba(2, 132, 199, 0.4);
}

/* ── 次数行 ── */
.count-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.today-count {
  font-size: 34px;
  font-weight: 900;
  color: var(--accent-b);
  line-height: 1;
}

.today-unit {
  font-size: 11px;
  color: var(--muted);
}

/* ── 操作按钮 ── */
.action-row {
  display: flex;
  gap: 6px;
}

.record-btn {
  flex: 1;
  border-radius: 10px;
  padding: 8px 6px;
  font-size: 13px;
  font-weight: 700;
  border: none;
  transition: opacity 0.2s, transform 0.1s;
  white-space: nowrap;
}

.record-btn.none {
  background: var(--accent-a);
  color: #fff;
  border: 1px solid transparent;
}

.record-btn.none.done {
  color: var(--accent-a);
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(34, 197, 94, 0.12);
}

.record-btn.none:hover:not(:disabled) {
  filter: brightness(1.05);
}

.record-btn.deer {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--danger);
}

.record-btn.deer:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.16);
}

.record-btn.deer.recorded {
  background: rgba(239, 68, 68, 0.2);
}

.record-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.record-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.chk-msg {
  margin: 0;
  font-size: 11px;
  color: var(--accent-b);
  line-height: 1.45;
}

/* ─────────────────────────────────────────────
   补卡弹层
───────────────────────────────────────────── */
.bf-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0 0 var(--safe-bottom, 0);
}

.bf-modal {
  width: 100%;
  max-width: 480px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-bottom: none;
  border-radius: 22px 22px 0 0;
  padding: 20px 18px 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 90vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  box-shadow: 0 -4px 24px rgba(0,0,0,0.10);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: 17px;
  font-weight: 800;
}

.modal-close {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid var(--card-border);
  background: rgba(0,0,0,0.05);
  color: var(--muted);
  transition: color 0.15s;
}

.modal-close:hover { color: var(--text); }

.modal-hint {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}

/* 月份导航 */
.month-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.month-label {
  font-size: 15px;
  font-weight: 700;
  flex: 1;
  text-align: center;
}

.nav-arrow {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid var(--card-border);
  background: rgba(0,0,0,0.04);
  color: var(--text);
  transition: background 0.15s;
}

.nav-arrow:hover:not(:disabled) { background: rgba(0,0,0,0.08); }
.nav-arrow:disabled { opacity: 0.35; cursor: default; }

/* 星期标题 */
.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 3px;
  text-align: center;
}

.wd-cell {
  font-size: 11px;
  color: var(--muted);
  padding: 4px 0;
  font-weight: 600;
}

/* 日历格子 */
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  transition: opacity 0.2s;
}

.cal-grid.busy {
  opacity: 0.4;
  pointer-events: none;
}

.cal-cell {
  aspect-ratio: 1;
  border-radius: 8px;
  border: 1px solid transparent;
  background: rgba(0,0,0,0.04);
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  cursor: pointer;
}

.cal-cell.cell-empty {
  background: transparent;
  cursor: default;
  border-color: transparent;
}

.cal-cell.cell-pending {
  background: rgba(2, 132, 199, 0.10);
  color: var(--accent-b);
  border-color: rgba(2, 132, 199, 0.28);
  cursor: pointer;
}

.cal-cell.cell-muted {
  color: rgba(100, 116, 139, 0.4);
  background: transparent;
  cursor: default;
}

.cal-cell.cell-today {
  border-color: rgba(2,132,199,0.4);
  color: var(--accent-b);
}

.cal-cell.cell-deer {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
  border-color: rgba(239, 68, 68, 0.28);
}

.cal-cell.cell-none {
  background: rgba(34, 197, 94, 0.18);
  color: var(--accent-a);
  border-color: rgba(34, 197, 94, 0.35);
}

.cal-cell.cell-selected {
  border-color: var(--accent-b) !important;
  background: rgba(2,132,199,0.14) !important;
  color: var(--text) !important;
  box-shadow: 0 0 0 2px rgba(2,132,199,0.14);
}

.cal-cell:hover:not(:disabled):not(.cell-empty):not(.cell-muted) {
  background: rgba(0,0,0,0.08);
}

/* 图例 */
.cal-legend {
  display: flex;
  gap: 14px;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--muted);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-deer { background: #f87171; }
.dot-none { background: var(--accent-a); }
.dot-pending { background: var(--accent-b); }

/* 确认操作区 */
.bf-confirm {
  border-radius: 14px;
  background: rgba(2,132,199,0.06);
  border: 1px solid rgba(2,132,199,0.18);
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.confirm-date {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent-b);
}

.confirm-actions {
  display: flex;
  gap: 8px;
}

.cf-btn {
  padding: 7px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 800;
  border: 1px solid transparent;
  transition: opacity 0.2s, transform 0.1s;
}

.cf-btn:active { transform: scale(0.97); }
.cf-btn:disabled { opacity: 0.5; }

.cf-none {
  background: var(--accent-a);
  color: #fff;
}

.cf-deer {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: var(--danger);
}

/* ── 弹层动画 ── */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.22s ease;
}
.modal-fade-enter-active .bf-modal,
.modal-fade-leave-active .bf-modal {
  transition: transform 0.22s cubic-bezier(0.32, 0.72, 0, 1);
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .bf-modal,
.modal-fade-leave-to .bf-modal {
  transform: translateY(100%);
}

/* 确认区滑入 */
.confirm-slide-enter-active,
.confirm-slide-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.confirm-slide-enter-from,
.confirm-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
