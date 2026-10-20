import { ref } from "vue";
import { apiFetch } from "../api/client";

export interface DisciplineStat {
  eligible: boolean;
  window_days: number;
  check_in_days: number;
  required_check_in_days: number;
  score: number | null;
  percentile: number | null;
  active_user_count: number;
  calculated_at: string | null;
}

const stat = ref<DisciplineStat | null>(null);
const loading = ref(false);
let _fetched = false;

export async function fetchDiscipline(force = false): Promise<void> {
  if (_fetched && !force) return;
  loading.value = true;
  try {
    stat.value = await apiFetch<DisciplineStat>("/discipline/me");
    _fetched = true;
  } finally {
    loading.value = false;
  }
}

export function resetDiscipline(): void {
  stat.value = null;
  _fetched = false;
}

export function useDiscipline() {
  return {
    stat,
    loading,
    fetchDiscipline,
  };
}
