import type {
  Advisory,
  BiodiversityIndexResponse,
  BleachingRisk,
  BleachingTrend,
  CatchVsSstResponse,
  ChatResponse,
  ComplianceTrendResponse,
  DatasetCorrelation,
  DatasetRecordsResponse,
  DatasetSummary,
  GlossaryEntry,
  NlqResponse,
  OceanPointEstimate,
  RangeShift,
  Species,
  SpeciesTrajectory,
  StationDetail,
  StationSummary,
  PollutionResponse,
  StockForecast,
  TimelineResponse,
  VesselActivityResponse,
  VesselsResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  const body = await res.json();
  return body.data as T;
}

async function postJSON<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  const body = await res.json();
  return body.data as T;
}

export const getStations = () => getJSON<StationSummary[]>('/api/stations');
export const getStation = (id: string) =>
  getJSON<StationDetail>(`/api/stations/${id}`);
export const getSpecies = () => getJSON<Species[]>('/api/species');
export const getAdvisories = () => getJSON<Advisory[]>('/api/advisories');

export const postChat = (
  message: string,
  stationContext?: unknown,
  speciesContext?: unknown
) =>
  postJSON<ChatResponse>('/api/chat', {
    message,
    station_context: stationContext ?? null,
    species_context: speciesContext ?? null,
  });

export const postNlq = (query: string) =>
  postJSON<NlqResponse>('/api/nlq', { query });

export async function postSttTranscribe(
  audioBlob: Blob,
  language = 'en'
): Promise<string> {
  const form = new FormData();
  form.append('audio', audioBlob, 'query.webm');
  form.append('language', language);
  const res = await fetch(`${API_BASE}/api/stt`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`POST /api/stt failed: ${res.status}`);
  const body = await res.json();
  return (body.data as { text: string }).text;
}

export const postTranslate = (
  text: string,
  targetLang: string,
  sourceLang = 'auto'
) =>
  postJSON<{ translated_text: string; target_lang: string }>(
    '/api/translate',
    { text, target_lang: targetLang, source_lang: sourceLang }
  ).then((r) => r.translated_text);

// sstDelta/fishingPressure/chlorophyllDelta are the Phase 21 what-if scenario
// overrides — omit (or pass the defaults) to get the real, non-hypothetical result.
export const getStockForecast = (
  species: string,
  region: string,
  sstDelta = 0,
  fishingPressure = 1
) =>
  getJSON<StockForecast>(
    `/api/predict/stock?species=${encodeURIComponent(species)}&region=${encodeURIComponent(region)}&sst_delta=${sstDelta}&fishing_pressure=${fishingPressure}`
  );

export const getBleachingRisk = (stationId: string) =>
  getJSON<BleachingRisk>(
    `/api/predict/bleaching?station_id=${encodeURIComponent(stationId)}`
  );

export const getRangeShift = (species: string, sstDelta = 0) =>
  getJSON<RangeShift>(
    `/api/predict/range-shift?species=${encodeURIComponent(species)}&sst_delta=${sstDelta}`
  );

export const getBleachingTrend = (
  stationId: string,
  sstDelta = 0,
  chlorophyllDelta = 0
) =>
  getJSON<BleachingTrend>(
    `/api/reefs/${encodeURIComponent(stationId)}/bleaching-trend?sst_delta=${sstDelta}&chlorophyll_delta=${chlorophyllDelta}`
  );

export const getSpeciesTrajectory = (speciesId: string) =>
  getJSON<SpeciesTrajectory>(
    `/api/species/${encodeURIComponent(speciesId)}/trajectory`
  );

export const getGlossary = () => getJSON<GlossaryEntry[]>('/api/glossary');

export const getTimeline = (metric: string, days = 30) =>
  getJSON<TimelineResponse>(
    `/api/timeline/${encodeURIComponent(metric)}?days=${days}`
  );

export const getVessels = () => getJSON<VesselsResponse>('/api/vessels');

export const getPollution = () => getJSON<PollutionResponse>('/api/pollution');

export const getCatchVsSst = () =>
  getJSON<CatchVsSstResponse>('/api/analytics/catch-vs-sst');
export const getBiodiversityIndex = () =>
  getJSON<BiodiversityIndexResponse>('/api/analytics/biodiversity-index');
export const getComplianceTrend = () =>
  getJSON<ComplianceTrendResponse>('/api/analytics/compliance-trend');
export const getVesselActivity = () =>
  getJSON<VesselActivityResponse>('/api/analytics/vessel-activity');

export const getDatasets = () => getJSON<DatasetSummary[]>('/api/datasets');

export const getDatasetRecords = (
  datasetId: string,
  search = '',
  sort?: string,
  order: 'asc' | 'desc' = 'asc'
) => {
  const params = new URLSearchParams({ search, order });
  if (sort) params.set('sort', sort);
  return getJSON<DatasetRecordsResponse>(
    `/api/datasets/${encodeURIComponent(datasetId)}/records?${params}`
  );
};

export const getDatasetCorrelation = (datasetId: string, x: string, y: string) =>
  getJSON<DatasetCorrelation>(
    `/api/datasets/${encodeURIComponent(datasetId)}/correlate?x=${encodeURIComponent(x)}&y=${encodeURIComponent(y)}`
  );

// Bespoke fetch (not getJSON) because the caller needs the actual reason a
// point was rejected (on land vs. too far from any station) to show the
// user something more useful than a generic "404" — FastAPI puts that in
// the JSON body's `detail`, which getJSON's generic error doesn't surface.
export async function getOceanPoint(
  lat: number,
  lng: number
): Promise<OceanPointEstimate> {
  const res = await fetch(`${API_BASE}/api/point?lat=${lat}&lng=${lng}`);
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || `GET /api/point failed: ${res.status}`);
  return body.data as OceanPointEstimate;
}
