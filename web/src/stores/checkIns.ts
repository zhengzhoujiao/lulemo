import { ref } from "vue";
import { apiFetch } from "../api/client";

export type CheckInStatus = "deer" | "none";
export type TodayCheckInStatus = CheckInStatus | null;

export interface CheckInMonth {
  year: number;
  month: number;
  days: Record<string, CheckInStatus>;
}

/** 上海日历日 YYYY-MM-DD（与后端 dates_cn 一致） */
export function todayShanghai(): string {
  const d = new Date();
  const adjusted = new Date(d.getTime() + 8 * 60 * 60 * 1000);
  const y = adjusted.getUTCFullYear();
  const m = String(adjusted.getUTCMonth() + 1).padStart(2, "0");
  const day = String(adjusted.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const _todayStatus = ref<TodayCheckInStatus>(null);
/** 近期打卡（供首页图表合并「补卡噜了」等无 records 的日期） */
const _checkInDaysMap = ref<Record<string, CheckInStatus>>({});

export const todayCheckInStatus = _todayStatus;
export const checkInDaysMap = _checkInDaysMap;

function shanghaiYearMonth(): { year: number; month: number } {
  const d = new Date();
  const adjusted = new Date(d.getTime() + 8 * 60 * 60 * 1000);
  return {
    year: adjusted.getUTCFullYear(),
    month: adjusted.getUTCMonth() + 1,
  };
}

/** 拉取最近若干自然月打卡，写入 checkInDaysMap */
export async function loadRecentCheckIns(monthCount = 7): Promise<void> {
  let { year, month } = shanghaiYearMonth();
  const merged: Record<string, CheckInStatus> = {};
  for (let i = 0; i < monthCount; i++) {
    try {
      const cal = await fetchCheckInMonth(year, month);
      Object.assign(merged, cal.days);
    } catch {
      /* 单月失败不阻断 */
    }
    month -= 1;
    if (month < 1) {
      month = 12;
      year -= 1;
    }
  }
  _checkInDaysMap.value = merged;
  const today = todayShanghai();
  const s = merged[today];
  _todayStatus.value = s === "deer" || s === "none" ? s : null;
}

export function statusText(status: TodayCheckInStatus): string {
  if (status === "deer") return "今日打卡：噜了";
  if (status === "none") return "今日打卡：没噜";
  return "今日打卡：未打卡";
}

export async function fetchCheckInMonth(year: number, month: number): Promise<CheckInMonth> {
  const q = new URLSearchParams({ year: String(year), month: String(month) });
  return apiFetch<CheckInMonth>(`/check-ins/month?${q.toString()}`);
}

export async function upsertCheckIn(
  status: CheckInStatus,
  localDate?: string | null,
): Promise<void> {
  await apiFetch("/check-ins", {
    method: "POST",
    body: {
      status,
      local_date: localDate && localDate.trim() ? localDate.trim() : null,
    },
  });
}

export async function refreshTodayStatus(): Promise<TodayCheckInStatus> {
  const now = new Date();
  const adjusted = new Date(now.getTime() + 8 * 60 * 60 * 1000);
  const year = adjusted.getUTCFullYear();
  const month = adjusted.getUTCMonth() + 1;
  const today = todayShanghai();

  try {
    const cal = await fetchCheckInMonth(year, month);
    _checkInDaysMap.value = { ..._checkInDaysMap.value, ...cal.days };
    const s = cal.days[today];
    _todayStatus.value = s === "deer" || s === "none" ? s : null;
  } catch {
    _todayStatus.value = null;
  }
  return _todayStatus.value;
}

/** 退出 / 切换账号时清空打卡缓存 */
export function resetCheckIns(): void {
  _todayStatus.value = null;
  _checkInDaysMap.value = {};
}
