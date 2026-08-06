<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import Chart from "chart.js/auto";
import { getBleachingTrend, getRangeShift, getStockForecast } from "../api";
import type { BleachingTrend, RangeShift, StockForecast } from "../api/types";
import InfoTip from "./InfoTip.vue";

const stock = ref<StockForecast | null>(null);
const bleaching = ref<BleachingTrend | null>(null);
const rangeA = ref<RangeShift | null>(null);
const rangeB = ref<RangeShift | null>(null);
const error = ref<string | null>(null);
const loading = ref(true);

const forecastCanvas = ref<HTMLCanvasElement | null>(null);
const dhwCanvas = ref<HTMLCanvasElement | null>(null);
const factorCanvas = ref<HTMLCanvasElement | null>(null);
const rangeCanvas = ref<HTMLCanvasElement | null>(null);
let forecastChart: Chart | null = null;
let dhwChart: Chart | null = null;
let factorChart: Chart | null = null;
let rangeChartInst: Chart | null = null;

const grid = "rgba(15,38,32,0.06)";
const factorColors: Record<string, string> = {
  dhw: "#D6512D",
  chlorophyll_trend: "#2E9E5B",
  historical_frequency: "#B9800F",
};

function renderForecastChart() {
  if (!stock.value || !forecastCanvas.value) return;
  const historyN = stock.value.history.slice(-6);
  const labels = [...historyN.map((h) => h.date.slice(0, 7)), ...stock.value.forecast.map((f) => `+${f.month_offset}`)];
  const lowData = [...historyN.map(() => null), ...stock.value.forecast.map((f) => f.low_80ci)];
  const highData = [...historyN.map(() => null), ...stock.value.forecast.map((f) => f.high_80ci)];
  const meanData = [...historyN.map((h) => h.tonnage), ...stock.value.forecast.map((f) => f.tonnage)];

  forecastChart?.destroy();
  forecastChart = new Chart(forecastCanvas.value, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Low 80% CI", data: lowData, borderColor: "transparent", pointRadius: 0, fill: false },
        {
          label: "High 80% CI",
          data: highData,
          borderColor: "transparent",
          backgroundColor: "rgba(18,143,130,0.12)",
          pointRadius: 0,
          fill: "-1",
        },
        { label: "Tonnage", data: meanData, borderColor: "#128F82", tension: 0.4, borderWidth: 2.5, pointRadius: 2 },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { x: { grid: { color: grid } }, y: { grid: { color: grid } } },
    },
  });
}

function renderDhwChart() {
  if (!bleaching.value || !dhwCanvas.value) return;
  const weeks = bleaching.value.weekly_series;
  dhwChart?.destroy();
  dhwChart = new Chart(dhwCanvas.value, {
    type: "line",
    data: {
      labels: weeks.map((w) => `wk ${w.week}`),
      datasets: [
        {
          label: "Cumulative DHW",
          data: weeks.map((w) => w.cumulative_dhw),
          borderColor: "#D6512D",
          backgroundColor: "rgba(214,81,45,0.12)",
          tension: 0.3,
          borderWidth: 2.5,
          pointRadius: 2,
          fill: true,
        },
        {
          label: "Alert Level 1 (4)",
          data: weeks.map(() => 4),
          borderColor: "#B9800F",
          borderDash: [5, 5],
          borderWidth: 1.3,
          pointRadius: 0,
        },
        {
          label: "Alert Level 2 (8)",
          data: weeks.map(() => 8),
          borderColor: "#D6512D",
          borderDash: [5, 5],
          borderWidth: 1.3,
          pointRadius: 0,
        },
      ],
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { boxWidth: 8, font: { size: 9 } } } },
      scales: { x: { grid: { color: grid } }, y: { grid: { color: grid }, title: { display: true, text: "DHW" } } },
    },
  });
}

function renderFactorChart() {
  if (!bleaching.value || !factorCanvas.value) return;
  const factors = bleaching.value.factors;
  factorChart?.destroy();
  factorChart = new Chart(factorCanvas.value, {
    type: "bar",
    data: {
      labels: factors.map((f) => `${f.label} (${Math.round(f.weight * 100)}%)`),
      datasets: [
        {
          label: "Contribution to composite score",
          data: factors.map((f) => f.contribution_pct),
          backgroundColor: factors.map((f) => factorColors[f.factor] ?? "#128F82"),
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: grid }, title: { display: true, text: "points of 100" } },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } },
      },
    },
  });
}

function renderRangeChart() {
  if (!rangeA.value || !rangeB.value || !rangeCanvas.value) return;
  const years = Array.from(
    new Set([
      ...rangeA.value.observed.map((p) => p.year),
      ...rangeA.value.projection.map((p) => p.year),
    ]),
  ).sort();

  function seriesFor(rs: RangeShift) {
    const observedByYear = new Map(rs.observed.map((p) => [p.year, p.mean_lat]));
    const projectedByYear = new Map(rs.projection.map((p) => [p.year, p.projected_mean_lat]));
    return years.map((y) => observedByYear.get(y) ?? projectedByYear.get(y) ?? null);
  }

  rangeChartInst?.destroy();
  rangeChartInst = new Chart(rangeCanvas.value, {
    type: "line",
    data: {
      labels: years,
      datasets: [
        { label: rangeA.value.species, data: seriesFor(rangeA.value), borderColor: "#128F82", tension: 0.3, pointRadius: 2, borderWidth: 2, spanGaps: true },
        { label: rangeB.value.species, data: seriesFor(rangeB.value), borderColor: "#B9800F", tension: 0.3, pointRadius: 2, borderWidth: 2, spanGaps: true },
      ],
    },
    options: {
      plugins: { legend: { position: "bottom", labels: { boxWidth: 8, font: { size: 9 } } } },
      scales: {
        x: { grid: { color: grid } },
        y: { grid: { color: grid }, title: { display: true, text: "mean occurrence latitude" } },
      },
    },
  });
}

onMounted(async () => {
  try {
    [stock.value, bleaching.value, rangeA.value, rangeB.value] = await Promise.all([
      getStockForecast("Sardinella longiceps", "Kerala coast"),
      getBleachingTrend("lakshadweep"),
      getRangeShift("Thunnus albacares"),
      getRangeShift("Rastrelliger kanagurta"),
    ]);
    loading.value = false;
    await nextTick(); // let the pred-block canvases mount now that loading is false
    renderForecastChart();
    renderDhwChart();
    renderFactorChart();
    renderRangeChart();
  } catch (e) {
    loading.value = false;
    error.value = "Couldn't reach the SAMUDRA backend for predictions. Is it running on :8000?";
  }
});

onBeforeUnmount(() => {
  forecastChart?.destroy();
  dhwChart?.destroy();
  factorChart?.destroy();
  rangeChartInst?.destroy();
});
</script>

<template>
  <div>
    <p v-if="loading" class="loading">Running forecasts — stock trend, bleaching buildup, range shift (each ends in a gpt-oss conclusion, ~5s)…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <template v-else>
      <div class="pred-block" v-if="stock">
        <h4>Sardine Stock Forecast — Kerala<InfoTip glossary-key="stock_forecast" /></h4>
        <p class="conclusion">{{ stock.conclusion }}</p>
        <div class="sub">{{ stock.forecast.length }}-month projection, 80% CI · trend {{ stock.trend_tonnage_per_month }} t/month</div>
        <canvas ref="forecastCanvas" height="140"></canvas>
        <p class="methodology">{{ stock.methodology }}</p>
      </div>

      <div class="pred-block" v-if="bleaching">
        <h4>Coral Bleaching Buildup — {{ bleaching.station_name }}<InfoTip glossary-key="composite_bleaching_score" /></h4>
        <p class="conclusion">{{ bleaching.conclusion }}</p>
        <div class="sub">
          Composite score <b class="coral-text">{{ bleaching.composite_score }}/100</b> · {{ bleaching.alert_level }}
        </div>
        <canvas ref="dhwCanvas" height="130"></canvas>
        <div class="sub factor-heading">What's driving the score<InfoTip glossary-key="dhw" /></div>
        <canvas ref="factorCanvas" height="100"></canvas>
        <p class="methodology">{{ bleaching.methodology }}</p>
      </div>

      <div class="pred-block" v-if="rangeA && rangeB">
        <h4>Range Shift Projection<InfoTip glossary-key="range_shift" /></h4>
        <p class="conclusion">{{ rangeA.conclusion }}</p>
        <div class="sub">Observed + 5yr projection, mean occurrence latitude</div>
        <canvas ref="rangeCanvas" height="140"></canvas>
        <p class="methodology">{{ rangeA.methodology }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.error,
.loading {
  color: var(--coral);
  font-size: 12.5px;
  font-family: var(--font-mono);
}
.loading {
  color: var(--muted);
}
.pred-block {
  margin-bottom: 22px;
}
.pred-block h4 {
  font-family: var(--font-display);
  font-size: 14px;
  margin-bottom: 6px;
  font-weight: 600;
}
.conclusion {
  font-size: 12.5px;
  line-height: 1.5;
  background: var(--teal-soft);
  color: var(--teal);
  border-radius: 8px;
  padding: 9px 11px;
  margin-bottom: 8px;
}
.pred-block .sub {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 10px;
}
.factor-heading {
  margin-top: 12px;
  display: flex;
  align-items: center;
}
.methodology {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  margin-top: 8px;
  line-height: 1.5;
}
.coral-text {
  color: var(--coral);
}
</style>
