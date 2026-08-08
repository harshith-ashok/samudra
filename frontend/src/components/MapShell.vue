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
  getOceanPoint,
  getPollution,
  getSpecies,
  getStation,
  getStations,
  getVessels,
  postNlq,
  postSttTranscribe,
  postTranslate,
} from '../api';
import type {
  MapRegion,
  NlqResponse,
  OceanPointEstimate,
  Species,
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
import OceanPointCard from './OceanPointCard.vue';
import GuidedIntro from './GuidedIntro.vue';
import ModuleRail, { type ModuleDef } from './ModuleRail.vue';
import LayerPanel, { type KpiDef, type LayerDef } from './LayerPanel.vue';
import TimelineScrubber, {
  type TimelineChangePayload,
} from './TimelineScrubber.vue';
import LanguageToggle from './LanguageToggle.vue';
import { useI18n, tEnglish } from '../composables/useI18n';
import { useVoiceRecorder } from '../composables/useVoiceRecorder';
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
const speciesChatContext = ref<{
  species: Species;
  trajectory: SpeciesTrajectory | null;
} | null>(null);
const violationCount = computed(
  () => vessels.value.filter((v) => v.in_violation).length
);
const nonCompliantCount = ref(0);
const speciesCount = ref(0);
const stateCount = computed(
  () => new Set(stations.value.map((s) => s.state)).size
);
const oceanPointClick = ref<{ lat: number; lng: number } | null>(null);
const oceanPointResult = ref<OceanPointEstimate | null>(null);
const oceanPointLoading = ref(false);
const oceanPointError = ref<string | null>(null);
const showIntro = ref(false);
const activePanel = ref<PanelKey>(null);
const clock = ref('');
const { t, currentLanguage } = useI18n();

const searchQuery = ref('');
const searchFocused = ref(false);
const nlqResult = ref<NlqResponse | null>(null);
const nlqLoading = ref(false);

// Displayed translated, but always submitted to NLQ in English — see
// useSuggestion() below and tEnglish()'s doc comment.
const suggestedQueryKeys = [
  'search.suggested1',
  'search.suggested2',
  'search.suggested3',
  'search.suggested4',
  'search.suggested5',
];

const typeColors: Record<StationType, string> = {
  buoy: '#128F82',
  edna: '#2E9E5B',
  advisory: '#D6512D',
  coral: '#B9800F',
};

const modules = computed<ModuleDef[]>(() => [
  {
    key: 'ai',
    label: t('modules.ai'),
    iconPaths: [
      'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
    ],
  },
  {
    key: 'species',
    label: t('modules.species'),
    iconPaths: ['M12 2C7 6 4 10 4 14a8 8 0 0 0 16 0c0-4-3-8-8-12z'],
  },
  {
    key: 'predict',
    label: t('modules.predict'),
    iconPaths: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'],
  },
  {
    key: 'analytics',
    label: t('modules.analytics'),
    iconPaths: ['M4 19V9', 'M11 19V4', 'M18 19v-7'],
  },
  {
    key: 'glossary',
    label: t('modules.glossary'),
    iconPaths: [
      'M12 2 2 7l10 5 10-5-10-5z',
      'M2 17l10 5 10-5',
      'M2 12l10 5 10-5',
    ],
  },
]);

const panelTitles = computed<Record<string, string>>(() => ({
  station: t('panels.station'),
  vessel: t('panels.vessel'),
  ai: t('modules.ai'),
  species: t('modules.species'),
  predict: t('modules.predict'),
  analytics: t('modules.analytics'),
  glossary: t('modules.glossary'),
}));

const stationLayerMeta = computed<
  Record<StationType, { label: string; glossaryKey: string }>
>(() => ({
  buoy: { label: t('layers.buoy'), glossaryKey: 'sst' },
  edna: { label: t('layers.edna'), glossaryKey: 'edna_confidence' },
  advisory: { label: t('layers.advisory'), glossaryKey: 'advisory' },
  coral: { label: t('layers.coral'), glossaryKey: 'dhw' },
}));

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
  ...(Object.keys(stationLayerMeta.value) as StationType[]).map((key) => ({
    key,
    label: stationLayerMeta.value[key].label,
    color: typeColors[key],
    glossaryKey: stationLayerMeta.value[key].glossaryKey,
    visible: layerVisible.value[key],
  })),
  {
    key: 'shift',
    label: t('layers.shift'),
    color: '#0F2620',
    glossaryKey: 'range_shift',
    visible: layerVisible.value.shift,
  },
  {
    key: 'vessels',
    label: t('layers.vessels'),
    color: '#5C7370',
    glossaryKey: 'vessel_tracking',
    visible: layerVisible.value.vessels,
  },
  {
    key: 'pollution',
    label: t('layers.pollution'),
    color: '#B9800F',
    glossaryKey: 'treatment_compliance',
    visible: layerVisible.value.pollution,
  },
]);

const kpis = computed<KpiDef[]>(() => [
  { label: t('kpis.stationsTracked'), value: stations.value.length },
  {
    label: t('kpis.vesselsRestricted'),
    value: violationCount.value,
    glossaryKey: 'mpa',
  },
  {
    label: t('kpis.nonCompliantPlants'),
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
let regionHighlightLayer: L.LayerGroup | null = null; // temporary area(s) an AI Assistant answer is grounded in (Phase 24)
let oceanPointMarker: L.CircleMarker | null = null; // temporary marker at the last clicked open-water point
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
  regionHighlightLayer = L.layerGroup().addTo(map);
  map.on('click', onMapClick);

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

  // Each route segment is independently land-avoiding and drawn on its own
  // (see api/types.ts SpeciesTrajectory) — concatenating them into one
  // polyline would draw an unchecked straight line across any gap between
  // two segments' endpoints, which is exactly what this was built to avoid.
  t.route_historical.forEach((segment) => {
    L.polyline(segment, {
      color: '#128F82',
      weight: 2.5,
      opacity: 0.85,
    }).addTo(trajectoryLayer!);
  });
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

  t.route_forecast.forEach((segment) => {
    L.polyline(segment, {
      color: '#B9800F',
      weight: 2,
      dashArray: '5,6',
      opacity: 0.8,
    }).addTo(trajectoryLayer!);
  });
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

  const last = t.smoothed[t.smoothed.length - 1];
  map.flyTo([last.lat, last.lng], Math.max(map.getZoom(), 6), {
    duration: 0.8,
  });
}

// A distinct color from every other layer on the map — this is meant to read
// as "the AI Assistant is pointing at this," not blend in with the
// permanent advisory/coral/vessel styling.
const REGION_HIGHLIGHT_COLOR = '#7C3AED';

function onChatRegions(mapRegions: MapRegion[]) {
  if (!map || !regionHighlightLayer) return;
  regionHighlightLayer.clearLayers();
  if (!mapRegions.length) return;

  const drawn: (L.Polygon | L.Circle)[] = [];
  mapRegions.forEach((region) => {
    const tooltip = region.approximate
      ? `<b>${region.name}</b><br>approximate area`
      : `<b>${region.name}</b>`;
    let layer: L.Polygon | L.Circle;
    if (region.kind === 'polygon') {
      layer = L.polygon(region.polygon, {
        color: REGION_HIGHLIGHT_COLOR,
        weight: 2,
        fillColor: REGION_HIGHLIGHT_COLOR,
        fillOpacity: 0,
        dashArray: '6,5',
      });
    } else {
      layer = L.circle([region.lat, region.lng], {
        radius: region.radius_km * 1000,
        color: REGION_HIGHLIGHT_COLOR,
        weight: 2,
        fillColor: REGION_HIGHLIGHT_COLOR,
        fillOpacity: 0,
        dashArray: '6,5',
      });
    }
    layer.bindTooltip(tooltip, { direction: 'center', sticky: true });
    layer.addTo(regionHighlightLayer!);
    drawn.push(layer);
  });

  // Fade the fill in rather than snapping it on — same "temporary, not just
  // another static layer" treatment as the marker pulse-on-load.
  drawn.forEach((layer) => {
    const proxy = { opacity: 0 };
    gsap.to(proxy, {
      opacity: 0.16,
      duration: 0.4,
      ease: 'power1.out',
      onUpdate: () => layer.setStyle({ fillOpacity: proxy.opacity }),
    });
  });

  const bounds = L.featureGroup(drawn).getBounds();
  if (bounds.isValid()) {
    map.flyToBounds(bounds, { padding: [60, 60], maxZoom: 8, duration: 0.8 });
  }
}

// Distinct from both the AI region-highlight purple and every station/vessel
// color, so a clicked point reads as "you asked about this spot," not as
// another permanent layer.
const OCEAN_POINT_COLOR = '#1D6FD6';

function onMapClick(e: L.LeafletMouseEvent) {
  // Leaflet's map 'click' still fires the DOM click that a marker/polygon
  // already handled itself — checking the actual target's class is the only
  // reliable way to tell "clicked open water" from "clicked a station/vessel/
  // MPA/region-highlight layer" apart, since those don't stopPropagation.
  const target = e.originalEvent.target as HTMLElement;
  if (target.closest('.leaflet-interactive')) return;
  queryOceanPoint(e.latlng.lat, e.latlng.lng);
}

async function queryOceanPoint(lat: number, lng: number) {
  if (!map) return;
  oceanPointClick.value = { lat, lng };
  oceanPointResult.value = null;
  oceanPointError.value = null;
  oceanPointLoading.value = true;

  if (oceanPointMarker) map.removeLayer(oceanPointMarker);
  oceanPointMarker = L.circleMarker([lat, lng], {
    radius: 0,
    color: '#FFFFFF',
    weight: 2,
    fillColor: OCEAN_POINT_COLOR,
    fillOpacity: 0.95,
  }).addTo(map);
  pulseMarker(oceanPointMarker, 7);

  try {
    oceanPointResult.value = await getOceanPoint(lat, lng);
  } catch (err) {
    oceanPointError.value = err instanceof Error ? err.message : String(err);
  } finally {
    oceanPointLoading.value = false;
  }
}

function closeOceanPoint() {
  oceanPointClick.value = null;
  oceanPointResult.value = null;
  oceanPointError.value = null;
  oceanPointLoading.value = false;
  if (map && oceanPointMarker) map.removeLayer(oceanPointMarker);
  oceanPointMarker = null;
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
  if (panel !== 'ai') onChatRegions([]); // highlight is only meaningful while the chat is open
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

function askAiAboutSpecies(payload: {
  species: Species;
  trajectory: SpeciesTrajectory | null;
}) {
  speciesChatContext.value = payload;
  openPanel('ai');
  nextTick(() =>
    aiChatRef.value?.send(`Tell me more about ${payload.species.common}`)
  );
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

// NLQ parses free text into a structured filter via gpt-oss, which reasons
// over English seed data — translate non-English speech to English before
// it hits that pipeline, same as the AI Assistant does.
async function transcribeForSearch(blob: Blob): Promise<string> {
  const text = await postSttTranscribe(blob, currentLanguage.value);
  if (text && currentLanguage.value !== 'en') {
    return postTranslate(text, 'en', currentLanguage.value);
  }
  return text;
}

const {
  state: micState,
  errorMsg: micErrorMsg,
  toggle: toggleMic,
  dispose: disposeMic,
} = useVoiceRecorder(
  transcribeForSearch,
  (text) => {
    searchQuery.value = text;
    searchFocused.value = true;
  },
  {
    transcribeError: () => t('chat.micError'),
    micDenied: () => t('chat.micDenied'),
  }
);

function useSuggestion(key: string) {
  // Displayed in whatever language is active, but always run against NLQ in
  // English — the query box just shows the same text the chip showed.
  searchQuery.value = t(key);
  runNlq(tEnglish(key));
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
const searchPlaceholder = computed(() => {
  if (micState.value === 'recording') return t('search.placeholderListening');
  if (micState.value === 'transcribing') return t('search.placeholderTranscribing');
  return t('search.placeholder');
});

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
  disposeMic();
  map?.remove();
});
</script>

<template>
  <div id="map" ref="mapEl"></div>

  <div class="topbar">
    <div class="brand">
      {{ t('app.brand') }}
      <small>{{ t('app.tagline') }}</small>
    </div>
    <div class="ticker">
      <span
        ><span class="dot"></span
        >{{ t('topbar.stationsLive', { count: stations.length }) }}</span
      >
      <span v-if="violationCount > 0" class="alert">{{
        t(
          violationCount === 1
            ? 'topbar.vesselRestrictedSingular'
            : 'topbar.vesselsRestrictedPlural',
          { count: violationCount }
        )
      }}</span>
      <span id="clock">{{ clock }}</span>
      <LanguageToggle v-model="currentLanguage" />
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
        :placeholder="searchPlaceholder"
        @focus="searchFocused = true"
        @blur="blurSearchSoon"
      />
      <button
        type="button"
        class="mic-btn"
        :class="micState"
        :disabled="micState === 'transcribing'"
        :title="micErrorMsg || t('search.micTitle')"
        @mousedown.prevent="toggleMic"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0" />
          <path d="M12 18v4M8 22h8" />
        </svg>
      </button>
      <span class="hint">{{ t('search.hint') }}</span>
    </div>
    <div class="search-results" :class="{ show: showResults }">
      <template v-if="!searchQuery">
        <div
          class="row"
          v-for="key in suggestedQueryKeys"
          :key="key"
          @mousedown="useSuggestion(key)"
        >
          {{ t(key) }}<span>{{ t('search.suggested') }}</span>
        </div>
      </template>
      <template v-else-if="nlqLoading">
        <div class="row loading-row">{{ t('search.translating') }}</div>
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
          {{ t('search.noMatches') }}
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

  <OceanPointCard
    v-if="oceanPointClick"
    :lat="oceanPointClick.lat"
    :lng="oceanPointClick.lng"
    :loading="oceanPointLoading"
    :error="oceanPointError"
    :point="oceanPointResult"
    @close="closeOceanPoint"
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
        :species-context="speciesChatContext"
        @regions="onChatRegions"
      />
      <SpeciesExplorer
        v-if="activePanel === 'species'"
        @trajectory="onSpeciesTrajectory"
        @ask-ai="askAiAboutSpecies"
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
.mic-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border: none;
  border-radius: 7px;
  background: none;
  color: var(--muted);
  cursor: pointer;
}
.mic-btn:hover:not(:disabled) {
  color: var(--teal);
  background: var(--surface-2);
}
.mic-btn svg {
  width: 15px;
  height: 15px;
}
.mic-btn.recording {
  color: var(--coral);
  background: var(--coral-soft);
  animation: mic-pulse 1.4s ease-in-out infinite;
}
.mic-btn.transcribing {
  color: var(--teal);
  cursor: default;
}
.mic-btn.error {
  color: var(--coral);
}
@keyframes mic-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(214, 81, 45, 0.35);
  }
  50% {
    box-shadow: 0 0 0 5px rgba(214, 81, 45, 0);
  }
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
