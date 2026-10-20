import { computed, ref } from "vue";
import { apiFetch } from "../api/client";
import { checkInDaysMap } from "./checkIns";
import { useAuth } from "./auth";

export interface LuRecord {
  id: string;
  timestamp: number; // ms since epoch
  date: string;      // YYYY-MM-DD
  note: string;
}

interface ApiRecord {
  record_id: string;
  user_id: string;
  timestamp: string; // ISO8601
  date: string;
  note: string;
  created_at: string;
}

function toLocal(r: ApiRecord): LuRecord {
  return {
    id: r.record_id,
    timestamp: new Date(r.timestamp).getTime(),
    date: r.date,
    note: r.note,
  };
}

function formatShanghaiDate(d: Date): string {
  if (isNaN(d.getTime())) return "";
  const adjusted = new Date(d.getTime() + 8 * 60 * 60 * 1000);
  const y = adjusted.getUTCFullYear();
  const m = String(adjusted.getUTCMonth() + 1).padStart(2, "0");
  const day = String(adjusted.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function today(): string {
  return formatShanghaiDate(new Date());
}

function accountJoinDate(createdAt?: string | null): string {
  if (!createdAt) return today();
  return formatShanghaiDate(new Date(createdAt));
}

function prevLocalDay(dateStr: string): string {
  const parts = dateStr.split("-");
  if (parts.length === 3) {
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    const d = new Date(Date.UTC(y, m, day));
    d.setUTCDate(d.getUTCDate() - 1);
    const ry = d.getUTCFullYear();
    const rm = String(d.getUTCMonth() + 1).padStart(2, "0");
    const rd = String(d.getUTCDate()).padStart(2, "0");
    return `${ry}-${rm}-${rd}`;
  }
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return formatShanghaiDate(d);
}

/* ── 模块级单例状态 ── */
const records = ref<LuRecord[]>([]);
const loading = ref(false);
let _fetched = false; // 避免重复拉取

async function fetchRecords(force = false): Promise<void> {
  if (_fetched && !force) return;
  loading.value = true;
  try {
    const data = await apiFetch<ApiRecord[]>("/records?limit=1000");
    records.value = data.map(toLocal);
    _fetched = true;
  } finally {
    loading.value = false;
  }
}

export { fetchRecords };

/** 用户退出时重置状态，供 auth logout 调用 */
export function resetRecords(): void {
  records.value = [];
  _fetched = false;
}

/* ── 统计计算（与原版逻辑一致） ── */

function countOnDate(date: string): number {
  return records.value.filter((r) => r.date === date).length;
}

export function countByDay(n = 7): { date: string; count: number }[] {
  const result: { date: string; count: number }[] = [];
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const date = formatShanghaiDate(d);
    result.push({ date, count: countOnDate(date) });
  }
  return result;
}

export function countByWeek(n = 6): { label: string; count: number }[] {
  const result: { label: string; count: number }[] = [];
  for (let i = n - 1; i >= 0; i--) {
    const end = new Date();
    end.setDate(end.getDate() - i * 7);
    const start = new Date(end);
    start.setDate(start.getDate() - 6);
    let count = 0;
    for (let j = 0; j <= 6; j++) {
      const d = new Date(start);
      d.setDate(d.getDate() + j);
      count += countOnDate(formatShanghaiDate(d));
    }
    result.push({ label: `${start.getMonth() + 1}/${start.getDate()}`, count });
  }
  return result;
}

export function countByMonth(n = 6): { label: string; count: number }[] {
  const result: { label: string; count: number }[] = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const prefix = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const count = records.value.filter((r) => r.date.startsWith(prefix)).length;
    result.push({ label: `${d.getMonth() + 1}月`, count });
  }
  return result;
}

/** 最近 n 个自然年（含本年），从早到晚排列 */
export function countByYear(n = 6): { year: number; label: string; count: number }[] {
  const result: { year: number; label: string; count: number }[] = [];
  const currentYear = new Date().getFullYear();
  for (let i = n - 1; i >= 0; i--) {
    const y = currentYear - i;
    const count = records.value.filter((r) => r.date.startsWith(`${y}-`)).length;
    result.push({ year: y, label: `${y}年`, count });
  }
  return result;
}

export const recentFrequency = computed(() => {
  const days = countByDay(7);
  const total = days.reduce((s, d) => s + Math.min(d.count, 1), 0);
  return total / 7;
});

/* ── useRecords ── */

export function useRecords() {
  const { user } = useAuth();

  const streakDays = computed(() => {
    const recordDates = new Set(records.value.map((r) => r.date));
    const todayStr = today();
    const checkIns = checkInDaysMap.value;

    // 今天已噜（行为记录或打卡）则连续自律归零
    if (recordDates.has(todayStr) || checkIns[todayStr] === "deer") return 0;

    const joinDate = accountJoinDate(user.value?.created_at);
    let count = 0;
    let check: string;

    // 今天打卡「没噜」且无行为记录 → 计入连续自律
    if (checkIns[todayStr] === "none" && !recordDates.has(todayStr)) {
      count = 1;
      check = prevLocalDay(todayStr);
    } else {
      check = prevLocalDay(todayStr);
    }

    while (check >= joinDate) {
      const checkIn = checkIns[check];
      if (checkIn !== "none" || recordDates.has(check)) break;
      count++;
      check = prevLocalDay(check);
    }
    return count;
  });

  async function addRecord(): Promise<void> {
    const now = new Date();
    const data = await apiFetch<ApiRecord>("/records", {
      method: "POST",
      body: { timestamp: now.toISOString(), note: "" },
    });
    records.value = [toLocal(data), ...records.value];
  }

  /** 为指定上海日历日新增一条噜记录（补卡「噜了」用） */
  async function addRecordForDate(localDate: string): Promise<void> {
    const timestamp = `${localDate}T12:00:00+08:00`;
    const data = await apiFetch<ApiRecord>("/records", {
      method: "POST",
      body: { timestamp, note: "" },
    });
    records.value = [toLocal(data), ...records.value];
  }

  async function removeRecord(id: string): Promise<void> {
    await apiFetch<null>(`/records/${id}`, { method: "DELETE" });
    records.value = records.value.filter((r) => r.id !== id);
  }

  async function removeLatest(): Promise<void> {
    if (records.value.length === 0) return;
    const latest = records.value[0];
    await removeRecord(latest.id);
  }

  async function updateNote(id: string, note: string): Promise<void> {
    await apiFetch<ApiRecord>(`/records/${id}`, {
      method: "PATCH",
      body: { note },
    });
    records.value = records.value.map((r) => (r.id === id ? { ...r, note } : r));
  }

  const todayCount = computed(() => countOnDate(today()));

  return {
    records,
    loading,
    fetchRecords,
    addRecord,
    addRecordForDate,
    removeRecord,
    removeLatest,
    updateNote,
    streakDays,
    todayCount,
    recentFrequency,
    countByDay,
    countByWeek,
    countByMonth,
    countByYear,
  };
}
