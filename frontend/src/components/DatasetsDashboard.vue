<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import Chart from 'chart.js/auto';
import { getDatasetCorrelation, getDatasetRecords, getDatasets } from '../api';
import type {
  DatasetCorrelation,
  DatasetRecord,
  DatasetSummary,
} from '../api/types';
import { useI18n } from '../composables/useI18n';

const { t } = useI18n();

const datasets = ref<DatasetSummary[]>([]);
const selectedId = ref<string | null>(null);
const selected = computed(() =>
  datasets.value.find((d) => d.id === selectedId.value) ?? null
);
const fieldOrder = computed(() =>
  selected.value ? Object.keys(selected.value.fields) : []
);

const searchQuery = ref('');
const sortField = ref('');
const sortOrder = ref<'asc' | 'desc'>('asc');
const rows = ref<DatasetRecord[]>([]);
const rowsLoading = ref(false);
const loadError = ref(false);

const xField = ref('');
const yField = ref('');
const correlation = ref<DatasetCorrelation | null>(null);
const correlationCanvas = ref<HTMLCanvasElement | null>(null);
let correlationChart: Chart | null = null;

async function loadDatasets() {
  try {
    datasets.value = await getDatasets();
    selectedId.value ??= datasets.value[0]?.id ?? null;
  } catch {
    loadError.value = true;
  }
}

async function loadRecords() {
  if (!selected.value) return;
  rowsLoading.value = true;
  loadError.value = false;
  try {
    const res = await getDatasetRecords(
      selected.value.id,
      searchQuery.value,
      sortField.value || undefined,
      sortOrder.value
    );
    rows.value = res.rows;
    sortField.value = res.sort;
  } catch {
    rows.value = [];
    loadError.value = true;
  } finally {
    rowsLoading.value = false;
  }
}

function toggleSort(field: string) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortField.value = field;
    sortOrder.value = 'asc';
  }
}

function renderCorrelationChart() {
  correlationChart?.destroy();
  correlationChart = null;
  if (!correlation.value || !correlationCanvas.value) return;
  correlationChart = new Chart(correlationCanvas.value, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: `${correlation.value.x} vs ${correlation.value.y}`,
          data: correlation.value.points.map((p) => ({ x: p.x, y: p.y })),
          backgroundColor: '#128F82',
          pointRadius: 2.5,
          pointHoverRadius: 4,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          title: { display: true, text: t(`datasets.fields.${correlation.value.x}`), font: { size: 10 } },
          ticks: { font: { size: 9 } },
        },
        y: {
          title: { display: true, text: t(`datasets.fields.${correlation.value.y}`), font: { size: 10 } },
          ticks: { font: { size: 9 } },
        },
      },
    },
  });
}

async function loadCorrelation() {
  if (!selected.value || !xField.value || !yField.value) {
    correlation.value = null;
    renderCorrelationChart();
    return;
  }
  try {
    correlation.value = await getDatasetCorrelation(
      selected.value.id,
      xField.value,
      yField.value
    );
  } catch {
    correlation.value = null;
  }
  await nextTick();
  renderCorrelationChart();
}

// Switching datasets resets every dataset-scoped control rather than
// carrying over a field/sort selection that may not exist on the new one.
watch(selected, (d) => {
  searchQuery.value = '';
  sortField.value = d?.default_sort ?? '';
  sortOrder.value = 'asc';
  const numeric = d?.numeric_fields ?? [];
  xField.value = numeric[0] ?? '';
  yField.value = numeric[1] ?? '';
  loadRecords();
  loadCorrelation();
});

let searchDebounce: number | undefined;
watch(searchQuery, () => {
  window.clearTimeout(searchDebounce);
  searchDebounce = window.setTimeout(loadRecords, 300);
});

watch([sortField, sortOrder], loadRecords);
watch([xField, yField], loadCorrelation);

loadDatasets().then(loadRecords).then(loadCorrelation);

onBeforeUnmount(() => correlationChart?.destroy());
</script>

<template>
  <div class="dash">
    <aside class="catalog">
      <button
        v-for="d in datasets"
        :key="d.id"
        type="button"
        class="catalog-item"
        :class="{ active: d.id === selectedId }"
        @click="selectedId = d.id"
      >
        <div class="catalog-name">{{ t(`datasets.catalog.${d.id}.name`) }}</div>
        <div class="catalog-desc">{{ t(`datasets.catalog.${d.id}.description`) }}</div>
        <div class="catalog-count">{{ t('datasets.recordCount', { count: d.record_count }) }}</div>
      </button>
    </aside>

    <main class="content" v-if="selected">
      <div class="toolbar">
        <input
          v-model="searchQuery"
          class="search-input"
          :placeholder="t('datasets.searchPlaceholder')"
        />
        <span class="source">{{ t('datasets.source') }}: {{ selected.source }}</span>
      </div>

      <p v-if="loadError" class="error">{{ t('datasets.error') }}</p>
      <p v-else-if="rowsLoading" class="loading">{{ t('datasets.loading') }}</p>
      <template v-else>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th
                  v-for="f in fieldOrder"
                  :key="f"
                  @click="toggleSort(f)"
                  :class="{ sorted: sortField === f }"
                >
                  {{ t(`datasets.fields.${f}`) }}
                  <span v-if="sortField === f" class="sort-arrow">{{
                    sortOrder === 'asc' ? '▲' : '▼'
                  }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in rows" :key="i">
                <td v-for="f in fieldOrder" :key="f">{{ row[f] ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!rows.length" class="no-results">{{ t('datasets.noResults') }}</p>
        </div>

        <div class="correlation" v-if="selected.correlatable">
          <h4>{{ t('datasets.correlationTitle') }}</h4>
          <div class="correlation-controls">
            <label>
              {{ t('datasets.xAxis') }}
              <select v-model="xField">
                <option v-for="f in selected.numeric_fields" :key="f" :value="f">
                  {{ t(`datasets.fields.${f}`) }}
                </option>
              </select>
            </label>
            <label>
              {{ t('datasets.yAxis') }}
              <select v-model="yField">
                <option v-for="f in selected.numeric_fields" :key="f" :value="f">
                  {{ t(`datasets.fields.${f}`) }}
                </option>
              </select>
            </label>
          </div>
          <template v-if="correlation">
            <div class="chart-box">
              <canvas ref="correlationCanvas"></canvas>
            </div>
            <p class="correlation-stats">
              {{ t('datasets.correlationR', { r: correlation.correlation_r }) }}
              · {{ t('datasets.correlationN', { n: correlation.n }) }}
            </p>
            <p class="methodology">{{ correlation.methodology }}</p>
          </template>
        </div>
        <p v-else class="correlation-unavailable">
          {{ t('datasets.correlationUnavailable') }}
        </p>
      </template>
    </main>
  </div>
</template>

<style scoped>
.dash {
  display: flex;
  height: 100%;
  min-height: 0;
}
.catalog {
  width: 260px;
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid var(--border);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.catalog-item {
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 10px 12px;
  cursor: pointer;
}
.catalog-item:hover {
  border-color: var(--teal);
}
.catalog-item.active {
  border-color: var(--teal);
  background: var(--teal-soft);
}
.catalog-name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 13.5px;
}
.catalog-desc {
  font-size: 11px;
  color: var(--muted);
  margin-top: 3px;
  line-height: 1.4;
}
.catalog-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--teal);
  margin-top: 6px;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 18px 22px;
  min-width: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}
.search-input {
  flex: 1;
  max-width: 360px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12.5px;
  color: var(--text);
}
.source {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
  text-align: right;
}
.error {
  color: var(--coral);
  font-size: 12.5px;
  font-family: var(--font-mono);
}
.loading {
  color: var(--muted);
  font-size: 12.5px;
}
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 9px;
  margin-bottom: 22px;
}
table {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
}
th {
  text-align: left;
  padding: 9px 12px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  white-space: nowrap;
  font-weight: 600;
  user-select: none;
}
th.sorted {
  color: var(--teal);
}
.sort-arrow {
  font-size: 8px;
  margin-left: 3px;
}
td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
tbody tr:last-child td {
  border-bottom: none;
}
tbody tr:hover {
  background: var(--surface-2);
}
.no-results {
  padding: 16px;
  color: var(--muted);
  font-size: 12.5px;
  text-align: center;
}

.correlation h4 {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
}
.correlation-controls {
  display: flex;
  gap: 18px;
  margin-bottom: 12px;
}
.correlation-controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}
.correlation-controls select {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--text);
}
.chart-box {
  width: 50vw;
  height: 260px;
  max-width: 100%;
}
.correlation-stats {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--teal);
  margin-top: 8px;
}
.methodology {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  margin-top: 6px;
  line-height: 1.5;
}
.correlation-unavailable {
  font-size: 12px;
  color: var(--muted);
}
</style>
