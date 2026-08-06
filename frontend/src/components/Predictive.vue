<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import Chart from "chart.js/auto";
import { getBleachingRisk, getRangeShift, getStockForecast } from "../api";
import type { BleachingRisk, RangeShift, StockForecast } from "../api/types";

const stock = ref<StockForecast | null>(null);
const bleaching = ref<BleachingRisk | null>(null);
const rangeA = ref<RangeShift | null>(null);
const rangeB = ref<RangeShift | null>(null);
const error = ref<string | null>(null);

const forecastCanvas = ref<HTMLCanvasElement | null>(null);
const gaugeCanvas = ref<HTMLCanvasElement | null>(null);
const rangeCanvas = ref<HTMLCanvasElement | null>(null);
let forecastChart: Chart | null = null;
let gaugeChart: Chart | null = null;
let rangeChartInst: Chart | null = null;

const grid = "rgba(15,38,32,0.06)";

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

function renderGaugeChart() {
  if (!bleaching.value || !gaugeCanvas.value) return;
  gaugeChart?.destroy();
  gaugeChart = new Chart(gaugeCanvas.value, {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [bleaching.value.risk_pct, 100 - bleaching.value.risk_pct],
          backgroundColor: ["#D6512D", "#EEF4F4"],
          borderWidth: 0,
        },
      ],
    },
    options: { cutout: "75%", plugins: { legend: { display: false }, tooltip: { enabled: false } } },
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
      getBleachingRisk("lakshadweep"),
      getRangeShift("Thunnus albacares"),
      getRangeShift("Rastrelliger kanagurta"),
    ]);
    await nextTick();
    renderForecastChart();
    renderGaugeChart();
    renderRangeChart();
  } catch (e) {
    error.value = "Couldn't reach the SAMUDRA backend for predictions. Is it running on :8000?";
  }
});

onBeforeUnmount(() => {
  forecastChart?.destroy();
  gaugeChart?.destroy();
  rangeChartInst?.destroy();
});
</script>

<template>
  <div>
    <p v-if="error" class="error">{{ error }}</p>
    <template v-else>
      <div class="pred-block" v-if="stock">
        <h4>Sardine Stock Forecast — Kerala</h4>
        <div class="sub">{{ stock.forecast.length }}-month projection, 80% CI · trend {{ stock.trend_tonnage_per_month }} t/month</div>
        <canvas ref="forecastCanvas" height="140"></canvas>
        <p class="methodology">{{ stock.methodology }}</p>
      </div>

      <div class="pred-block" v-if="bleaching">
        <h4>Coral Bleaching Risk</h4>
        <div class="sub">{{ bleaching.station_name }}, current reading</div>
        <div class="gauge-wrap">
          <div class="gauge">
            <canvas ref="gaugeCanvas"></canvas>
            <div class="num">{{ bleaching.risk_pct }}%</div>
          </div>
          <div class="gauge-caption">
            DHW: <b class="coral-text">{{ bleaching.dhw }}</b><br />{{ bleaching.alert_level }}
          </div>
        </div>
        <p class="methodology">{{ bleaching.methodology }}</p>
      </div>

      <div class="pred-block" v-if="rangeA && rangeB">
        <h4>Range Shift Projection</h4>
        <div class="sub">Observed + 5yr projection, mean occurrence latitude</div>
        <canvas ref="rangeCanvas" height="140"></canvas>
        <p class="methodology">{{ rangeA.methodology }}</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.error {
  color: var(--coral);
  font-size: 12.5px;
  font-family: var(--font-mono);
}
.pred-block {
  margin-bottom: 22px;
}
.pred-block h4 {
  font-family: var(--font-display);
  font-size: 14px;
  margin-bottom: 2px;
  font-weight: 600;
}
.pred-block .sub {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 10px;
}
.methodology {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  margin-top: 8px;
  line-height: 1.5;
}
.gauge-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.gauge {
  position: relative;
  width: 92px;
  height: 92px;
  flex-shrink: 0;
}
.gauge .num {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
}
.gauge-caption {
  font-size: 11.5px;
  color: var(--muted);
  line-height: 1.6;
}
.coral-text {
  color: var(--coral);
}
</style>
