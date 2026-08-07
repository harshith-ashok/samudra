<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import Chart from 'chart.js/auto';
import type { StationDetail } from '../api/types';
import { useI18n } from '../composables/useI18n';

const props = defineProps<{ station: StationDetail | null }>();
const emit = defineEmits<{ (e: 'ask-ai', station: StationDetail): void }>();
const { t } = useI18n();

const canvasEl = ref<HTMLCanvasElement | null>(null);
let chartInst: Chart | null = null;

const typeColors: Record<string, string> = {
  buoy: '#128F82',
  edna: '#2E9E5B',
  advisory: '#D6512D',
  coral: '#B9800F',
};

function renderChart() {
  if (!props.station || !canvasEl.value) return;
  chartInst?.destroy();
  const history = props.station.history.slice(-14);
  const color = typeColors[props.station.type] ?? '#128F82';
  chartInst = new Chart(canvasEl.value, {
    type: 'line',
    data: {
      labels: history.map((h) => (h.day === 0 ? 'today' : `${h.day}d`)),
      datasets: [
        {
          data: history.map((h) => h.sst),
          borderColor: color,
          backgroundColor: `${color}1A`,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          borderWidth: 2,
        },
      ],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(15,38,32,0.06)' } },
        y: { grid: { color: 'rgba(15,38,32,0.06)' } },
      },
    },
  });
}

watch(
  () => props.station?.id,
  async () => {
    await nextTick();
    renderChart();
  },
  { immediate: true }
);

onBeforeUnmount(() => chartInst?.destroy());
</script>

<template>
  <div v-if="station">
    <span class="stat-badge">{{ station.type.toUpperCase() }}</span>
    <h3 class="stat-name">{{ station.name }}</h3>
    <div class="stat-readout">
      <b>{{ t('station.waterTemperature', { value: station.latest.sst_c }) }}</b>
      <span class="unit-note">{{ t('station.sstNote') }}</span><br />
      <b>{{ t('station.saltiness', { value: station.latest.salinity_psu }) }}</b>
      <span class="unit-note">{{ t('station.salinityNote') }}</span><br />
      <b>{{
        t('station.planktonLevel', { value: station.latest.chlorophyll_mg_m3 })
      }}</b>
      <span class="unit-note">{{ t('station.chlorophyllNote') }}</span>
    </div>
    <canvas ref="canvasEl" height="120"></canvas>
    <p class="source-note">{{ t('station.source', { source: station.source }) }}</p>
    <div class="chip" style="margin-top: 14px" @click="emit('ask-ai', station)">
      {{ t('station.askAi') }}
    </div>
  </div>
</template>

<style scoped>
.stat-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 9.5px;
  padding: 4px 9px;
  border-radius: 5px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--teal);
  margin-bottom: 12px;
  font-weight: 600;
}
.stat-name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 19px;
  margin-bottom: 8px;
}
.stat-readout {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 14px;
  margin: 12px 0;
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--muted);
  line-height: 1.9;
}
.stat-readout b {
  color: var(--text);
  font-family: var(--font-body);
  font-weight: 600;
}
.source-note {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  margin-top: 8px;
}
.unit-note {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  font-weight: 400;
}
.chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 11px;
  font-size: 11.5px;
  color: var(--muted);
  cursor: pointer;
  font-weight: 500;
}
.chip:hover {
  color: var(--teal);
  border-color: var(--teal);
}
</style>
