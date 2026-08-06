import type {
  Advisory,
  BleachingRisk,
  ChatResponse,
  NlqResponse,
  RangeShift,
  Species,
  StationDetail,
  StationSummary,
  StockForecast,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  const body = await res.json();
  return body.data as T;
}

async function postJSON<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  const body = await res.json();
  return body.data as T;
}

export const getStations = () => getJSON<StationSummary[]>("/api/stations");
export const getStation = (id: string) => getJSON<StationDetail>(`/api/stations/${id}`);
export const getSpecies = () => getJSON<Species[]>("/api/species");
export const getAdvisories = () => getJSON<Advisory[]>("/api/advisories");

export const postChat = (message: string, stationContext?: unknown) =>
  postJSON<ChatResponse>("/api/chat", { message, station_context: stationContext ?? null });

export const postNlq = (query: string) => postJSON<NlqResponse>("/api/nlq", { query });

export const getStockForecast = (species: string, region: string) =>
  getJSON<StockForecast>(
    `/api/predict/stock?species=${encodeURIComponent(species)}&region=${encodeURIComponent(region)}`,
  );

export const getBleachingRisk = (stationId: string) =>
  getJSON<BleachingRisk>(`/api/predict/bleaching?station_id=${encodeURIComponent(stationId)}`);

export const getRangeShift = (species: string) =>
  getJSON<RangeShift>(`/api/predict/range-shift?species=${encodeURIComponent(species)}`);
