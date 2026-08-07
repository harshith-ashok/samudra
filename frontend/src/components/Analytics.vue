<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import Chart from 'chart.js/auto';
import {
  getBiodiversityIndex,
  getCatchVsSst,
  getComplianceTrend,
  getVesselActivity,
} from '../api';
import type {
  BiodiversityIndexResponse,
  CatchVsSstResponse,
  ComplianceTrendResponse,
  VesselActivityResponse,
} from '../api/types';
import InfoTip from './InfoTip.vue';

const catchVsSst = ref<CatchVsSstResponse | null>(null);
const biodiversity = ref<BiodiversityIndexResponse | null>(null);
const compliance = ref<ComplianceTrendResponse | null>(null);
const vesselActivity = ref<VesselActivityResponse | null>(null);
const error = ref<string | null>(null);

const scatterCanvas = ref<HTMLCanvasElement | null>(null);
const biodiversityCanvas = ref<HTMLCanvasElement | null>(null);
const complianceCanvas = ref<HTMLCanvasElement | null>(null);
const vesselCanvas = ref<HTMLCanvasElement | null>(null);
const charts: Chart[] = [];

const grid = 'rgba(15,38,32,0.06)';
const seriesColors = ['#128F82', '#B9800F', '#D6512D'];

function renderScatter() {
  if (!catchVsSst.value || !scatterCanvas.value) return;
  charts.push(
    new Chart(scatterCanvas.value, {
      type: 'scatter',
      data: {
        datasets: catchVsSst.value.series.map((s, i) => ({
          label: `${s.species} (r=${s.correlation_r})`,
          data: s.points.map((p) => ({ x: p.sst_c, y: p.tonnage })),
          backgroundColor: seriesColors[i % seriesColors.length],
        })),
      },
      options: {
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 8, font: { size: 9 } },
          },
        },
        scales: {
          x: {
            title: { display: true, text: 'SST (°C)' },
            grid: { color: grid },
          },
          y: {
            title: { display: true, text: 'Tonnage' },
            grid: { color: grid },
          },
        },
      },
    })
  );
}

function renderBiodiversity() {
  if (!biodiversity.value || !biodiversityCanvas.value) return;
  charts.push(
    new Chart(biodiversityCanvas.value, {
      type: 'bar',
      data: {
        labels: biodiversity.value.regions.map((r) => r.region),
        datasets: [
          {
            data: biodiversity.value.regions.map((r) => r.species_count),
            backgroundColor: '#128F82',
          },
        ],
      },
      options: {
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: grid } },
          y: { grid: { display: false } },
        },
      },
    })
  );
}

function renderCompliance() {
  if (!compliance.value || !complianceCanvas.value) return;
  charts.push(
    new Chart(complianceCanvas.value, {
      type: 'line',
      data: {
        labels: compliance.value.trend.map((t) => t.month),
        datasets: [
          {
            data: compliance.value.trend.map((t) => t.pct_compliant),
            borderColor: '#128F82',
            backgroundColor: 'rgba(18,143,130,0.10)',
            fill: true,
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 2,
          },
        ],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: {
            title: { display: true, text: '% plants compliant' },
            grid: { color: grid },
          },
          x: { grid: { color: grid } },
        },
      },
    })
  );
}

function renderVesselActivity() {
  if (!vesselActivity.value || !vesselCanvas.value) return;
  charts.push(
    new Chart(vesselCanvas.value, {
      type: 'bar',
      data: {
        labels: vesselActivity.value.zones.map((z) => z.zone_name),
        datasets: [
          {
            label: '% of sampled positions in violation',
            data: vesselActivity.value.zones.map((z) =>
              Math.round((100 * z.violation_ticks) / z.total_ticks)
            ),
            backgroundColor: '#D6512D',
          },
        ],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { title: { display: true, text: '%' }, grid: { color: grid } },
          x: { grid: { color: grid } },
        },
      },
    })
  );
}

onMounted(async () => {
  try {
    [
      catchVsSst.value,
      biodiversity.value,
      compliance.value,
      vesselActivity.value,
    ] = await Promise.all([
      getCatchVsSst(),
      getBiodiversityIndex(),
      getComplianceTrend(),
      getVesselActivity(),
    ]);
    await nextTick();
    renderScatter();
    renderBiodiversity();
    renderCompliance();
    renderVesselActivity();
  } catch {
    error.value =
      "Couldn't reach the SAMUDRA backend for analytics. Is it running on :8000?";
  }
});

onBeforeUnmount(() => charts.forEach((c) => c.destroy()));
</script>

<template>
  <div>
    <p v-if="error" class="error">{{ error }}</p>
    <template v-else>
      <div class="a-block" v-if="catchVsSst">
        <h4>SST vs. Catch Tonnage<InfoTip glossary-key="stock_forecast" /></h4>
        <div class="sub">
          Monthly pairs per species/region, with Pearson's r
        </div>
        <canvas ref="scatterCanvas" height="160"></canvas>
        <p class="methodology">{{ catchVsSst.methodology }}</p>
      </div>

      <div class="a-block" v-if="biodiversity">
        <h4>
          Biodiversity Index by Region<InfoTip
            glossary-key="biodiversity_index"
          />
        </h4>
        <div class="sub">Distinct species observed (survey + eDNA)</div>
        <canvas
          ref="biodiversityCanvas"
          :height="40 + biodiversity.regions.length * 22"
        ></canvas>
        <p class="methodology">{{ biodiversity.methodology }}</p>
      </div>

      <div class="a-block" v-if="compliance">
        <h4>
          Treatment Plant Compliance Trend<InfoTip
            glossary-key="treatment_compliance"
          />
        </h4>
        <div class="sub">
          % of monitored plants compliant, current snapshot
          {{ compliance.current_snapshot_pct }}%
        </div>
        <canvas ref="complianceCanvas" height="140"></canvas>
        <p class="methodology">{{ compliance.methodology }}</p>
      </div>

      <div class="a-block" v-if="vesselActivity">
        <h4>Vessel Activity Near MPAs<InfoTip glossary-key="mpa" /></h4>
        <div class="sub">
          Share of {{ vesselActivity.samples_per_vessel_loop }} sampled loop
          positions per vessel found inside each zone
        </div>
        <canvas ref="vesselCanvas" height="140"></canvas>
        <p class="methodology">{{ vesselActivity.methodology }}</p>
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
.a-block {
  margin-bottom: 24px;
}
.a-block h4 {
  font-family: var(--font-display);
  font-size: 14px;
  margin-bottom: 2px;
  font-weight: 600;
  display: flex;
  align-items: center;
}
.a-block .sub {
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
</style>
