<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";
import gsap from "gsap";
import { getStation, getStations, postNlq } from "../api";
import type { NlqResponse, StationDetail, StationSummary, StationType } from "../api/types";
import StationDetailPanel from "./StationDetail.vue";
import AIChat from "./AIChat.vue";
import SpeciesExplorer from "./SpeciesExplorer.vue";
import Predictive from "./Predictive.vue";

type PanelType = "station" | "ai" | "species" | "predict" | null;

const mapEl = ref<HTMLDivElement | null>(null);
const panelEl = ref<HTMLDivElement | null>(null);
const aiChatRef = ref<InstanceType<typeof AIChat> | null>(null);

const stations = ref<StationSummary[]>([]);
const selectedStation = ref<StationDetail | null>(null);
const activePanel = ref<PanelType>(null);
const clock = ref("");

const searchQuery = ref("");
const searchFocused = ref(false);
const nlqResult = ref<NlqResponse | null>(null);
const nlqLoading = ref(false);

const suggestedQueries = [
  "Vulnerable species near Kerala since March",
  "SST anomalies near Goa and Chennai",
  "Active fishing advisories",
  "Coral bleaching risk in Lakshadweep",
  "Newly detected eDNA species this month",
];

const typeColors: Record<StationType, string> = {
  buoy: "#128F82",
  edna: "#2E9E5B",
  advisory: "#D6512D",
  coral: "#B9800F",
};

const panelTitles: Record<Exclude<PanelType, null>, string> = {
  station: "Station Detail",
  ai: "AI Assistant",
  species: "Species Explorer",
  predict: "Predictive Analytics",
};

const layerVisible = ref<Record<StationType | "shift", boolean>>({
  buoy: true,
  edna: true,
  advisory: true,
  coral: true,
  shift: true,
});

let map: L.Map | null = null;
const layerGroups: Partial<Record<StationType | "shift", L.LayerGroup>> = {};
let clockTimer: number | undefined;

function fmtClock() {
  clock.value = new Date().toLocaleTimeString("en-IN");
}

function pulseMarker(marker: L.CircleMarker, targetRadius: number) {
  const proxy = { r: 0 };
  gsap.to(proxy, {
    r: targetRadius,
    duration: 0.28,
    ease: "back.out(2)",
    onUpdate: () => marker.setRadius(proxy.r),
  });
}

async function initMap() {
  if (!mapEl.value) return;
  map = L.map(mapEl.value, { zoomControl: false, attributionControl: true }).setView([15, 79], 5);
  L.control.zoom({ position: "bottomleft" }).addTo(map);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap &copy; CARTO",
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  (["buoy", "edna", "advisory", "coral", "shift"] as const).forEach((key) => {
    layerGroups[key] = L.layerGroup().addTo(map!);
  });

  stations.value.forEach((s) => {
    const marker = L.circleMarker([s.lat, s.lng], {
      radius: 0,
      color: "#FFFFFF",
      weight: 2,
      fillColor: typeColors[s.type],
      fillOpacity: 0.95,
    });
    marker.bindTooltip(`<b>${s.name}</b>`, { direction: "top", offset: [0, -6] });
    marker.on("click", () => openStation(s.id));
    marker.addTo(layerGroups[s.type]!);
    pulseMarker(marker, s.type === "advisory" ? 9 : 7);

    if (s.type === "advisory" || s.type === "coral") {
      L.circle([s.lat, s.lng], {
        radius: 70000,
        color: typeColors[s.type],
        weight: 1,
        fillColor: typeColors[s.type],
        fillOpacity: 0.07,
      }).addTo(layerGroups[s.type]!);
    }
  });

  // Illustrative range-shift paths — northward drift for warm-water pelagic species,
  // shown as a static overlay; the actual per-species trend line lives in the
  // Predictive Analytics panel (/api/predict/range-shift), which is the real computation.
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
    L.polyline(path, { color: "#0F2620", weight: 1.6, dashArray: "5,6", opacity: 0.5 }).addTo(layerGroups.shift!);
    const end = path[path.length - 1];
    L.circleMarker(end, { radius: 4, color: "#FFFFFF", weight: 1.5, fillColor: "#0F2620", fillOpacity: 1 }).addTo(
      layerGroups.shift!,
    );
  });
}

function toggleLayer(key: StationType | "shift") {
  if (!map) return;
  const group = layerGroups[key];
  if (!group) return;
  layerVisible.value[key] = !layerVisible.value[key];
  if (layerVisible.value[key]) map.addLayer(group);
  else map.removeLayer(group);
}

async function openStation(id: string) {
  try {
    selectedStation.value = await getStation(id);
    openPanel("station");
  } catch {
    // backend unreachable — silently ignore, panel just won't open
  }
}

function openPanel(panel: Exclude<PanelType, null>) {
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
    ease: "power2.out",
  });
});

function askAiAboutStation(station: StationDetail) {
  openPanel("ai");
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
});

onBeforeUnmount(() => {
  window.clearInterval(clockTimer);
  map?.remove();
});
</script>

<template>
  <div id="map" ref="mapEl"></div>

  <div class="topbar">
    <div class="brand">
      <span class="mark"></span>SAMUDRA
      <small>Unified Ocean Intelligence</small>
    </div>
    <div class="ticker">
      <span><span class="dot"></span>{{ stations.length }} stations live</span>
      <span id="clock">{{ clock }}</span>
    </div>
  </div>

  <div class="searchwrap">
    <div class="searchbar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
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
        <div class="row" v-for="q in suggestedQueries" :key="q" @mousedown="useSuggestion(q)">
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
          @mousedown="r.record_type === 'station' ? flyToStation(r.id as string) : undefined"
        >
          {{ (r.name ?? r.common ?? r.sci ?? r.summary) as string }}
          <span>{{ r.record_type }}</span>
        </div>
        <div v-if="!nlqResult.results.length" class="row no-match">No matches — try a region, species, or advisory keyword</div>
      </template>
    </div>
  </div>

  <div class="fab-stack">
    <div class="fab" :class="{ active: activePanel === 'ai' }" @click="openPanel('ai')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>AI Assistant
    </div>
    <div class="fab" :class="{ active: activePanel === 'species' }" @click="openPanel('species')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
        <path d="M12 2C7 6 4 10 4 14a8 8 0 0 0 16 0c0-4-3-8-8-12z" />
      </svg>Species Explorer
    </div>
    <div class="fab" :class="{ active: activePanel === 'predict' }" @click="openPanel('predict')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
        <path d="M3 17l6-6 4 4 8-8" />
        <path d="M15 7h6v6" />
      </svg>Predictive Analytics
    </div>
  </div>

  <div class="layer-panel">
    <h4>Map Layers</h4>
    <label class="layer-row" v-for="key in (['buoy', 'edna', 'advisory', 'coral', 'shift'] as const)" :key="key">
      <input type="checkbox" :checked="layerVisible[key]" @change="toggleLayer(key)" />
      <i :style="{ background: key === 'shift' ? '#0F2620' : typeColors[key] }"></i>
      {{ { buoy: "Ocean buoys", edna: "eDNA sites", advisory: "Fishing advisories", coral: "Coral bleaching risk", shift: "Predicted range shift" }[key] }}
    </label>
    <div class="divider"></div>
    <div class="kpi-mini"><span>Stations tracked</span><b>{{ stations.length }}</b></div>
  </div>

  <div class="side-panel" ref="panelEl">
    <div class="panel-header">
      <h3>{{ activePanel ? panelTitles[activePanel] : "" }}</h3>
      <button @click="closePanel">×</button>
    </div>
    <div class="panel-body">
      <StationDetailPanel v-if="activePanel === 'station'" :station="selectedStation" @ask-ai="askAiAboutStation" />
      <AIChat v-if="activePanel === 'ai'" ref="aiChatRef" :station-context="selectedStation" />
      <SpeciesExplorer v-if="activePanel === 'species'" />
      <Predictive v-if="activePanel === 'predict'" />
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
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
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

.fab-stack {
  position: fixed;
  left: 20px;
  top: 150px;
  z-index: 25;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 186px;
}
.fab {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 9px;
  padding: 11px 13px;
  cursor: pointer;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  box-shadow: var(--shadow);
  transition: border-color 0.12s, color 0.12s;
}
.fab svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  color: var(--muted);
}
.fab:hover {
  border-color: var(--teal);
}
.fab.active {
  background: var(--teal);
  color: #fff;
  border-color: var(--teal);
}
.fab.active svg {
  color: #fff;
}

.layer-panel {
  position: fixed;
  right: 20px;
  bottom: 26px;
  z-index: 20;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
  width: 200px;
}
.layer-panel h4 {
  font-family: var(--font-mono);
  font-size: 9.5px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 10px;
}
.layer-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 0;
  font-size: 12.5px;
  cursor: pointer;
}
.layer-row input {
  accent-color: var(--teal);
  width: 14px;
  height: 14px;
}
.layer-row i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
}
.layer-panel .divider {
  height: 1px;
  background: var(--border);
  margin: 10px 0;
}
.kpi-mini {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--muted);
  padding: 3px 0;
}
.kpi-mini b {
  color: var(--text);
  font-weight: 600;
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
