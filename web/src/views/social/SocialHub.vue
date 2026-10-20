<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { useRoute } from "vue-router";

const route = useRoute();

const hideSubnav = computed(() => route.meta.hideSubnav === true);
const isTeamsRoute = computed(() => route.path === "/social/teams");
const teamTab = computed(() => (route.query.teamTab === "plaza" ? "plaza" : "mine"));

const tabs = [
  { to: "/social/plaza", label: "七嘴八舌" },
  { to: "/social/teams", label: "小组" },
  { to: "/social/rank", label: "排名" },
];
const teamTabs = [
  { key: "mine", label: "我的小组" },
  { key: "plaza", label: "小组广场" },
] as const;

function tabActive(path: string) {
  return route.path === path;
}
</script>

<template>
  <div class="social-shell" :class="{ 'social-shell--flat': hideSubnav }">
    <div v-if="!hideSubnav" class="subnav">
      <div class="subnav-main">
        <RouterLink
          v-for="t in tabs"
          :key="t.to"
          :to="t.to"
          class="pill"
          :class="{ active: tabActive(t.to) }"
        >
          {{ t.label }}
        </RouterLink>
      </div>
      <div v-if="isTeamsRoute" class="subnav-team">
        <RouterLink
          v-for="t in teamTabs"
          :key="t.key"
          :to="{ path: '/social/teams', query: { ...route.query, teamTab: t.key } }"
          class="team-pill"
          :class="{ active: teamTab === t.key }"
        >
          {{ t.label }}
        </RouterLink>
      </div>
    </div>
    <RouterView v-slot="{ Component }">
      <keep-alive :include="['SocialPlaza', 'SocialTeams', 'SocialRank']">
        <component :is="Component" />
      </keep-alive>
    </RouterView>
  </div>
</template>

<style scoped>
.social-shell {
  min-height: 100%;
  padding: 6px 6px;
  max-width: 560px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.social-shell--flat {
  padding: 0;
  max-width: none;
  margin: 0;
  gap: 0;
  min-height: 100%;
}
.subnav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px;
  border-radius: 12px;
  background: var(--card);
  border: 1px solid var(--card-border);
}

.subnav-main,
.subnav-team {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  scrollbar-width: none;
}

.subnav-main::-webkit-scrollbar,
.subnav-team::-webkit-scrollbar {
  display: none;
}
.pill {
  flex: 1;
  min-width: 0;
  text-align: center;
  padding: 7px 8px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  border: 1px solid transparent;
  color: var(--muted);
  background: transparent;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}
.pill.active {
  color: var(--text);
  background: var(--bg);
  border-color: rgba(2, 132, 199, 0.18);
  box-shadow: 0 1px 4px rgba(2, 132, 199, 0.12);
}
.pill:active {
  transform: scale(0.98);
}

.team-pill {
  flex: 1;
  min-width: 0;
  text-align: center;
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  border: 1px solid transparent;
  color: var(--muted);
  background: rgba(0, 0, 0, 0.03);
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}

.team-pill.active {
  color: var(--text);
  background: var(--bg);
  border-color: rgba(2, 132, 199, 0.22);
}
</style>
