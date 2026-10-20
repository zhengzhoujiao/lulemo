<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";
import coinIcon from "../assets/images/抛硬币.png";
import coinIconActive from "../assets/images/抛硬币action.png";
import cardIcon from "../assets/images/card.png";
import cardIconActive from "../assets/images/cardAction.png";

const route = useRoute();

const items = [
  { to: "/", label: "噜了么", exact: true },
  { to: "/today", label: "今日噜么" },
  { to: "/identity", label: "选择身份" },
  { to: "/social/teams", label: "社交" },
];

function isActive(path: string, exact?: boolean) {
  if (exact) return route.path === path;
  if (path.startsWith("/social")) return route.path.startsWith("/social");
  return route.path.startsWith(path);
}
</script>

<template>
  <nav class="nav" aria-label="主导航">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="nav-item"
      :class="{ active: isActive(item.to, item.exact) }"
    >
      <!-- 噜了么：柱状图图标 -->
      <svg v-if="item.to === '/'" class="nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="14" width="4" height="7" rx="1.5" fill="currentColor" opacity="0.5"/>
        <rect x="10" y="9" width="4" height="12" rx="1.5" fill="currentColor" opacity="0.75"/>
        <rect x="17" y="4" width="4" height="17" rx="1.5" fill="currentColor"/>
      </svg>
      <!-- 今日噜么：抛硬币 -->
      <img
        v-else-if="item.to === '/today'"
        :src="isActive(item.to) ? coinIconActive : coinIcon"
        class="nav-icon nav-icon-img"
        alt=""
        aria-hidden="true"
      />
      <!-- 选择身份：卡牌 -->
      <img
        v-else-if="item.to === '/identity'"
        :src="isActive(item.to) ? cardIconActive : cardIcon"
        class="nav-icon nav-icon-img"
        alt=""
        aria-hidden="true"
      />
      <!-- 社交：气泡图标 -->
      <svg v-else class="nav-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M4 17.5V18a2 2 0 0 0 2 2h1.5v2l4-2H18a4 4 0 0 0 4-4V10a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v3.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
        <circle cx="9.5" cy="11.5" r="1.1" fill="currentColor"/>
        <circle cx="13" cy="11.5" r="1.1" fill="currentColor"/>
        <circle cx="16.5" cy="11.5" r="1.1" fill="currentColor"/>
      </svg>
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  padding: 8px 8px calc(8px + var(--safe-bottom));
  background: rgba(241, 245, 249, 0.90);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border-top: 1px solid var(--card-border);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 4px 6px;
  border-radius: var(--radius-md);
  color: var(--muted);
  text-decoration: none;
  font-size: 11px;
  font-weight: 600;
  transition:
    color 0.18s ease,
    background 0.18s ease;
}

.nav-icon {
  width: 25px;
  height: 25px;
  transition: transform 0.18s ease;
}

.nav-icon-img {
  object-fit: contain;
}

.nav-item.active {
  color: var(--text);
  background: rgba(56, 189, 248, 0.1);
}

.nav-item.active .nav-icon {
  color: var(--accent-b);
  transform: translateY(-1px);
}

.nav-item:active .nav-icon {
  transform: scale(0.9);
}
</style>
