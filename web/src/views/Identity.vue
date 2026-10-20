<script setup lang="ts">
import { ref } from "vue";
import { useIdentity } from "../stores/identity";

const { roles, activeRole, setRole } = useIdentity();
const settingRole = ref(false);

async function handleSetRole(id: Parameters<typeof setRole>[0]) {
  if (settingRole.value) return;
  settingRole.value = true;
  try {
    await setRole(id);
  } finally {
    settingRole.value = false;
  }
}
</script>

<template>
  <div class="page">
    <div class="impact-note">
      <svg class="note-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10 9v5M10 7v.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
      <p>选择你的身份，影响「今日噜么」里随机到「噜」的概率。当前身份：<strong class="active-label">{{ activeRole.label }}</strong></p>
    </div>
    <section class="list" role="list">
      <button
        v-for="role in roles"
        :key="role.id"
        type="button"
        class="role"
        :class="{ active: activeRole.id === role.id }"
        role="listitem"
        :disabled="settingRole"
        @click="handleSetRole(role.id)"
      >
        <div class="role-emoji" aria-hidden="true">{{ role.emoji }}</div>
        <div class="role-body">
          <div class="role-head">
            <span class="role-name">{{ role.label }}</span>
            <span class="role-pill" :class="{ 'pill-active': activeRole.id === role.id }">
              噜率 {{ Math.round(role.luProbability * 100) }}%
            </span>
          </div>
          <p class="role-desc">{{ role.description }}</p>
          <p class="role-flavor">{{ role.flavor }}</p>
        </div>
        <div v-if="activeRole.id === role.id" class="check-mark" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.5"/>
            <path d="M6.5 10.5l2.5 2.5 5-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </button>
    </section>
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

.active-label {
  color: var(--accent-b);
  font-weight: 700;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.role {
  width: 100%;
  text-align: left;
  border-radius: var(--radius-lg);
  padding: 14px;
  background: var(--card);
  border: 1px solid var(--card-border);
  color: var(--text);
  display: flex;
  align-items: flex-start;
  gap: 14px;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease,
    transform 0.08s ease;
  position: relative;
}

.role:active {
  transform: translateY(1px);
}

.role.active {
  border-color: rgba(2, 132, 199, 0.45);
  background: rgba(2, 132, 199, 0.06);
}

.role-emoji {
  font-size: 36px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.role-body {
  flex: 1;
  min-width: 0;
}

.role-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 5px;
}

.role-name {
  font-size: 16px;
  font-weight: 700;
}

.role-pill {
  font-size: 11px;
  color: var(--muted);
  border: 1px solid var(--card-border);
  padding: 3px 8px;
  border-radius: 999px;
  white-space: nowrap;
  flex-shrink: 0;
}

.role-pill.pill-active {
  color: var(--accent-b);
  border-color: rgba(2, 132, 199, 0.32);
  background: rgba(2, 132, 199, 0.08);
}

.role-desc {
  margin: 0 0 4px;
  font-size: 14px;
  color: var(--text);
  font-weight: 500;
}

.role-flavor {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.55;
}

.check-mark {
  width: 20px;
  height: 20px;
  color: var(--accent-b);
  flex-shrink: 0;
  margin-top: 2px;
}

.check-mark svg {
  width: 100%;
  height: 100%;
}

.impact-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  border-radius: var(--radius-md);
  background: rgba(2, 132, 199, 0.06);
  border: 1px solid rgba(2, 132, 199, 0.14);
  padding: 12px 14px;
}

.note-icon {
  width: 18px;
  height: 18px;
  color: var(--accent-b);
  flex-shrink: 0;
  margin-top: 1px;
}

.impact-note p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}
</style>
