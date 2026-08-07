<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue';
import L from 'leaflet';
import 'leaflet.markercluster';
import gsap from 'gsap';
import {
  getPollution,
  getSpecies,
  getStation,
  getStations,
  getVessels,
  postNlq,
} from '../api';
import type {
  NlqResponse,
  SpeciesTrajectory,
  StationDetail,
  StationSummary,
  StationType,
  Vessel,
  VesselsResponse,
} from '../api/types';
import StationDetailPanel from './StationDetail.vue';
import AIChat from './AIChat.vue';
import SpeciesExplorer from './SpeciesExplorer.vue';
import Predictive from './Predictive.vue';
import Analytics from './Analytics.vue';
import GlossaryPanel from './GlossaryPanel.vue';
import VesselDetail from './VesselDetail.vue';
import ImpactCard from './ImpactCard.vue';
import GuidedIntro from './GuidedIntro.vue';
import ModuleRail, { type ModuleDef } from './ModuleRail.vue';
import LayerPanel, { type KpiDef, type LayerDef } from './LayerPanel.vue';
import TimelineScrubber, {
  type TimelineChangePayload,
} from './TimelineScrubber.vue';
import { colorForMetricValue } from '../utils/colorScale';

const VESSEL_POLL_MS = 4000;

// Panel keys are plain strings (not a closed union) on purpose: new modules
// (analytics, vessel detail, ...) get added by pushing to `modules` below,
// not by touching every switch/type in this file.
type PanelKey = string | null;

const mapEl = ref<HTMLDivElement | null>(null);
const panelEl = ref<HTMLDivElement | null>(null);
const aiChatRef = ref<InstanceType<typeof AIChat> | null>(null);

const stations = ref<StationSummary[]>([]);
const selectedStation = ref<StationDetail | null>(null);
const vessels = ref<Vessel[]>([]);
const selectedVessel = ref<Vessel | null>(null);
const violationCount = computed(
  () => vessels.value.filter((v) => v.in_violation).length
);
const nonCompliantCount = ref(0);
const speciesCount = ref(0);
const stateCount = computed(
  () => new Set(stations.value.map((s) => s.state)).size
);
const showIntro = ref(false);
const activePanel = ref<PanelKey>(null);
const clock = ref('');

const searchQuery = ref('');
const searchFocused = ref(false);
const nlqResult = ref<NlqResponse | null>(null);
const nlqLoading = ref(false);

const suggestedQueries = [
  'Vulnerable species near Kerala since March',
  'SST anomalies near Goa and Chennai',
  'Active fishing advisories',
  'Coral bleaching risk in Lakshadweep',
  'Newly detected eDNA species this month',
];

const typeColors: Record<StationType, string> = {
  buoy: '#128F82',
  edna: '#2E9E5B',
  advisory: '#D6512D',
  coral: '#B9800F',
};

const modules: ModuleDef[] = [
  {
    key: 'ai',
    label: 'AI Assistant',
    iconPaths: [
      'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
    ],
  },
  {
    key: 'species',
    label: 'Movement Trends',
    iconPaths: ['M12 2C7 6 4 10 4 14a8 8 0 0 0 16 0c0-4-3-8-8-12z'],
  },
  {
    key: 'predict',
    label: 'Predictive Analytics',
    iconPaths: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'],
  },
  {
    key: 'analytics',
    label: 'Analytics',
    iconPaths: ['M4 19V9', 'M11 19V4', 'M18 19v-7'],
  },
  {
    key: 'glossary',
    label: 'Data Glossary',
    iconPaths: [
      'M12 2 2 7l10 5 10-5-10-5z',
      'M2 17l10 5 10-5',
      'M2 12l10 5 10-5',
    ],
  },
];

const panelTitles: Record<string, string> = {
  station: 'Station Detail',
  vessel: 'Vessel Detail',
  ai: 'AI Assistant',
  species: 'Movement Trends',
  predict: 'Predictive Analytics',
  analytics: 'Analytics',
  glossary: 'Data Glossary',
};

const stationLayerMeta: Record<
  StationType,
  { label: string; glossaryKey: string }
> = {
  buoy: { label: 'Ocean buoys', glossaryKey: 'sst' },
  edna: { label: 'eDNA sites', glossaryKey: 'edna_confidence' },
  advisory: { label: 'Fishing advisories', glossaryKey: 'advisory' },
  coral: { label: 'Coral bleaching risk', glossaryKey: 'dhw' },
};

const layerVisible = ref<Record<string, boolean>>({
  buoy: true,
  edna: true,
  advisory: true,
  coral: true,
  shift: true,
  vessels: true,
  pollution: true,
});

const layers = computed<LayerDef[]>(() => [
  ...(Object.keys(stationLayerMeta) as StationType[]).map((key) => ({
    key,
    label: stationLayerMeta[key].label,
    color: typeColors[key],
    glossaryKey: stationLayerMeta[key].glossaryKey,
    visible: layerVisible.value[key],
  })),
  {
    key: 'shift',
    label: 'Predicted range shift',
    color: '#0F2620',
    glossaryKey: 'range_shift',
    visible: layerVisible.value.shift,
  },
  {
    key: 'vessels',
    label: 'Vessel tracking',
    color: '#5C7370',
    glossaryKey: 'vessel_tracking',
    visible: layerVisible.value.vessels,
  },
  {
    key: 'pollution',
    label: 'Pollution sources',
    color: '#B9800F',
    glossaryKey: 'treatment_compliance',
    visible: layerVisible.value.pollution,
  },
]);

const kpis = computed<KpiDef[]>(() => [
  { label: 'Stations tracked', value: stations.value.length },
  {
    label: 'Vessels in restricted waters',
    value: violationCount.value,
    glossaryKey: 'mpa',
  },
  {
    label: 'Non-compliant plants',
    value: nonCompliantCount.value,
    glossaryKey: 'treatment_compliance',
  },
]);

let map: L.Map | null = null;
const layerGroups: Record<string, L.LayerGroup> = {}; // "shift" and "vessels" — low density, no clustering needed
const radiusLayers: Partial<Record<StationType, L.LayerGroup>> = {}; // the 70km advisory/coral circle overlays
let stationCluster: L.MarkerClusterGroup | null = null; // all station markers, regardless of type — declutters at low zoom
const stationMarkers: Record<string, L.CircleMarker> = {};
const stationBaseRadius: Record<string, number> = {};
const coralCircles: Record<string, L.Circle> = {}; // reef stress-zone overlays, resized/darkened as the timeline scrubs SST (Phase 16/18)
const vesselMarkers: Record<string, L.CircleMarker> = {};
let trajectoryLayer: L.LayerGroup | null = null; // one species' movement path, drawn from the Movement Trends panel
let mpaPolygonsDrawn = false;
let clockTimer: number | undefined;
let vesselPollTimer: number | undefined;

function isStationType(key: string): key is StationType {
  return key in typeColors;
}

function fmtClock() {
  clock.value = new Date().toLocaleTimeString('en-IN');
}

function pulseMarker(marker: L.CircleMarker, targetRadius: number) {
  const proxy = { r: 0 };
  gsap.to(proxy, {
    r: targetRadius,
    duration: 0.28,
    ease: 'back.out(2)',
    onUpdate: () => marker.setRadius(proxy.r),
  });
}

async function initMap() {
  if (!mapEl.value) return;
  map = L.map(mapEl.value, {
    zoomControl: false,
    attributionControl: true,
  }).setView([15, 79], 5);
  L.control.zoom({ position: 'bottomleft' }).addTo(map);
  L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      subdomains: 'abcd',
      maxZoom: 19,
    }
  ).addTo(map);

  (['shift', 'vessels', 'pollution'] as const).forEach((key) => {
    layerGroups[key] = L.layerGroup().addTo(map!);
  });
  (['advisory', 'coral'] as const).forEach((key) => {
    radiusLayers[key] = L.layerGroup().addTo(map!);
  });
  trajectoryLayer = L.layerGroup().addTo(map);

  // One shared cluster group across all station types — with 20+ stations,
  // per-type layer groups left dense clumps (Lakshadweep, Gujarat, Kerala) that
  // overlapped and were hard to click at country-level zoom.
  stationCluster = L.markerClusterGroup({
    maxClusterRadius: 45,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
  });
  stationCluster.addTo(map);

  stations.value.forEach((s) => {
    const marker = L.circleMarker([s.lat, s.lng], {
      radius: 0,
      color: '#FFFFFF',
      weight: 2,
      fillColor: typeColors[s.type],
      fillOpacity: 0.95,
    });
    marker.bindTooltip(`<b>${s.name}</b>`, {
      direction: 'top',
      offset: [0, -6],
    });
    marker.on('click', () => openStation(s.id));
    stationCluster!.addLayer(marker);
    const baseRadius = s.type === 'advisory' ? 9 : 7;
    stationMarkers[s.id] = marker;
    stationBaseRadius[s.id] = baseRadius;
    pulseMarker(marker, baseRadius);

    if (s.type === 'advisory' || s.type === 'coral') {
      const circle = L.circle([s.lat, s.lng], {
        radius: 70000,
        color: typeColors[s.type],
        weight: 1,
        fillColor: typeColors[s.type],
        fillOpacity: 0.07,
      }).addTo(radiusLayers[s.type]!);
      if (s.type === 'coral') coralCircles[s.id] = circle;
    }
  });

  // Illustrative range-shift paths — northward drift for warm-water pelagic species,
  // shown as a static overlay; the real per-species trajectory (computed from actual
  // OBIS/GBIF records) is drawn on demand from the Movement Trends panel — see
  // onSpeciesTrajectory() — and the basic single-line version lives in Predictive.vue.
  const shiftPaths: [number, number][][] = [
    [
      [13.0827, 80.2707],
      [15.5, 81.0],
      [18.0, 83.5],
      [20.5, 86.5],
    ],
    [
      [9.9312, 76.2673],
      [11.5, 75.8],
      [13.5, 74.5],
      [15.5, 73.5],
    ],
  ];
  shiftPaths.forEach((path) => {
    L.polyline(path, {
      color: '#0F2620',
      weight: 1.6,
      dashArray: '5,6',
      opacity: 0.5,
    }).addTo(layerGroups.shift!);
    const end = path[path.length - 1];
    L.circleMarker(end, {
      radius: 4,
      color: '#FFFFFF',
      weight: 1.5,
      fillColor: '#0F2620',
      fillOpacity: 1,
    }).addTo(layerGroups.shift!);
  });
}

function openVessel(id: string) {
  const v = vessels.value.find((x) => x.id === id);
  if (!v) return;
  selectedVessel.value = v;
  openPanel('vessel');
}

function renderVessels(payload: VesselsResponse) {
  if (!map) return;
  if (!mpaPolygonsDrawn) {
    payload.mpa_zones.forEach((zone) => {
      L.polygon(zone.polygon, {
        color: '#D6512D',
        weight: 1.5,
        fillColor: '#D6512D',
        fillOpacity: 0.08,
        dashArray: '4,4',
      })
        .bindTooltip(`<b>${zone.name}</b>`, { direction: 'center' })
        .addTo(layerGroups.vessels!);
    });
    mpaPolygonsDrawn = true;
  }
  payload.vessels.forEach((v) => {
    const color = v.in_violation ? '#D6512D' : '#5C7370';
    let marker = vesselMarkers[v.id];
    if (!marker) {
      marker = L.circleMarker([v.lat, v.lng], {
        radius: 5,
        color: '#FFFFFF',
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.95,
      });
      marker.on('click', () => openVessel(v.id));
      marker.addTo(layerGroups.vessels!);
      vesselMarkers[v.id] = marker;
    } else {
      marker.setLatLng([v.lat, v.lng]);
      marker.setStyle({ fillColor: color });
    }
    marker.bindTooltip(
      `<b>${v.name}</b>${v.in_violation ? ' — in protected zone' : ''}`,
      { direction: 'top', offset: [0, -6] }
    );
  });
  vessels.value = payload.vessels;
  if (activePanel.value === 'vessel' && selectedVessel.value) {
    selectedVessel.value =
      payload.vessels.find((v) => v.id === selectedVessel.value!.id) ??
      selectedVessel.value;
  }
}

async function loadVessels() {
  try {
    renderVessels(await getVessels());
  } catch {
    // backend unreachable — leave existing markers as-is
  }
}

const complianceColors: Record<string, string> = {
  compliant: '#2E9E5B',
  'non-compliant': '#D6512D',
  'under-review': '#B9800F',
};

async function loadPollution() {
  if (!map) return;
  try {
    const payload = await getPollution();
    nonCompliantCount.value = payload.non_compliant_count;
    payload.plants.forEach((p) => {
      const color = complianceColors[p.compliance] ?? '#5C7370';
      const marker = L.circleMarker([p.lat, p.lng], {
        radius: 6,
        color: '#FFFFFF',
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.9,
      });
      marker.bindTooltip(`<b>${p.name}</b>`, {
        direction: 'top',
        offset: [0, -6],
      });
      marker.bindPopup(
        `<b>${p.name}</b><br>${p.city} · ${p.type}<br>Discharge: ${p.discharge_mld} MLD<br>Compliance: ${p.compliance}<br>Last inspected: ${p.last_inspected}`
      );
      marker.addTo(layerGroups.pollution!);
    });
  } catch {
    // backend unreachable — pollution layer stays empty
  }
}

const SST_STRESS_MIN = 27; // baseline-ish SST in the seed data — no stress below this
const SST_STRESS_MAX = 30.5; // near the top of the seed range — full stress at/above this

function onTimelineChange(payload: TimelineChangePayload) {
  for (const [stationId, value] of Object.entries(payload.values)) {
    const marker = stationMarkers[stationId];
    if (marker) {
      marker.setStyle({
        fillColor: colorForMetricValue(payload.metric, value),
        fillOpacity: payload.kind === 'forecast' ? 0.5 : 0.95,
        dashArray: payload.kind === 'forecast' ? '2,3' : undefined,
      });
      marker.setRadius(stationBaseRadius[stationId] ?? 7);
    }

    // Reef zones visibly darken/expand as thermal stress builds while scrubbing SST —
    // driven by the same recorded/forecast SST values as the marker color (Phase 16/18).
    if (payload.metric === 'sst') {
      const circle = coralCircles[stationId];
      if (!circle) continue;
      const t = Math.max(
        0,
        Math.min(
          1,
          (value - SST_STRESS_MIN) / (SST_STRESS_MAX - SST_STRESS_MIN)
        )
      );
      circle.setRadius(70000 + t * 45000);
      circle.setStyle({
        fillColor: colorForMetricValue('sst', value),
        fillOpacity: 0.06 + t * 0.22,
      });
    }
  }
}

function onSpeciesTrajectory(t: SpeciesTrajectory | null) {
  if (!map || !trajectoryLayer) return;
  trajectoryLayer.clearLayers();
  if (!t) return;

  const historicalPath: [number, number][] = t.smoothed.map((p) => [
    p.lat,
    p.lng,
  ]);
  L.polyline(historicalPath, {
    color: '#128F82',
    weight: 2.5,
    opacity: 0.85,
  }).addTo(trajectoryLayer);
  t.smoothed.forEach((p, i) => {
    const isLatest = i === t.smoothed.length - 1;
    L.circleMarker([p.lat, p.lng], {
      radius: isLatest ? 6 : 3.5,
      color: '#FFFFFF',
      weight: 1.5,
      fillColor: '#128F82',
      fillOpacity: 0.95,
    })
      .bindTooltip(`${p.year}`, { direction: 'top', offset: [0, -4] })
      .addTo(trajectoryLayer!);
  });

  const last = t.smoothed[t.smoothed.length - 1];
  const forecastPath: [number, number][] = [
    [last.lat, last.lng],
    ...t.forecast.map((p): [number, number] => [p.lat, p.lng]),
  ];
  L.polyline(forecastPath, {
    color: '#B9800F',
    weight: 2,
    dashArray: '5,6',
    opacity: 0.8,
  }).addTo(trajectoryLayer);
  t.forecast.forEach((p) => {
    L.circleMarker([p.lat, p.lng], {
      radius: 3.5,
      color: '#FFFFFF',
      weight: 1.5,
      fillColor: '#B9800F',
      fillOpacity: 0.85,
    })
      .bindTooltip(`${p.year} (forecast)`, {
        direction: 'top',
        offset: [0, -4],
      })
      .addTo(trajectoryLayer!);
  });

  map.flyTo([last.lat, last.lng], Math.max(map.getZoom(), 6), {
    duration: 0.8,
  });
}

function toggleLayer(key: string) {
  if (!map) return;
  layerVisible.value[key] = !layerVisible.value[key];
  const visible = layerVisible.value[key];

  if (isStationType(key)) {
    if (!stationCluster) return;
    stations.value
      .filter((s) => s.type === key)
      .forEach((s) => {
        const marker = stationMarkers[s.id];
        if (!marker) return;
        if (visible) stationCluster!.addLayer(marker);
        else stationCluster!.removeLayer(marker);
      });
    const radiusLayer = radiusLayers[key];
    if (radiusLayer) {
      if (visible) map.addLayer(radiusLayer);
      else map.removeLayer(radiusLayer);
    }
    return;
  }

  const group = layerGroups[key];
  if (!group) return;
  if (visible) map.addLayer(group);
  else map.removeLayer(group);
}

async function openStation(id: string) {
  try {
    selectedStation.value = await getStation(id);
    openPanel('station');
  } catch {
    // backend unreachable — silently ignore, panel just won't open
  }
}

function openPanel(panel: string) {
  activePanel.value = panel;
}

function closePanel() {
  activePanel.value = null;
}

watch(activePanel, async (panel) => {
  await nextTick();
  if (!panelEl.value) return;
  const closedX = panelEl.value.getBoundingClientRect().width;
  gsap.to(panelEl.value, {
    x: panel ? 0 : closedX,
    duration: 0.25,
    ease: 'power2.out',
  });
});

function askAiAboutStation(station: StationDetail) {
  openPanel('ai');
  nextTick(() => aiChatRef.value?.send(`Tell me more about ${station.name}`));
}

async function runNlq(query: string) {
  if (!query.trim()) {
    nlqResult.value = null;
    return;
  }
  nlqLoading.value = true;
  try {
    nlqResult.value = await postNlq(query);
  } catch {
    nlqResult.value = null;
  } finally {
    nlqLoading.value = false;
  }
}

let nlqDebounce: number | undefined;
watch(searchQuery, (q) => {
  window.clearTimeout(nlqDebounce);
  nlqDebounce = window.setTimeout(() => runNlq(q), 350);
});

function useSuggestion(q: string) {
  searchQuery.value = q;
  runNlq(q);
}

function blurSearchSoon() {
  window.setTimeout(() => (searchFocused.value = false), 150);
}

function flyToStation(id: string) {
  const s = stations.value.find((x) => x.id === id);
  if (!s || !map) return;
  map.flyTo([s.lat, s.lng], 8, { duration: 1.1 });
  window.setTimeout(() => openStation(id), 500);
  searchFocused.value = false;
}

const showResults = computed(() => searchFocused.value);

onMounted(async () => {
  fmtClock();
  clockTimer = window.setInterval(fmtClock, 1000);
  try {
    stations.value = await getStations();
  } catch {
    stations.value = [];
  }
  await nextTick();
  initMap();
  await loadVessels();
  vesselPollTimer = window.setInterval(loadVessels, VESSEL_POLL_MS);
  await loadPollution();
  try {
    speciesCount.value = (await getSpecies()).length;
  } catch {
    speciesCount.value = 0;
  }

  if (!localStorage.getItem('samudra_intro_seen')) {
    window.setTimeout(() => (showIntro.value = true), 600);
  }
});

onBeforeUnmount(() => {
  window.clearInterval(clockTimer);
  window.clearInterval(vesselPollTimer);
  map?.remove();
});
</script>

<template>
  <div id="map" ref="mapEl"></div>

  <div class="topbar">
    <div class="brand">
      SAMUDRA
      <small>Unified Ocean Intelligence</small>
    </div>
    <div class="ticker">
      <span><span class="dot"></span>{{ stations.length }} stations live</span>
      <span v-if="violationCount > 0" class="alert"
        >{{ violationCount }} vessel{{ violationCount === 1 ? '' : 's' }} in
        restricted waters</span
      >
      <span id="clock">{{ clock }}</span>
    </div>
  </div>

  <div class="searchwrap">
    <div class="searchbar">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
      >
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.35-4.35" />
      </svg>
      <input
        v-model="searchQuery"
        placeholder="Ask the map — e.g. 'vulnerable species near Kerala since March'"
        @focus="searchFocused = true"
        @blur="blurSearchSoon"
      />
      <span class="hint">NLQ</span>
    </div>
    <div class="search-results" :class="{ show: showResults }">
      <template v-if="!searchQuery">
        <div
          class="row"
          v-for="q in suggestedQueries"
          :key="q"
          @mousedown="useSuggestion(q)"
        >
          {{ q }}<span>suggested</span>
        </div>
      </template>
      <template v-else-if="nlqLoading">
        <div class="row loading-row">translating query…</div>
      </template>
      <template v-else-if="nlqResult">
        <div class="trace">{{ nlqResult.trace }}</div>
        <div
          v-for="(r, i) in nlqResult.results"
          :key="i"
          class="row"
          @mousedown="
            r.record_type === 'station'
              ? flyToStation(r.id as string)
              : undefined
          "
        >
          {{ (r.name ?? r.common ?? r.sci ?? r.summary) as string }}
          <span>{{ r.record_type }}</span>
        </div>
        <div v-if="!nlqResult.results.length" class="row no-match">
          No matches — try a region, species, or advisory keyword
        </div>
      </template>
    </div>
  </div>

  <ModuleRail
    :modules="modules"
    :active-panel="activePanel"
    @open="openPanel"
  />

  <LayerPanel :layers="layers" :kpis="kpis" @toggle="toggleLayer" />

  <ImpactCard
    :station-count="stations.length"
    :state-count="stateCount"
    :species-count="speciesCount"
  />

  <TimelineScrubber @change="onTimelineChange" />

  <GuidedIntro v-if="showIntro" @done="showIntro = false" />

  <div class="side-panel" ref="panelEl">
    <div class="panel-header">
      <h3>{{ activePanel ? panelTitles[activePanel] : '' }}</h3>
      <button @click="closePanel">×</button>
    </div>
    <div class="panel-body">
      <StationDetailPanel
        v-if="activePanel === 'station'"
        :station="selectedStation"
        @ask-ai="askAiAboutStation"
      />
      <VesselDetail v-if="activePanel === 'vessel'" :vessel="selectedVessel" />
      <AIChat
        v-if="activePanel === 'ai'"
        ref="aiChatRef"
        :station-context="selectedStation"
      />
      <SpeciesExplorer
        v-if="activePanel === 'species'"
        @trajectory="onSpeciesTrajectory"
      />
      <Predictive v-if="activePanel === 'predict'" />
      <Analytics v-if="activePanel === 'analytics'" />
      <GlossaryPanel v-if="activePanel === 'glossary'" />
    </div>
  </div>
</template>

<style scoped>
#map {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: #e7eeee;
}

.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 700;
  font-size: 15.5px;
  letter-spacing: -0.01em;
}
.brand .mark {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: var(--teal);
  flex-shrink: 0;
}
.brand small {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  font-weight: 500;
  letter-spacing: 0.08em;
  margin-left: 3px;
  text-transform: uppercase;
}
.ticker {
  display: flex;
  align-items: center;
  gap: 18px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted);
}
.ticker span {
  display: flex;
  align-items: center;
}
.ticker .alert {
  color: var(--coral);
  font-weight: 600;
}
.ticker .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--edna);
  margin-right: 7px;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.searchwrap {
  position: fixed;
  top: 76px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  width: min(560px, 88vw);
}
.searchbar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 11px 15px;
  box-shadow: var(--shadow);
}
.searchbar svg {
  width: 15px;
  height: 15px;
  color: var(--muted);
  flex-shrink: 0;
}
.searchbar input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 13px;
  font-family: var(--font-body);
}
.searchbar .hint {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 2px 6px;
}
.search-results {
  margin-top: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  display: none;
  box-shadow: var(--shadow);
  max-height: 340px;
  overflow-y: auto;
}
.search-results.show {
  display: block;
}
.search-results .trace {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--teal);
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--teal-soft);
}
.search-results .row {
  padding: 10px 14px;
  font-size: 12.5px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.search-results .row:last-child {
  border-bottom: none;
}
.search-results .row:hover {
  background: var(--surface-2);
}
.search-results .row span {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 10.5px;
  white-space: nowrap;
}
.search-results .no-match,
.search-results .loading-row {
  cursor: default;
  color: var(--muted);
}

.side-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(50vw, 720px);
  min-width: min(400px, 92vw);
  z-index: 30;
  background: var(--surface);
  border-left: 1px solid var(--border);
  box-shadow: -6px 0 24px rgba(15, 38, 32, 0.06);
  transform: translateX(100%);
  display: flex;
  flex-direction: column;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
}
.panel-header h3 {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 17px;
}
.panel-header button {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--muted);
  width: 26px;
  height: 26px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 14px;
}
.panel-header button:hover {
  color: var(--coral);
  border-color: var(--coral);
}
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 20px;
}
</style>
