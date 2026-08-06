export type StationType = "buoy" | "edna" | "advisory" | "coral";

export interface StationSummary {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: StationType;
  latest: {
    sst_c: number;
    salinity_psu: number;
    chlorophyll_mg_m3: number;
  };
  source: string;
}

export interface StationHistoryPoint {
  day: number;
  sst: number;
  salinity: number;
  chlorophyll: number;
}

export interface StationDetail extends StationSummary {
  history: StationHistoryPoint[];
}

export interface Species {
  sci: string;
  common: string;
  region: string;
  status: "LC" | "NT" | "VU" | "EN" | null;
  note: string;
}

export interface Advisory {
  id: string;
  region: string;
  species: string;
  status: "active" | "resolved";
  issued: string;
  summary: string;
  severity: "low" | "medium" | "high";
}

export interface ChatResponse {
  answer: string;
  sources: string[];
}

export interface NlqResponse {
  query: string;
  filter: Record<string, unknown>;
  trace: string;
  results: Array<Record<string, unknown> & { record_type: string }>;
}

export interface StockForecast {
  species: string;
  region: string;
  history: Array<{ date: string; tonnage: number }>;
  forecast: Array<{ month_offset: number; tonnage: number; low_80ci: number; high_80ci: number }>;
  trend_tonnage_per_month: number;
  methodology: string;
  source: string;
}

export interface BleachingRisk {
  station_id: string;
  station_name: string;
  dhw: number;
  risk_pct: number;
  alert_level: string;
  baseline_sst_c: number;
  threshold_sst_c: number;
  latest_sst_c: number;
  methodology: string;
  source: string;
}

export interface RangeShift {
  species: string;
  observed: Array<{ year: number; mean_lat: number; n: number }>;
  projection: Array<{ year: number; projected_mean_lat: number }>;
  slope_deg_lat_per_year: number;
  direction: string;
  methodology: string;
  source: string;
}
