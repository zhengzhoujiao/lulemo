<script setup lang="ts">
import { computed, ref } from "vue";

export interface MobileSelectOption {
  value: string;
  label: string;
}

const model = defineModel<string>({ required: true });

const props = defineProps<{
  label: string;
  options: MobileSelectOption[];
  sheetTitle?: string;
  disabled?: boolean;
}>();

const showSheet = ref(false);

const selectedLabel = computed(
  () => props.options.find((o) => o.value === model.value)?.label ?? "请选择",
);

function openSheet() {
  if (props.disabled) return;
  showSheet.value = true;
}

function closeSheet() {
  showSheet.value = false;
}

function pick(value: string) {
  model.value = value;
  closeSheet();
}
</script>

<template>
  <div class="mobile-select">
    <span class="field-label">{{ label }}</span>
    <button
      type="button"
      class="trigger"
      :class="{ disabled }"
      :disabled="disabled"
      :aria-label="`${label}：${selectedLabel}`"
      @click="openSheet"
    >
      <span class="trigger-text">{{ selectedLabel }}</span>
      <svg class="chevron" viewBox="0 0 16 16" fill="none" width="16" height="16" aria-hidden="true">
        <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <Teleport to="body">
      <Transition name="sheet-fade">
        <div v-if="showSheet" class="sheet-overlay" @click.self="closeSheet">
          <div class="sheet" role="dialog" aria-modal="true" :aria-label="sheetTitle ?? label">
            <div class="sheet-header">
              <span class="sheet-title">{{ sheetTitle ?? label }}</span>
              <button type="button" class="sheet-close" aria-label="关闭" @click="closeSheet">
                <svg viewBox="0 0 24 24" fill="none" width="20" height="20" aria-hidden="true">
                  <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </div>

            <ul class="option-list" role="listbox" :aria-label="sheetTitle ?? label">
              <li v-for="opt in options" :key="opt.value" role="presentation">
                <button
                  type="button"
                  class="option-item"
                  role="option"
                  :aria-selected="model === opt.value"
                  :class="{ active: model === opt.value }"
                  @click="pick(opt.value)"
                >
                  <span>{{ opt.label }}</span>
                  <svg
                    v-if="model === opt.value"
                    class="check"
                    viewBox="0 0 16 16"
                    fill="none"
                    width="16"
                    height="16"
                    aria-hidden="true"
                  >
                    <path d="M3.5 8.5l3 3 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </li>
            </ul>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.mobile-select {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.field-label {
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
}

.trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 9px 10px;
  border-radius: 10px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--text);
  font-size: 13px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s;
  -webkit-tap-highlight-color: transparent;
}

.trigger:active:not(:disabled) {
  background: rgba(0, 0, 0, 0.07);
}

.trigger:disabled,
.trigger.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.trigger-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  flex-shrink: 0;
  color: var(--muted);
}

.sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: var(--safe-bottom, 0);
}

.sheet {
  width: 100%;
  max-width: 480px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-bottom: none;
  border-radius: 22px 22px 0 0;
  display: flex;
  flex-direction: column;
  max-height: min(60vh, 420px);
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.10);
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--card-border);
  flex-shrink: 0;
}

.sheet-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
}

.sheet-close {
  border: none;
  background: none;
  color: var(--muted);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.option-list {
  margin: 0;
  padding: 8px 0 calc(8px + var(--safe-bottom, 0px));
  list-style: none;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.option-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: none;
  background: transparent;
  text-align: left;
  padding: 14px 16px;
  font-size: 15px;
  color: var(--text);
  line-height: 1.35;
  transition: background 0.12s, color 0.12s;
  -webkit-tap-highlight-color: transparent;
}

.option-item.active {
  color: var(--accent-a);
  font-weight: 700;
  background: rgba(22, 163, 74, 0.08);
}

.option-item:active {
  background: rgba(0, 0, 0, 0.05);
}

.check {
  flex-shrink: 0;
  color: var(--accent-a);
}

.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.22s ease;
}

.sheet-fade-enter-active .sheet,
.sheet-fade-leave-active .sheet {
  transition: transform 0.22s cubic-bezier(0.32, 0.72, 0, 1);
}

.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
}

.sheet-fade-enter-from .sheet,
.sheet-fade-leave-to .sheet {
  transform: translateY(100%);
}
</style>
