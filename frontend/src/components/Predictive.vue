<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import Chart from 'chart.js/auto';
import { getBleachingTrend, getRangeShift, getStockForecast } from '../api';
import type { BleachingTrend, RangeShift, StockForecast } from '../api/types';
import InfoTip from './InfoTip.vue';
import ConfidenceMeter from './ConfidenceMeter.vue';

// One entry per stock forecast shown — add another species/region pair here
// and it gets its own chart automatically, no other code changes needed.
const STOCK_CONFIGS = [
  {
    species: 'Sardinella longiceps',
    region: 'Kerala coast',
    label: 'Sardine Stock Forecast — Kerala',
  },
  {
    species: 'Rastrelliger kanagurta',
    region: 'Tamil Nadu coast',
    label: 'Mackerel Stock Forecast — Tamil Nadu',
  },
];

const stocks = ref<(StockForecast | null)[]>(STOCK_CONFIGS.map(() => null));
const bleaching = ref<BleachingTrend | null>(null);
const rangeA = ref<RangeShift | null>(null);
const rangeB = ref<RangeShift | null>(null);
const error = ref<string | null>(null);
const loading = ref(true);

// Phase 21 — what-if scenario simulator. Defaults are no-ops: dragging a slider
// re-fetches the same endpoints with overrides, it never touches the real
// forecast shown on initial load.
const sstDelta = ref(0);
const fishingPressure = ref(1);
const chlorophyllDelta = ref(0);
const scenarioUpdating = ref(false);
const scenarioActive = computed(
  () =>
    sstDelta.value !== 0 ||
    fishingPressure.value !== 1 ||
    chlorophyllDelta.value !== 0
);

function resetScenario() {
  sstDelta.value = 0;
  fishingPressure.value = 1;
  chlorophyllDelta.value = 0;
}

const stockCanvases: (HTMLCanvasElement | null)[] = [];
const stockCharts: (Chart | null)[] = [];
function setStockCanvas(el: Element | null, i: number) {
  stockCanvases[i] = el as HTMLCanvasElement | null;
}

const dhwCanvas = ref<HTMLCanvasElement | null>(null);
const factorCanvas = ref<HTMLCanvasElement | null>(null);
const rangeCanvas = ref<HTMLCanvasElement | null>(null);
let dhwChart: Chart | null = null;
let factorChart: Chart | null = null;
let rangeChartInst: Chart | null = null;

const grid = 'rgba(15,38,32,0.06)';
const factorColors: Record<string, string> = {
  dhw: '#D6512D',
  chlorophyll_trend: '#2E9E5B',
  historical_frequency: '#B9800F',
};

function renderStockChart(i: number) {
  const stock = stocks.value[i];
  const canvas = stockCanvases[i];
  if (!stock || !canvas) return;
  const historyN = stock.history.slice(-6);
  const labels = [
    ...historyN.map((h) => h.date.slice(0, 7)),
    ...stock.forecast.map((f) => `+${f.month_offset}`),
  ];
  const lowData = [
    ...historyN.map(() => null),
    ...stock.forecast.map((f) => f.low_80ci),
  ];
  const highData = [
    ...historyN.map(() => null),
    ...stock.forecast.map((f) => f.high_80ci),
  ];
  const meanData = [
    ...historyN.map((h) => h.tonnage),
    ...stock.forecast.map((f) => f.tonnage),
  ];

  stockCharts[i]?.destroy();
  stockCharts[i] = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Low 80% CI',
          data: lowData,
          borderColor: 'transparent',
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'High 80% CI',
          data: highData,
          borderColor: 'transparent',
          backgroundColor: 'rgba(18,143,130,0.12)',
          pointRadius: 0,
          fill: '-1',
        },
        {
          label: 'Tonnage',
          data: meanData,
          borderColor: '#128F82',
          tension: 0.4,
          borderWidth: 2.5,
          pointRadius: 2,
        },
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
    type: 'line',
    data: {
      labels: weeks.map((w) => `wk ${w.week}`),
      datasets: [
        {
          label: 'Cumulative DHW',
          data: weeks.map((w) => w.cumulative_dhw),
          borderColor: '#D6512D',
          backgroundColor: 'rgba(214,81,45,0.12)',
          tension: 0.3,
          borderWidth: 2.5,
          pointRadius: 2,
          fill: true,
        },
        {
          label: 'Alert Level 1 (4)',
          data: weeks.map(() => 4),
          borderColor: '#B9800F',
          borderDash: [5, 5],
          borderWidth: 1.3,
          pointRadius: 0,
        },
        {
          label: 'Alert Level 2 (8)',
          data: weeks.map(() => 8),
          borderColor: '#D6512D',
          borderDash: [5, 5],
          borderWidth: 1.3,
          pointRadius: 0,
        },
      ],
    },
    options: {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 8, font: { size: 9 } },
        },
      },
      scales: {
        x: { grid: { color: grid } },
        y: { grid: { color: grid }, title: { display: true, text: 'DHW' } },
      },
    },
  });
}

function renderFactorChart() {
  if (!bleaching.value || !factorCanvas.value) return;
  const factors = bleaching.value.factors;
  factorChart?.destroy();
  factorChart = new Chart(factorCanvas.value, {
    type: 'bar',
    data: {
      labels: factors.map((f) => `${f.label} (${Math.round(f.weight * 100)}%)`),
      datasets: [
        {
          label: 'Contribution to composite score',
          data: factors.map((f) => f.contribution_pct),
          backgroundColor: factors.map(
            (f) => factorColors[f.factor] ?? '#128F82'
          ),
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: grid },
          title: { display: true, text: 'points of 100' },
        },
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
    ])
  ).sort();

  function seriesFor(rs: RangeShift) {
    const observedByYear = new Map(
      rs.observed.map((p) => [p.year, p.mean_lat])
    );
    const projectedByYear = new Map(
      rs.projection.map((p) => [p.year, p.projected_mean_lat])
    );
    return years.map(
      (y) => observedByYear.get(y) ?? projectedByYear.get(y) ?? null
    );
  }

  rangeChartInst?.destroy();
  rangeChartInst = new Chart(rangeCanvas.value, {
    type: 'line',
    data: {
      labels: years,
      datasets: [
        {
          label: rangeA.value.species,
          data: seriesFor(rangeA.value),
          borderColor: '#128F82',
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2,
          spanGaps: true,
        },
        {
          label: rangeB.value.species,
          data: seriesFor(rangeB.value),
          borderColor: '#B9800F',
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2,
          spanGaps: true,
        },
      ],
    },
    options: {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 8, font: { size: 9 } },
        },
      },
      scales: {
        x: { grid: { color: grid } },
        y: {
          grid: { color: grid },
          title: { display: true, text: 'mean occurrence latitude' },
        },
      },
    },
  });
}

async function loadAll(isInitial: boolean) {
  try {
    const [newStocks, newBleaching, newRangeA, newRangeB] = await Promise.all(
      [
        Promise.all(
          STOCK_CONFIGS.map((c) =>
            getStockForecast(
              c.species,
              c.region,
              sstDelta.value,
              fishingPressure.value
            )
          )
        ),
        getBleachingTrend(
          'lakshadweep',
          sstDelta.value,
          chlorophyllDelta.value
        ),
        getRangeShift('Thunnus albacares', sstDelta.value),
        getRangeShift('Rastrelliger kanagurta', sstDelta.value),
      ]
    );
    stocks.value = newStocks;
    bleaching.value = newBleaching;
    rangeA.value = newRangeA;
    rangeB.value = newRangeB;
    if (isInitial) loading.value = false;
    await nextTick(); // let the pred-block canvases mount now that loading is false
    stocks.value.forEach((_, i) => renderStockChart(i));
    renderDhwChart();
    renderFactorChart();
    renderRangeChart();
  } catch (e) {
    if (isInitial) {
      loading.value = false;
      error.value =
        "Couldn't reach the SAMUDRA backend for predictions. Is it running on :8000?";
    }
  }
}

let scenarioDebounce: number | undefined;
watch([sstDelta, fishingPressure, chlorophyllDelta], () => {
  if (loading.value) return; // still on initial load, nothing to re-run yet
  scenarioUpdating.value = true;
  window.clearTimeout(scenarioDebounce);
  scenarioDebounce = window.setTimeout(async () => {
    await loadAll(false);
    scenarioUpdating.value = false;
  }, 400);
});

onMounted(() => loadAll(true));

onBeforeUnmount(() => {
  window.clearTimeout(scenarioDebounce);
  stockCharts.forEach((c) => c?.destroy());
  dhwChart?.destroy();
  factorChart?.destroy();
  rangeChartInst?.destroy();
});
</script>

<template>
  <div>
    <p v-if="loading" class="loading">
      Running forecasts — stock trend, bleaching buildup, range shift (each ends
      in a gpt-oss conclusion, ~5s)…
    </p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <template v-else>
      <div class="whatif-block">
        <div class="whatif-head">
          <h4>What-If Scenario Simulator<InfoTip glossary-key="whatif_scenario" /></h4>
          <button
            v-if="scenarioActive"
            class="reset-btn"
            type="button"
            @click="resetScenario"
          >
            Reset
          </button>
        </div>
        <p class="whatif-hint">
          Drag a slider to re-run the real models below with a hypothetical
          input — every chart updates live, it never replaces the actual
          forecast shown at 0/×1.
        </p>
        <div class="slider-row">
          <label
            >SST anomaly
            <b>{{ sstDelta > 0 ? '+' : '' }}{{ sstDelta.toFixed(1) }}°C</b></label
          >
          <input
            type="range"
            min="-2"
            max="3"
            step="0.1"
            v-model.number="sstDelta"
          />
        </div>
        <div class="slider-row">
          <label
            >Fishing pressure
            <b>×{{ fishingPressure.toFixed(1) }}</b></label
          >
          <input
            type="range"
            min="0.5"
            max="2"
            step="0.1"
            v-model.number="fishingPressure"
          />
        </div>
        <div class="slider-row">
          <label
            >Chlorophyll-a delta
            <b
              >{{ chlorophyllDelta > 0 ? '+' : ''
              }}{{ chlorophyllDelta.toFixed(2) }} mg/m³</b
            ></label
          >
          <input
            type="range"
            min="-0.4"
            max="0.4"
            step="0.05"
            v-model.number="chlorophyllDelta"
          />
        </div>
      </div>

      <template v-for="(stock, i) in stocks" :key="STOCK_CONFIGS[i].species">
        <div class="pred-block" v-if="stock">
          <h4>
            {{ STOCK_CONFIGS[i].label
            }}<InfoTip glossary-key="stock_forecast" />
          </h4>
          <div v-if="stock.scenario.active" class="scenario-pill">
            Simulated scenario — not a live forecast{{
              scenarioUpdating ? ' · updating…' : ''
            }}
          </div>
          <p class="conclusion">{{ stock.conclusion }}</p>
          <ConfidenceMeter :confidence="stock.confidence" />
          <div class="sub">
            {{ stock.forecast.length }}-month projection, 80% CI · trend
            {{ stock.trend_tonnage_per_month }} t/month
          </div>
          <canvas
            :ref="(el) => setStockCanvas(el as Element | null, i)"
            height="140"
          ></canvas>
          <p class="methodology">{{ stock.methodology }}</p>
        </div>
      </template>

      <div class="pred-block" v-if="bleaching">
        <h4>
          Coral Bleaching Buildup — {{ bleaching.station_name
          }}<InfoTip glossary-key="composite_bleaching_score" />
        </h4>
        <div v-if="bleaching.scenario.active" class="scenario-pill">
          Simulated scenario — not a live forecast{{
            scenarioUpdating ? ' · updating…' : ''
          }}
        </div>
        <p class="conclusion">{{ bleaching.conclusion }}</p>
        <ConfidenceMeter :confidence="bleaching.confidence" />
        <div class="sub">
          Composite score
          <b class="coral-text">{{ bleaching.composite_score }}/100</b> ·
          {{ bleaching.alert_level }}
        </div>
        <div class="countdown" :class="bleaching.threshold_countdown.status">
          <template v-if="bleaching.threshold_countdown.status === 'projected'">
            <span class="countdown-num">{{
              Math.round(bleaching.threshold_countdown.days!)
            }}</span>
            <span class="countdown-unit">day{{
              Math.round(bleaching.threshold_countdown.days!) === 1 ? '' : 's'
            }}</span>
            <span class="countdown-caption"
              >until {{ bleaching.threshold_countdown.next_alert_label }} at
              the current heat-stress trend</span
            >
          </template>
          <template v-else>
            <span class="countdown-caption">{{
              bleaching.threshold_countdown.message
            }}</span>
          </template>
        </div>
        <canvas ref="dhwCanvas" height="130"></canvas>
        <div class="sub factor-heading">
          What's driving the score<InfoTip glossary-key="dhw" />
        </div>
        <canvas ref="factorCanvas" height="100"></canvas>
        <p class="methodology">{{ bleaching.methodology }}</p>
      </div>

      <div class="pred-block" v-if="rangeA && rangeB">
        <h4>Range Shift Projection<InfoTip glossary-key="range_shift" /></h4>
        <div v-if="rangeA.scenario.active" class="scenario-pill">
          Simulated scenario — not a live forecast{{
            scenarioUpdating ? ' · updating…' : ''
          }}
        </div>
        <p class="conclusion">{{ rangeA.conclusion }}</p>
        <ConfidenceMeter :confidence="rangeA.confidence" />
        <div class="sub">
          Observed + 5yr projection, mean occurrence latitude
        </div>
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
.whatif-block {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 22px;
}
.whatif-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.whatif-head h4 {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
}
.reset-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
}
.reset-btn:hover {
  color: var(--coral);
  border-color: var(--coral);
}
.whatif-hint {
  font-size: 11px;
  line-height: 1.5;
  color: var(--muted);
  margin: 6px 0 12px;
}
.slider-row {
  margin-bottom: 10px;
}
.slider-row:last-child {
  margin-bottom: 0;
}
.slider-row label {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 4px;
}
.slider-row label b {
  color: var(--text);
  font-family: var(--font-mono);
  font-weight: 600;
}
.slider-row input[type='range'] {
  width: 100%;
  accent-color: var(--amber);
}
.scenario-pill {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 600;
  color: var(--amber);
  background: var(--amber-soft);
  border: 1px solid #efdba6;
  border-radius: 5px;
  padding: 3px 8px;
  margin-bottom: 8px;
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
.pred-block .confidence-meter {
  margin-bottom: 8px;
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
.countdown {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  background: var(--coral-soft);
  border: 1px solid #f0c4b4;
  border-radius: 9px;
  padding: 10px 13px;
  margin-bottom: 12px;
}
.countdown.at_max,
.countdown.not_trending,
.countdown.unreachable {
  background: var(--surface-2);
  border-color: var(--border);
}
.countdown-num {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  color: var(--coral);
  line-height: 1;
}
.countdown-unit {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--coral);
  font-weight: 600;
}
.countdown-caption {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.4;
}
</style>
