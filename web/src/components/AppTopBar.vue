<script setup lang="ts">
defineProps<{
  title?: string;
}>();
</script>

<template>
  <header class="app-topbar" role="banner">
    <div class="app-topbar-inner">
      <div v-if="$slots.leading" class="leading">
        <slot name="leading" />
      </div>
      <div class="brand">
        <slot name="title">
          <h1 v-if="title" class="title">{{ title }}</h1>
        </slot>
      </div>
      <div v-if="$slots.trailing" class="trailing">
        <slot name="trailing" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding: calc(10px + var(--safe-top, 0px)) 14px 10px;
  background: rgba(241, 245, 249, 0.90);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border-bottom: 1px solid var(--card-border);
}

.app-topbar-inner {
  max-width: 560px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 32px;
}

.leading {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.brand {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.title {
  margin: 0;
  font-size: 18px;
  font-weight: 900;
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
}

.trailing {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
