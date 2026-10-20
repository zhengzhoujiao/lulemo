<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { apiFetch, ApiError } from "../api/client";

interface UserItem {
  user_id: string;
  account: string;
  nickname: string;
  nickname_tag: number;
  register_seq: number;
  display_name: string;
  role: number;
  identity_role: string;
  created_at: string;
  region: { province_name: string; city_name: string; district_name: string } | null;
}

const router = useRouter();
const loading = ref(true);
const users = ref<UserItem[]>([]);
const error = ref("");

const identityLabels: Record<string, string> = {
  balanced: "均衡",
  sigma: "西格玛",
  chaos: "混沌",
  monk: "僧侣",
  pure_love: "纯爱",
};

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function regionText(r: UserItem["region"]): string {
  if (!r) return "—";
  const parts = [r.province_name, r.city_name, r.district_name].filter(Boolean);
  return parts.length ? parts.join(" ") : "—";
}

async function loadUsers() {
  loading.value = true;
  error.value = "";
  try {
    users.value = await apiFetch<UserItem[]>("/users?limit=500");
  } catch (e) {
    if (e instanceof ApiError && e.status === 403) {
      router.replace("/settings");
      return;
    }
    error.value = e instanceof Error ? e.message : "加载失败";
  } finally {
    loading.value = false;
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/settings");
  }
}

onMounted(loadUsers);
</script>

<template>
  <div class="admin-users-page">
    <header class="page-topbar">
      <button type="button" class="back-btn" aria-label="返回" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" width="22" height="22" aria-hidden="true">
          <path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <h1 class="topbar-title">用户列表</h1>
      <span class="topbar-spacer" aria-hidden="true" />
    </header>

    <div class="page-body">
      <p v-if="loading" class="status-hint">加载中…</p>
      <p v-else-if="error" class="status-hint error">{{ error }}</p>
      <p v-else-if="users.length === 0" class="status-hint">暂无用户</p>

      <div v-else class="user-list">
        <div
          v-for="(u, i) in users"
          :key="u.user_id"
          class="user-card"
          :style="{ animationDelay: `${i * 30}ms` }"
        >
          <div class="user-avatar" aria-hidden="true">{{ u.display_name.slice(0, 1) }}</div>
          <div class="user-info">
            <div class="user-top-row">
              <span class="user-name">{{ u.display_name }}</span>
              <span v-if="u.role === 1" class="badge badge-admin">管理员</span>
              <span v-if="u.register_seq > 0 && u.register_seq <= 100" class="badge badge-veteran">元老</span>
            </div>
            <div class="user-detail-row">
              <span class="user-field">账号：{{ u.account }}</span>
              <span class="user-field">身份：{{ identityLabels[u.identity_role] ?? u.identity_role }}</span>
            </div>
            <div class="user-detail-row">
              <span class="user-field">地区：{{ regionText(u.region) }}</span>
              <span class="user-field">注册：{{ fmtDate(u.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-users-page {
  min-height: 100%;
  max-width: 560px;
  margin: 0 auto;
  padding-bottom: calc(24px + var(--safe-bottom, 0px));
}

.page-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: grid;
  grid-template-columns: 40px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: calc(10px + var(--safe-top, 0px)) 12px 10px;
  background: rgba(241, 245, 249, 0.92);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border-bottom: 1px solid var(--card-border);
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text);
  -webkit-tap-highlight-color: transparent;
}

.back-btn:active {
  background: rgba(0, 0, 0, 0.06);
}

.topbar-title {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--text);
}

.topbar-spacer {
  width: 36px;
}

.page-body {
  padding: 12px 10px;
}

.status-hint {
  text-align: center;
  color: var(--muted);
  font-size: 14px;
  margin: 24px 0;
}

.status-hint.error {
  color: var(--danger);
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: var(--card);
  border: 1px solid var(--card-border);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
  animation: card-in 0.35s ease both;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--card);
  border: 1px solid var(--card-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}

.user-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-top-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.user-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.badge {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
  letter-spacing: 0.05em;
}

.badge-admin {
  color: #b45309;
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.badge-veteran {
  color: #8b6914;
  background: linear-gradient(180deg, #fff8e7 0%, #f5e6b8 100%);
  border: 1px solid #c9a227;
}

.user-detail-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.user-field {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}
</style>
