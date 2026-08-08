<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import Chart from 'chart.js/auto';
import { getSpecies, getSpeciesTrajectory } from '../api';
import type { Species, SpeciesTrajectory } from '../api/types';
import { speciesSlug } from '../utils/speciesId';
import InfoTip from './InfoTip.vue';
import ConfidenceMeter from './ConfidenceMeter.vue';
import { useI18n } from '../composables/useI18n';

const emit = defineEmits<{
  (e: 'trajectory', payload: SpeciesTrajectory | null): void;
  (e: 'ask-ai', payload: { species: Species; trajectory: SpeciesTrajectory | null }): void;
}>();

const { t } = useI18n();

const species = ref<Species[]>([]);
const hovered = ref<Species | null>(null);
const loading = ref(true);

const selected = ref<Species | null>(null);
const trajectory = ref<SpeciesTrajectory | null>(null);
const trajectoryError = ref<string | null>(null);
const trajectoryLoading = ref(false);

const trajectoryCanvas = ref<HTMLCanvasElement | null>(null);
let trajectoryChart: Chart | null = null;

const statusLabelKey: Record<string, string> = {
  LC: 'species.statusLC',
  NT: 'species.statusNT',
  VU: 'species.statusVU',
  EN: 'species.statusEN',
};
const statusClass: Record<string, string> = {
  LC: 'lc',
  NT: 'nt',
  VU: 'vu',
  EN: 'vu',
};

function renderTrajectoryChart() {
  if (!trajectory.value || !trajectoryCanvas.value) return;
  const t = trajectory.value;
  const years = [
    ...t.smoothed.map((p) => p.year),
    ...t.forecast.map((p) => p.year),
  ];
  const historicalLat = [
    ...t.smoothed.map((p) => p.lat),
    ...t.forecast.map(() => null),
  ];
  const forecastLat = [
    ...t.smoothed.map(() => null),
    ...t.forecast.map((p) => p.lat),
  ];
  // bridge the gap so the dashed forecast segment visually connects to the last solid point
  if (forecastLat.length > t.smoothed.length)
    forecastLat[t.smoothed.length - 1] = t.smoothed[t.smoothed.length - 1].lat;

  trajectoryChart?.destroy();
  trajectoryChart = new Chart(trajectoryCanvas.value, {
    type: 'line',
    data: {
      labels: years,
      datasets: [
        {
          label: 'Observed (smoothed)',
          data: historicalLat,
          borderColor: '#128F82',
          backgroundColor: '#128F82',
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 2.5,
          spanGaps: true,
        },
        {
          label: 'Forecast continuation',
          data: forecastLat,
          borderColor: '#B9800F',
          backgroundColor: '#B9800F',
          borderDash: [5, 5],
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
        x: { grid: { color: 'rgba(15,38,32,0.06)' } },
        y: {
          grid: { color: 'rgba(15,38,32,0.06)' },
          title: { display: true, text: 'centroid latitude' },
        },
      },
    },
  });
}

function askAiAboutSpecies() {
  if (!selected.value) return;
  emit('ask-ai', { species: selected.value, trajectory: trajectory.value });
}

async function selectSpecies(s: Species) {
  selected.value = s;
  trajectory.value = null;
  trajectoryError.value = null;
  trajectoryChart?.destroy();
  emit('trajectory', null);
  trajectoryLoading.value = true;
  try {
    trajectory.value = await getSpeciesTrajectory(speciesSlug(s.sci));
    trajectoryLoading.value = false;
    await nextTick(); // let the canvas mount now that trajectoryLoading is false
    renderTrajectoryChart();
    emit('trajectory', trajectory.value);
  } catch {
    trajectoryLoading.value = false;
    trajectoryError.value = t('species.notEnoughData', { name: s.common });
  }
}

onMounted(async () => {
  try {
    species.value = await getSpecies();
  } finally {
    loading.value = false;
  }
});

onBeforeUnmount(() => {
  trajectoryChart?.destroy();
  emit('trajectory', null);
});
</script>

<template>
  <div>
    <p v-if="loading" class="loading">{{ t('species.loadingTable') }}</p>
    <template v-else>
      <table>
        <thead>
          <tr>
            <th>{{ t('species.colSpecies') }}</th>
            <th>{{ t('species.colRegion') }}</th>
            <th>{{ t('species.colStatus') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in species"
            :key="s.sci"
            :class="{ selected: selected?.sci === s.sci }"
            @mouseenter="hovered = s"
            @mouseleave="hovered = null"
            @click="selectSpecies(s)"
          >
            <td>
              <i>{{ s.sci }}</i>
            </td>
            <td>{{ s.region }}</td>
            <td>
              <span
                v-if="s.status"
                class="tag"
                :class="statusClass[s.status]"
                >{{ t(statusLabelKey[s.status]) }}</span
              >
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="movement-block" v-if="selected">
        <div class="species-media">
          <img
            v-if="selected.media"
            :src="selected.media.image_url"
            :alt="selected.common"
            class="species-photo"
          />
          <div v-else class="species-photo-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6-10-6-10-6z" />
              <circle cx="15" cy="11" r="1" fill="currentColor" stroke="none" />
            </svg>
            <span>{{ t('species.noPhoto') }}</span>
          </div>
          <p v-if="selected.media" class="species-photo-caption">
            {{ selected.media.attribution }}
          </p>
        </div>
        <h4>
          {{ t('species.movementTrendTitle', { name: selected.common })
          }}<InfoTip glossary-key="species_trajectory" />
        </h4>
        <p v-if="trajectoryLoading" class="loading">
          {{ t('species.computingTrajectory') }}
        </p>
        <p v-else-if="trajectoryError" class="error">{{ trajectoryError }}</p>
        <template v-else-if="trajectory">
          <p class="conclusion">{{ trajectory.conclusion }}</p>
          <ConfidenceMeter
            :confidence="trajectory.confidence"
            :confidence-pct="trajectory.confidence_pct"
          />
          <div class="sub">
            {{ t('species.drifted') }}
            <b>{{ trajectory.drift_km }} km {{ trajectory.direction }}</b> ·
            {{ trajectory.historical.length }} {{ t('species.yearsOfRecords') }}
          </div>
          <canvas ref="trajectoryCanvas" height="140"></canvas>
          <p class="methodology">{{ trajectory.methodology }}</p>
        </template>
        <div
          v-if="!trajectoryLoading"
          class="chip"
          @click="askAiAboutSpecies"
        >
          {{ t('species.askAi') }}
        </div>
      </div>
    </template>

    <div class="species-hover-card" :class="{ show: hovered }">
      <template v-if="hovered">
        <div class="shc-head">
          <span class="shc-sci">{{ hovered.sci }}</span>
          <span
            v-if="hovered.status"
            class="tag"
            :class="statusClass[hovered.status]"
            >{{ t(statusLabelKey[hovered.status]) }}</span
          >
        </div>
        <div class="shc-common">{{ hovered.common }}</div>
        <div class="shc-region">{{ hovered.region }}</div>
        <p class="shc-note">{{ hovered.note }}</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.loading {
  color: var(--muted);
  font-size: 12.5px;
  font-family: var(--font-mono);
}
.error {
  color: var(--coral);
  font-size: 12px;
  line-height: 1.5;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11.5px;
}
th {
  text-align: left;
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  color: var(--muted);
  padding: 7px 6px;
  border-bottom: 1px solid var(--border);
}
td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border);
}
tbody tr {
  cursor: pointer;
}
tbody tr:hover {
  background: var(--surface-2);
}
tbody tr.selected {
  background: var(--teal-soft);
}
.tag {
  font-family: var(--font-mono);
  font-size: 9.5px;
  padding: 2px 7px;
  border-radius: 5px;
  border: 1px solid;
  font-weight: 600;
}
.tag.lc {
  color: #0b7a63;
  background: #e3f5f0;
  border-color: #bfe6dc;
}
.tag.nt {
  color: var(--amber);
  background: var(--amber-soft);
  border-color: #efdba6;
}
.tag.vu {
  color: var(--coral);
  background: var(--coral-soft);
  border-color: #f0c4b4;
}

.movement-block {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
.species-media {
  margin-bottom: 12px;
}
.species-photo {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--border);
  display: block;
}
.species-photo-placeholder {
  width: 100%;
  height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--surface-2);
  border: 1px dashed var(--border-strong);
  border-radius: 10px;
  color: var(--muted);
}
.species-photo-placeholder svg {
  width: 26px;
  height: 26px;
  opacity: 0.5;
}
.species-photo-placeholder span {
  font-family: var(--font-mono);
  font-size: 9.5px;
}
.species-photo-caption {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--muted);
  margin-top: 5px;
  line-height: 1.4;
}
.movement-block h4 {
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
.movement-block .sub {
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 10px;
}
.movement-block .confidence-meter {
  margin-bottom: 8px;
}
.methodology {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  margin-top: 8px;
  line-height: 1.5;
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
  margin-top: 12px;
}
.chip:hover {
  color: var(--teal);
  border-color: var(--teal);
}

.species-hover-card {
  position: fixed;
  left: 20px;
  bottom: 20px;
  width: 270px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 15px 17px;
  z-index: 40;
  opacity: 0;
  transform: translate(-18px, 18px) scale(0.97);
  transition:
    opacity 0.22s ease,
    transform 0.22s ease;
  pointer-events: none;
}
.species-hover-card.show {
  opacity: 1;
  transform: translate(0, 0) scale(1);
}
.species-hover-card .shc-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 5px;
}
.species-hover-card .shc-sci {
  font-family: var(--font-display);
  font-size: 14px;
  font-style: italic;
  line-height: 1.3;
}
.species-hover-card .shc-common {
  font-size: 11.5px;
  color: var(--teal);
  font-weight: 600;
  margin-bottom: 3px;
}
.species-hover-card .shc-region {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  margin-bottom: 9px;
}
.species-hover-card .shc-note {
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text);
}
</style>
