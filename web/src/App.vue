<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, RouterLink, RouterView } from "vue-router";
import AppTopBar from "./components/AppTopBar.vue";
import BottomNav from "./components/BottomNav.vue";
import settingsIcon from "./assets/images/设置.png";
import { useAuth } from "./stores/auth";

const route = useRoute();
const { bootstrapSession, isLoggedIn } = useAuth();

const showShell = computed(() => route.name !== "auth");
const hideTopBar = computed(() => route.meta.hideTopBar === true);
const hideBottomNav = computed(() => route.meta.hideBottomNav === true);

const pageTitle = computed(() => {
  const t = route.meta.title;
  if (typeof t === "string" && t) return t;
  if (route.path.startsWith("/social")) return "社交";
  return "噜了么";
});

onMounted(async () => {
  if (isLoggedIn.value) {
    await bootstrapSession();
  }
});
</script>

<template>
  <div class="app-shell">
    <AppTopBar v-if="showShell && !hideTopBar" :title="pageTitle">
      <template #trailing>
        <RouterLink to="/settings" class="settings-btn" aria-label="设置">
          <img :src="settingsIcon" alt="" class="settings-btn-icon" width="22" height="22" />
        </RouterLink>
      </template>
    </AppTopBar>
    <main
      class="app-main"
      :class="{
        'with-topbar': showShell && !hideTopBar,
        'auth-main': !showShell,
        'full-page': hideTopBar,
      }"
    >
      <RouterView />
    </main>
    <BottomNav v-if="showShell && !hideBottomNav" />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
  min-height: 0;
  padding-bottom: 88px;
}

.app-main.with-topbar {
  padding-top: calc(var(--app-topbar-h) + var(--safe-top, 0px) + 8px);
}

.app-main.full-page {
  padding-top: 0;
  padding-bottom: 0;
}

.app-main.auth-main {
  padding-bottom: 0;
  display: flex;
  flex-direction: column;
}

.settings-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.15s, background 0.15s;
  -webkit-tap-highlight-color: transparent;
}

.settings-btn:active,
.settings-btn.router-link-active {
  background: rgba(2, 132, 199, 0.1);
}

.settings-btn-icon {
  display: block;
  width: 22px;
  height: 22px;
  object-fit: contain;
}
</style>
