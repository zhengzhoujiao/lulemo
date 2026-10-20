import { computed, ref } from "vue";
import { apiFetch } from "../api/client";
import { isLoggedIn, syncUserIdentityRole } from "./auth";

export type IdentityRoleId =
  | "balanced"
  | "sigma"
  | "chaos"
  | "monk"
  | "pure_love";

export interface IdentityRole {
  id: IdentityRoleId;
  label: string;
  emoji: string;
  /** 随机到「噜」的概率，0–1 */
  luProbability: number;
  description: string;
  flavor: string;
}

const ROLES_RAW: IdentityRole[] = [
  {
    id: "balanced",
    label: "平常心",
    emoji: "😐",
    luProbability: 0.5,
    description: "一半一半，交给命运。",
    flavor: "不执着于结果，顺其自然，今天怎样都好。",
  },
  {
    id: "sigma",
    label: "西格玛男人",
    emoji: "😎",
    luProbability: 0.1,
    description: "自律拉满，几乎不噜。",
    flavor: "真·西格玛只专注于自身的成长。",
  },
  {
    id: "chaos",
    label: "混沌乐子人",
    emoji: "🤪",
    luProbability: 0.8,
    description: "世界很大，先噜为敬。",
    flavor: "规则是什么？不存在的。今日份快乐必须有。",
  },
  {
    id: "monk",
    label: "修行僧",
    emoji: "🧘",
    luProbability: 0.25,
    description: "闭关清修，偶尔破戒。",
    flavor: "色即是空，空……等等，今天好像不太空。",
  },
  {
    id: "pure_love",
    label: "纯爱战神",
    emoji: "💘",
    luProbability: 0.05,
    description: "手留给未来那个人。",
    flavor: "心中有情，手上自律。恋爱脑，但很有原则的那种。",
  },
];

const ROLES = [...ROLES_RAW].sort((a, b) => a.luProbability - b.luProbability);

const STORAGE_KEY = "lulemo:identity-role";

const stored = localStorage.getItem(STORAGE_KEY) as IdentityRoleId | null;
const storedValid = stored && ROLES.some((r) => r.id === stored);

const activeId = ref<IdentityRoleId>(storedValid ? stored! : "balanced");

function normalizeRole(role: string): IdentityRoleId {
  return ROLES.some((r) => r.id === role) ? (role as IdentityRoleId) : "balanced";
}

/** 登录后用服务端角色初始化（不触发 API 同步） */
export function initIdentityFromServer(role: string): void {
  const valid = normalizeRole(role);
  activeId.value = valid;
  localStorage.setItem(STORAGE_KEY, valid);
}

export function useIdentity() {
  const roles = ROLES;

  const activeRole = computed(
    () => ROLES.find((r) => r.id === activeId.value) ?? ROLES[0],
  );

  async function setRole(id: IdentityRoleId): Promise<void> {
    activeId.value = id;
    localStorage.setItem(STORAGE_KEY, id);
    syncUserIdentityRole(id);

    if (isLoggedIn.value) {
      try {
        await apiFetch("/users/me/identity", {
          method: "PUT",
          body: { identity_role: id },
        });
      } catch {
        // 静默失败：本地已更新，下次登录时服务端会以本地为准
      }
    }
  }

  return { roles, activeRole, setRole };
}
