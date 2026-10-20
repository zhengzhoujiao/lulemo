import { computed, ref } from "vue";
import { apiFetch, ApiError, getStoredToken, saveToken, removeToken } from "../api/client";
import { resetCheckIns, loadRecentCheckIns } from "./checkIns";
import { fetchDiscipline, resetDiscipline } from "./discipline";
import { initIdentityFromServer } from "./identity";
import { resetRecords, fetchRecords } from "./records";

export type IdentityRoleId =
  | "balanced"
  | "sigma"
  | "chaos"
  | "monk"
  | "pure_love";

/** 注册时提交到后端的行政区划 */
export interface UserRegionPayload {
  province_code: string;
  city_code: string;
  district_code: string;
  province_name: string;
  city_name: string;
  district_name: string;
}

export interface UserInfo {
  user_id: string;
  account: string;
  nickname: string;
  nickname_tag: number;
  register_seq: number;
  display_name: string;
  role: number;
  identity_role: IdentityRoleId;
  created_at: string;
  region?: UserRegionPayload | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  account: string;
  nickname: string;
  nickname_tag: number;
  register_seq: number;
  display_name: string;
  role: number;
  identity_role: string;
}

const LS_TODAY_VERDICT = "lulemo:today:verdict";

/* ── 模块级单例状态 ── */
const _token = ref<string | null>(getStoredToken());
const _user = ref<UserInfo | null>(null);

export const isLoggedIn = computed(() => !!_token.value);

/** role === 1 为管理员（与后端 UserInDB.role 一致） */
export const isAdmin = computed(() => (_user.value?.role ?? 0) === 1);

function applyTokenResponse(data: TokenResponse): void {
  _token.value = data.access_token;
  saveToken(data.access_token);
  _user.value = {
    user_id: data.user_id,
    account: data.account,
    nickname: data.nickname,
    nickname_tag: data.nickname_tag,
    register_seq: data.register_seq ?? 0,
    display_name: data.display_name,
    role: data.role ?? 0,
    identity_role: data.identity_role as IdentityRoleId,
    created_at: "",
    region: null,
  };
}

function clearUserLocalStorage(): void {
  localStorage.removeItem(LS_TODAY_VERDICT);
}

/** 登录 / 注册 / 刷新后拉取当前用户数据与各模块缓存 */
export async function bootstrapSession(): Promise<boolean> {
  if (!_token.value) return false;

  const ok = await fetchMeInternal();
  if (!ok) return false;

  if (_user.value?.identity_role) {
    initIdentityFromServer(_user.value.identity_role);
  }

  resetRecords();
  resetCheckIns();
  resetDiscipline();

  await Promise.all([
    fetchRecords(true),
    loadRecentCheckIns(),
    fetchDiscipline(true),
  ]);
  return true;
}

async function fetchMeInternal(): Promise<boolean> {
  if (!_token.value) return false;
  try {
    const data = await apiFetch<UserInfo>("/auth/me");
    _user.value = data;
    return true;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      logout();
    }
    return false;
  }
}

/** 切换身份后同步用户信息中的 identity_role（与 identity store 一致） */
export function syncUserIdentityRole(id: IdentityRoleId): void {
  if (_user.value) {
    _user.value = { ..._user.value, identity_role: id };
  }
}

export function logout(): void {
  _token.value = null;
  _user.value = null;
  removeToken();
  resetRecords();
  resetCheckIns();
  resetDiscipline();
  clearUserLocalStorage();
}

export function useAuth() {
  async function register(
    account: string,
    nickname: string,
    password: string,
    region: UserRegionPayload,
  ): Promise<void> {
    const data = await apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: { account, nickname, password, region },
      token: null,
    });
    applyTokenResponse(data);
    await bootstrapSession();
  }

  async function login(account: string, password: string): Promise<void> {
    const data = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: { account, password },
      token: null,
    });
    applyTokenResponse(data);
    await bootstrapSession();
  }

  /** 用已有 token 拉取用户信息（应用启动时调用） */
  async function fetchMe(): Promise<boolean> {
    return fetchMeInternal();
  }

  return {
    token: _token,
    user: _user,
    isLoggedIn,
    isAdmin,
    register,
    login,
    logout,
    fetchMe,
    bootstrapSession,
  };
}
