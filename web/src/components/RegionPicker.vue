<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { regionData } from "element-china-area-data";

interface AreaItem {
  value: string;
  label: string;
  children?: AreaItem[];
}

const provinces = regionData as unknown as AreaItem[];

const provinceCode = defineModel<string>("provinceCode", { default: "" });
const cityCode = defineModel<string>("cityCode", { default: "" });
const districtCode = defineModel<string>("districtCode", { default: "" });

const props = defineProps<{
  disabled?: boolean;
  placeholder?: string;
}>();

const showSheet = ref(false);
const draftProvince = ref("");
const draftCity = ref("");
const draftDistrict = ref("");

const cityOptions = computed(() => {
  const p = provinces.find((x) => x.value === draftProvince.value);
  return p?.children ?? [];
});

const districtOptions = computed(() => {
  const c = cityOptions.value.find((x) => x.value === draftCity.value);
  return c?.children ?? [];
});

const displayText = computed(() => {
  const p = provinces.find((x) => x.value === provinceCode.value);
  const c = p?.children?.find((x) => x.value === cityCode.value);
  const d = c?.children?.find((x) => x.value === districtCode.value);
  if (!p || !c || !d) return "";
  return `${p.label} ${c.label} ${d.label}`;
});

const isComplete = computed(
  () => !!(draftProvince.value && draftCity.value && draftDistrict.value),
);

watch(draftProvince, (code) => {
  if (!code) {
    draftCity.value = "";
    draftDistrict.value = "";
    return;
  }
  const cities = provinces.find((x) => x.value === code)?.children ?? [];
  if (!cities.some((x) => x.value === draftCity.value)) {
    draftCity.value = cities[0]?.value ?? "";
  }
});

watch(draftCity, (code) => {
  if (!code) {
    draftDistrict.value = "";
    return;
  }
  const districts =
    cityOptions.value.find((x) => x.value === code)?.children ?? [];
  if (!districts.some((x) => x.value === draftDistrict.value)) {
    draftDistrict.value = districts[0]?.value ?? "";
  }
});

function openSheet() {
  if (props.disabled) return;
  draftProvince.value = provinceCode.value;
  draftCity.value = cityCode.value;
  draftDistrict.value = districtCode.value;
  showSheet.value = true;
}

function closeSheet() {
  showSheet.value = false;
}

function confirm() {
  if (!isComplete.value) return;
  provinceCode.value = draftProvince.value;
  cityCode.value = draftCity.value;
  districtCode.value = draftDistrict.value;
  closeSheet();
}

function pickProvince(code: string) {
  draftProvince.value = code;
}

function pickCity(code: string) {
  draftCity.value = code;
}

function pickDistrict(code: string) {
  draftDistrict.value = code;
}
</script>

<template>
  <div class="region-picker">
    <button
      type="button"
      class="trigger"
      :class="{ filled: !!displayText, disabled: disabled }"
      :disabled="disabled"
      @click="openSheet"
    >
      <span class="trigger-text">{{ displayText || placeholder || "请选择省 · 市 · 区" }}</span>
      <svg class="chevron" viewBox="0 0 16 16" fill="none" width="16" height="16" aria-hidden="true">
        <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <Teleport to="body">
      <Transition name="sheet-fade">
        <div v-if="showSheet" class="sheet-overlay" @click.self="closeSheet">
          <div class="sheet" role="dialog" aria-modal="true" aria-label="选择所在地区">
            <div class="sheet-header">
              <button type="button" class="sheet-action muted" @click="closeSheet">取消</button>
              <span class="sheet-title">选择地区</span>
              <button
                type="button"
                class="sheet-action confirm"
                :disabled="!isComplete"
                @click="confirm"
              >
                确定
              </button>
            </div>

            <div class="columns">
              <ul class="col" role="listbox" aria-label="省">
                <li
                  v-for="p in provinces"
                  :key="p.value"
                  role="option"
                  :aria-selected="draftProvince === p.value"
                >
                  <button
                    type="button"
                    class="col-item"
                    :class="{ active: draftProvince === p.value }"
                    @click="pickProvince(p.value)"
                  >
                    {{ p.label }}
                  </button>
                </li>
              </ul>
              <ul class="col" role="listbox" aria-label="市">
                <li
                  v-for="c in cityOptions"
                  :key="c.value"
                  role="option"
                  :aria-selected="draftCity === c.value"
                >
                  <button
                    type="button"
                    class="col-item"
                    :class="{ active: draftCity === c.value }"
                    @click="pickCity(c.value)"
                  >
                    {{ c.label }}
                  </button>
                </li>
              </ul>
              <ul class="col" role="listbox" aria-label="区">
                <li
                  v-for="d in districtOptions"
                  :key="d.value"
                  role="option"
                  :aria-selected="draftDistrict === d.value"
                >
                  <button
                    type="button"
                    class="col-item"
                    :class="{ active: draftDistrict === d.value }"
                    @click="pickDistrict(d.value)"
                  >
                    {{ d.label }}
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.region-picker {
  width: 100%;
}

.trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 11px 14px;
  border-radius: 12px;
  border: 1px solid var(--card-border);
  background: rgba(0, 0, 0, 0.04);
  color: var(--muted);
  font-size: 15px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s;
  -webkit-tap-highlight-color: transparent;
}

.trigger.filled {
  color: var(--text);
}

.trigger:active:not(:disabled) {
  background: rgba(0, 0, 0, 0.07);
}

.trigger:disabled {
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

/* ── Bottom sheet ── */
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
  max-height: min(70vh, 520px);
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

.sheet-action {
  border: none;
  background: none;
  font-size: 15px;
  font-weight: 600;
  padding: 4px 2px;
  min-width: 44px;
}

.sheet-action.muted {
  color: var(--muted);
  text-align: left;
}

.sheet-action.confirm {
  color: var(--accent-a);
  text-align: right;
}

.sheet-action.confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.columns {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  flex: 1;
  min-height: 0;
  height: 280px;
}

.col {
  margin: 0;
  padding: 8px 0;
  list-style: none;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  border-right: 1px solid var(--card-border);
}

.col:last-child {
  border-right: none;
}

.col::-webkit-scrollbar {
  display: none;
}

.col-item {
  width: 100%;
  border: none;
  background: transparent;
  text-align: left;
  padding: 10px 12px;
  font-size: 14px;
  color: var(--text);
  line-height: 1.35;
  transition: background 0.12s, color 0.12s;
  -webkit-tap-highlight-color: transparent;
}

.col-item.active {
  color: var(--accent-a);
  font-weight: 700;
  background: rgba(22, 163, 74, 0.08);
}

.col-item:active {
  background: rgba(0, 0, 0, 0.05);
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
