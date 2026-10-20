<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useIdentity } from "../stores/identity";
import { fetchDiscipline } from "../stores/discipline";
import { useRecords } from "../stores/records";
import {
  refreshTodayStatus,
  todayCheckInStatus,
  upsertCheckIn,
} from "../stores/checkIns";
import coinLu from "../assets/images/噜.png";
import coinNot from "../assets/images/不噜.png";

type Verdict = "none" | "lu" | "not";
type CoinPhase = "idle" | "spinning-lu" | "spinning-not" | "lu" | "not";

const { activeRole } = useIdentity();
const { addRecord } = useRecords();

const verdict = ref<Verdict>("none");
const busy = ref(false);
const followMessage = ref("");
const coinPhase = ref<CoinPhase>("idle");

const LS_VERDICT = "lulemo:today:verdict";

onMounted(() => {
  refreshTodayStatus().catch(() => {});
  const v = localStorage.getItem(LS_VERDICT);
  if (v === "lu" || v === "not") {
    verdict.value = v;
    coinPhase.value = v;
    followMessage.value = pickFollow(v);
  }
});

watch(verdict, (v) => {
  if (v === "none") localStorage.removeItem(LS_VERDICT);
  else localStorage.setItem(LS_VERDICT, v);
});

const verdictHint = computed(() => {
  if (verdict.value === "none") return "按下按钮，让命运替你做决定。";
  return "想再来一次？那就再抛一次。";
});

/** 今日已打卡（噜了或没噜） */
const hasCheckedInToday = computed(() => todayCheckInStatus.value !== null);

/** 噜：始终显示；不噜：未打卡时显示，动画播放期间保持可见 */
const showSyncButton = computed(() => {
  if (verdict.value === "lu") return true;
  if (verdict.value === "not") return !hasCheckedInToday.value || syncBump.value === "not";
  return false;
});

function pickFollow(v: Exclude<Verdict, "none">): string {
  const luPool = [
    "记得温柔对待自己：适度、放松、注意卫生与休息。",
    "今天把节奏放慢一点，给身体一点恢复时间。",
    "把它当作释放压力的一种方式，但别让它变成负担。",
    "享受当下，之后记得多喝水、好好休息。",
  ];
  const notPool = [
    "把精力留给运动、睡眠或一件小事的完成感。",
    "给身体一个缓冲日，明天再决定也不迟。",
    "试试转移注意力：散步、音乐、整理房间都很加分。",
    "今天积攒的能量，留着做些更有意义的事吧。",
  ];
  const pool = v === "lu" ? luPool : notPool;
  return pool[Math.floor(Math.random() * pool.length)]!;
}

function roll() {
  if (busy.value) return;
  busy.value = true;
  verdict.value = "none";

  const p = activeRole.value.luProbability;
  const next: Exclude<Verdict, "none"> = Math.random() < p ? "lu" : "not";

  coinPhase.value = next === "lu" ? "spinning-lu" : "spinning-not";

  window.setTimeout(() => {
    verdict.value = next;
    coinPhase.value = next;
    followMessage.value = pickFollow(next);
    busy.value = false;
  }, 1400);
}

const syncing = ref(false);
const syncBump = ref<"lu" | "not" | null>(null);
let syncBumpTimer: ReturnType<typeof setTimeout> | null = null;

function flashSyncBump(kind: "lu" | "not") {
  syncBump.value = kind;
  if (syncBumpTimer) clearTimeout(syncBumpTimer);
  syncBumpTimer = setTimeout(() => {
    syncBump.value = null;
    syncBumpTimer = null;
  }, 1800);
}

async function syncToRecord() {
  if (syncing.value || verdict.value === "none") return;
  syncing.value = true;
  try {
    if (verdict.value === "lu") {
      await upsertCheckIn("deer", null);
      await addRecord();
      flashSyncBump("lu");
      await refreshTodayStatus();
      await fetchDiscipline(true);
    } else if (verdict.value === "not") {
      await upsertCheckIn("none", null);
      flashSyncBump("not");
      await refreshTodayStatus();
      await fetchDiscipline(true);
    }
  } finally {
    syncing.value = false;
  }
}

function clearVerdict() {
  verdict.value = "none";
  coinPhase.value = "idle";
  followMessage.value = "";
}
</script>

<template>
  <div class="page">
    <div class="card">
      <!-- 顶部 badge -->
      <div class="tag-row">
        <div class="tag">
          <span class="dot" aria-hidden="true" />
          <span>犹豫不决？交给天意</span>
        </div>
        <span class="role-tag">身份：{{ activeRole.label }}</span>
      </div>

      <!-- 硬币展示区 -->
      <div class="coin-wrap" aria-live="polite">
        <p class="coin-kicker">抛个硬币</p>

        <div class="coin-stage">
          <div class="coin" :class="`coin--${coinPhase}`">
            <!-- 正面：不噜 -->
            <div class="coin-face coin-face--front">
              <img :src="coinNot" alt="不噜" class="coin-img" draggable="false" />
            </div>
            <!-- 反面：噜 -->
            <div class="coin-face coin-face--back">
              <img :src="coinLu" alt="噜" class="coin-img" draggable="false" />
            </div>
          </div>
        </div>

        <p class="coin-hint">{{ verdictHint }}</p>

        <transition name="fade-up">
          <p v-if="verdict !== 'none'" class="follow">{{ followMessage }}</p>
        </transition>

        <div v-if="showSyncButton" class="sync-row">
          <button
            type="button"
            class="sync-btn"
            :disabled="syncing"
            @click="syncToRecord"
          >
            {{ syncing ? "记录中…" : "记录到噜了么" }}
          </button>
          <Transition name="sync-bump-fade">
            <span
              v-if="syncBump"
              class="sync-bump"
              :class="syncBump === 'lu' ? 'sync-bump--lu' : 'sync-bump--not'"
            >
              {{ syncBump === "lu" ? "噜+1" : "不噜+1" }}
            </span>
          </Transition>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <button
          type="button"
          class="btn primary"
          :disabled="busy"
          @click="roll"
        >
          {{ busy ? "硬币翻转中…" : verdict === "none" ? "交给天意" : "再抛一次" }}
        </button>
        <button
          v-if="verdict !== 'none'"
          type="button"
          class="btn ghost"
          :disabled="busy"
          @click="clearVerdict"
        >
          清空
        </button>
      </div>

      <p class="footer-note">结果按身份概率随机抽取，仅供娱乐与自我参考。</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  padding: 8px 8px 100px;
  max-width: 560px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-intro {
  margin: 0 0 4px;
}

.lead {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
  font-size: 14px;
}

.lead strong {
  color: var(--text);
  font-weight: 700;
}

.lead .active-label {
  color: var(--accent-b);
}

.card {
  width: 100%;
  border-radius: 12px;
  padding: 15px 15px 15px;
  background: var(--card);
  border: 1px solid var(--card-border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.07);
}

.tag-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid var(--card-border);
  color: var(--muted);
  font-size: 12px;
}

.role-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent-b) 35%, transparent);
  background: color-mix(in srgb, var(--accent-b) 12%, transparent);
  color: var(--accent-b);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--accent-b);
}

/* ── 硬币容器 ── */
.coin-wrap {
  margin-top: 4px;
  padding: 20px 16px 16px;
  border-radius: var(--radius-lg);
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid var(--card-border);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.coin-kicker {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}

.coin-hint {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

/* ── 3D 舞台 ── */
.coin-stage {
  perspective: 700px;
  width: 180px;
  height: 180px;
}

.coin {
  width: 180px;
  height: 180px;
  position: relative;
  transform-style: preserve-3d;
  transform: rotateY(0deg);
  transition: none;
}

/* 两面公共样式 */
.coin-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.coin-face--front {
  transform: rotateY(0deg);
}

.coin-face--back {
  transform: rotateY(180deg);
}

.coin-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  user-select: none;
  /* 空闲时略灰，有待抛出的感觉 */
  filter: saturate(0.85) brightness(0.95);
  transition: filter 0.3s;
}

/* 结果落定后图片恢复原色 */
.coin--lu .coin-img,
.coin--not .coin-img {
  filter: saturate(1) brightness(1);
}

/* ── 动画：旋转到不噜（正面，0deg） ── */
@keyframes spin-to-not {
  from { transform: rotateY(0deg); }
  to   { transform: rotateY(1080deg); } /* 6×180 = 正面 */
}

/* ── 动画：旋转到噜（反面，180deg） ── */
@keyframes spin-to-lu {
  from { transform: rotateY(0deg); }
  to   { transform: rotateY(900deg); } /* 5×180 = 反面 */
}

.coin--spinning-not {
  animation: spin-to-not 1.4s cubic-bezier(0.2, 0.8, 0.4, 1) forwards;
}

.coin--spinning-lu {
  animation: spin-to-lu 1.4s cubic-bezier(0.2, 0.8, 0.4, 1) forwards;
}

/* 结果定格（无缝衔接动画终态，transition: none 防止跳变） */
.coin--not {
  transform: rotateY(0deg);
  transition: none;
}

.coin--lu {
  transform: rotateY(180deg);
  transition: none;
}

/* 结果定格后的轻微弹动入场 */
.coin--not,
.coin--lu {
  animation: coin-land 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes coin-land {
  0%   { scale: 1; }
  50%  { scale: 1.06; }
  100% { scale: 1; }
}

/* ── 跟随文案 ── */
.follow {
  margin: 0;
  padding-top: 10px;
  border-top: 1px dashed rgba(0, 0, 0, 0.12);
  color: var(--text);
  line-height: 1.65;
  font-size: 13px;
  text-align: left;
  width: 100%;
}

.sync-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.sync-bump {
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
  line-height: 1;
}

.sync-bump--lu {
  color: var(--accent-a);
}

.sync-bump--not {
  color: var(--muted);
}

.sync-bump-fade-enter-active,
.sync-bump-fade-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.sync-bump-fade-enter-from,
.sync-bump-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.sync-btn {
  background: rgba(22, 163, 74, 0.08);
  border: 1px solid rgba(22, 163, 74, 0.32);
  color: var(--accent-a);
  border-radius: 10px;
  padding: 7px 16px;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s, transform 0.1s;
}

.sync-btn:hover {
  background: rgba(22, 163, 74, 0.14);
}

.sync-btn:active:not(:disabled) {
  transform: scale(0.96);
}

.sync-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── 操作按钮 ── */
.actions {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.btn {
  width: 100%;
  border-radius: 14px;
  padding: 14px;
  border: 1px solid transparent;
  font-weight: 800;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: opacity 0.2s, transform 0.1s;
}

.btn:active:not(:disabled) {
  transform: scale(0.98);
}

.btn.primary {
  color: #fff;
  border: 0;
  background: var(--accent-a);
}

.btn.primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn.ghost {
  background: rgba(0, 0, 0, 0.04);
  border-color: rgba(0, 0, 0, 0.10);
  color: var(--muted);
}

.footer-note {
  margin: 12px 0 0;
  color: var(--muted);
  opacity: 0.75;
  font-size: 11px;
  line-height: 1.55;
  text-align: center;
}

/* 过渡动画 */
.fade-up-enter-active {
  transition: opacity 0.35s ease, transform 0.35s ease;
}
.fade-up-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
</style>
