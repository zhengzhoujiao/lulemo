<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppTopBar from "../../components/AppTopBar.vue";
import TeamDetailPanel, { type TeamCard } from "../../components/TeamDetailPanel.vue";

const route = useRoute();
const router = useRouter();
const teamId = route.params.teamId as string;
const team = ref<TeamCard | null>(null);

function onLeft() {
  router.back();
}
</script>

<template>
  <div class="team-detail-page">
    <AppTopBar>
      <template #leading>
        <button type="button" class="icon-btn" aria-label="返回" @click="router.back()">
          <svg viewBox="0 0 24 24" fill="none" width="22" height="22" aria-hidden="true">
            <path d="M14 6l-6 6 6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </template>
      <template #title>
        <span class="page-title">
          聊天信息（{{ team?.member_count ?? "…" }}）
        </span>
      </template>
    </AppTopBar>

    <main class="detail-body">
      <TeamDetailPanel
        :team-id="teamId"
        variant="menu"
        @team-loaded="team = $event"
        @left="onLeft"
      />
    </main>
  </div>
</template>

<style scoped>
.team-detail-page {
  min-height: 100vh;
  min-height: 100dvh;
  min-height: 100svh;
  background: var(--bg);
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 10px;
  color: var(--text);
  -webkit-tap-highlight-color: transparent;
}

.icon-btn:active {
  background: rgba(0, 0, 0, 0.06);
}

.page-title {
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.04em;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-body {
  max-width: 560px;
  margin: 0 auto;
  padding-top: var(--app-topbar-h);
}
</style>
