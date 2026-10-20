<script setup lang="ts">
defineOptions({ name: "SocialRank" });

import { onActivated, onMounted, onUnmounted, ref, shallowRef, watch, nextTick } from "vue";
import * as echarts from "echarts";
import { apiFetch } from "../../api/client";
import MobileSelect from "../../components/MobileSelect.vue";

type Scope = "province" | "city" | "district" | "team";
type Period = "day" | "week" | "month" | "year";
type Metric = "rate" | "count" | "check_in";

const scopeOptions = [
  { value: "province", label: "省" },
  { value: "city", label: "市" },
  { value: "district", label: "区" },
  { value: "team", label: "小队（≥10 人）" },
] as const;

const periodOptions = [
  { value: "day", label: "日" },
  { value: "week", label: "周" },
  { value: "month", label: "月" },
  { value: "year", label: "年" },
] as const;

const metricOptions = [
  { value: "rate", label: "噜率" },
  { value: "count", label: "噜数目" },
  { value: "check_in", label: "打卡率" },
] as const;

function isPercentMetric(m: Metric): boolean {
  return m === "rate" || m === "check_in";
}

function metricSeriesName(m: Metric): string {
  if (m === "rate") return "噜率";
  if (m === "check_in") return "打卡率";
  return "次数";
}

function metricAxisName(m: Metric): string {
  if (m === "rate") return "噜率(%)";
  if (m === "check_in") return "打卡率(%)";
  return "噜次数";
}

function formatMetricValue(m: Metric, value: number): string {
  if (isPercentMetric(m)) return `${(value * 100).toFixed(2)}%`;
  return String(Math.round(value));
}

interface RankRow {
  rank: number;
  bucket_code: string;
  bucket_label: string;
  value: number;
}

interface RankingResponse {
  scope: Scope | string;
  period: Period | string;
  metric: Metric | string;
  anchor: string;
  range_start: string;
  range_end: string;
  rows: RankRow[];
  note?: string | null;
}

const scope = ref<Scope>("province");
const period = ref<Period>("week");
const metric = ref<Metric>("count");
const loading = ref(false);
const note = ref<string | null>(null);
const data = ref<RankingResponse | null>(null);

const chartEl = shallowRef<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

async function load(opts?: { silent?: boolean }) {
  const silent = opts?.silent === true && data.value != null;
  if (!silent) {
    loading.value = true;
    note.value = null;
  }
  try {
    const q = new URLSearchParams({
      scope: scope.value,
      period: period.value,
      metric: metric.value,
    });
    const res = await apiFetch<RankingResponse>(`/rankings?${q.toString()}`);
    data.value = res;
    note.value = res.note ?? null;
    await nextTick();
    await renderChart(res);
  } catch {
    if (!silent) {
      data.value = null;
      note.value = "加载失败，请稍后重试";
      if (chart) chart.clear();
    } else {
      note.value = "更新失败，请稍后重试";
    }
  } finally {
    loading.value = false;
  }
}

async function renderChart(res: RankingResponse) {
  if (!chartEl.value) return;
  if (!chart) chart = echarts.init(chartEl.value);

  const labels = res.rows.map((r) => r.bucket_label);
  const vals = res.rows.map((r) =>
    isPercentMetric(metric.value) ? Math.round(r.value * 10000) / 100 : r.value,
  );

  const yName = metricAxisName(metric.value);

  chart.setOption(
    {
      grid: { left: 52, right: 12, top: 28, bottom: 28 },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
      },
      xAxis: {
        type: "category",
        data: labels,
        axisLabel: {
          rotate: labels.length > 8 ? 40 : 0,
          interval: 0,
          fontSize: 10,
          color: "#475569",
        },
      },
      yAxis: {
        type: "value",
        name: yName,
        nameTextStyle: { color: "#475569", fontSize: 11 },
        splitLine: { lineStyle: { color: "rgba(71,85,105,0.14)" } },
        axisLabel: { color: "#475569", fontSize: 11 },
      },
      series: [
        {
          name: metricSeriesName(metric.value),
          type: "bar",
          data: vals,
          barMaxWidth: 28,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#38bdf8" },
              { offset: 1, color: "#22d3ee33" },
            ]),
          },
        },
      ],
    },
    true,
  );
}

watch([scope, period, metric], () => {
  load();
});

onMounted(() => {
  window.addEventListener("resize", resize);
  load();
});

let activatedOnce = false;

onActivated(() => {
  chart?.resize();
  if (!activatedOnce) {
    activatedOnce = true;
    return;
  }
  void load({ silent: data.value != null });
});

function resize() {
  chart?.resize();
}

onUnmounted(() => {
  window.removeEventListener("resize", resize);
  chart?.dispose();
  chart = null;
});
</script>

<template>
  <section class="card">
    <h2 class="title">榜单</h2>
    <p class="muted small">
      区间 {{ data?.range_start ?? "—" }} ~ {{ data?.range_end ?? "—" }}
    </p>

    <div class="filters">
      <MobileSelect
        v-model="scope"
        label="维度"
        sheet-title="选择维度"
        :options="[...scopeOptions]"
        :disabled="loading"
      />
      <MobileSelect
        v-model="period"
        label="周期"
        sheet-title="选择周期"
        :options="[...periodOptions]"
        :disabled="loading"
      />
      <MobileSelect
        v-model="metric"
        label="指标"
        sheet-title="选择指标"
        :options="[...metricOptions]"
        :disabled="loading"
      />
    </div>

    <p v-if="note" class="note">{{ note }}</p>
    <p v-if="loading" class="muted">载入中…</p>

    <div ref="chartEl" class="chart" />

    <ul v-if="data?.rows.length" class="list">
      <li v-for="r in data.rows.slice(0, 20)" :key="`${r.bucket_code}-${r.rank}`" class="row">
        <span class="rk">#{{ r.rank }}</span>
        <span class="lbl">{{ r.bucket_label }}</span>
        <span class="val">
          {{ formatMetricValue(metric, r.value) }}
        </span>
      </li>
    </ul>
    <p v-else-if="!loading && !note" class="muted">暂无数据</p>
  </section>
</template>

<style scoped>
.card {
  border-radius: var(--radius-lg);
  background: var(--card);
  border: 1px solid var(--card-border);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}
.muted {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}
.small {
  font-size: 11px;
}
.filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}
.note {
  margin: 0;
  font-size: 12px;
  color: #d97706;
  line-height: 1.5;
}
.chart {
  height: 280px;
  width: 100%;
}
.list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.row {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 6px 8px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.04);
}
.rk {
  color: var(--accent-b);
  font-weight: 800;
}
.lbl {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.val {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}
</style>
