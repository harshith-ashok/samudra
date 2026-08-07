export type StationType = 'buoy' | 'edna' | 'advisory' | 'coral';

export interface StationSummary {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: StationType;
  state: string;
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
  status: 'LC' | 'NT' | 'VU' | 'EN' | null;
  note: string;
}

export interface Advisory {
  id: string;
  region: string;
  species: string;
  status: 'active' | 'resolved';
  issued: string;
  summary: string;
  severity: 'low' | 'medium' | 'high';
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
  forecast: Array<{
    month_offset: number;
    tonnage: number;
    low_80ci: number;
    high_80ci: number;
  }>;
  trend_tonnage_per_month: number;
  conclusion: string;
  confidence: string;
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
  conclusion: string;
  confidence: string;
  methodology: string;
  source: string;
}

export interface BleachingTrendWeek {
  week: number;
  mean_sst_c: number;
  excess_c: number;
  cumulative_dhw: number;
}

export interface BleachingFactor {
  factor: string;
  label: string;
  weight: number;
  raw_value: number;
  normalized: number;
  contribution_pct: number;
}

export interface BleachingTrend {
  station_id: string;
  station_name: string;
  weekly_series: BleachingTrendWeek[];
  baseline_sst_c: number;
  threshold_sst_c: number;
  composite_score: number;
  alert_level: string;
  factors: BleachingFactor[];
  conclusion: string;
  confidence: string;
  methodology: string;
  source: string;
}

export interface SpeciesTrajectoryPoint {
  year: number;
  lat: number;
  lng: number;
  n?: number;
}

export interface SpeciesTrajectory {
  species_id: string;
  scientific_name: string;
  common_name: string;
  historical: SpeciesTrajectoryPoint[];
  smoothed: SpeciesTrajectoryPoint[];
  forecast: SpeciesTrajectoryPoint[];
  drift_km: number;
  direction: string;
  conclusion: string;
  confidence: string;
  methodology: string;
  source: string;
}

export interface TimelinePoint {
  day: number;
  value: number;
  kind: 'recorded' | 'forecast';
}

export interface TimelineResponse {
  metric: string;
  days: number;
  min_day: number;
  max_day: number;
  forecast_from_day: number;
  stations: Record<string, TimelinePoint[]>;
  methodology: string;
}

export interface MpaZone {
  id: string;
  name: string;
  region: string;
  source: string;
  polygon: [number, number][];
}

export interface Vessel {
  id: string;
  name: string;
  type: string;
  lat: number;
  lng: number;
  heading_deg: number;
  speed_knots: number;
  track: [number, number][];
  in_violation: boolean;
  violation_zone: string | null;
}

export interface VesselsResponse {
  vessels: Vessel[];
  mpa_zones: MpaZone[];
  violation_count: number;
  source: string;
}

export interface TreatmentPlant {
  id: string;
  name: string;
  city: string;
  region: string;
  lat: number;
  lng: number;
  type: 'STP' | 'ETP';
  discharge_mld: number;
  compliance: 'compliant' | 'non-compliant' | 'under-review';
  last_inspected: string;
}

export interface PollutionResponse {
  plants: TreatmentPlant[];
  non_compliant_count: number;
  source: string;
}

export interface CatchVsSstSeries {
  species: string;
  region: string;
  points: { date: string; sst_c: number; tonnage: number }[];
  correlation_r: number;
}

export interface CatchVsSstResponse {
  series: CatchVsSstSeries[];
  methodology: string;
}

export interface BiodiversityIndexResponse {
  regions: { region: string; species_count: number }[];
  methodology: string;
}

export interface ComplianceTrendResponse {
  trend: { month: string; pct_compliant: number }[];
  current_snapshot_pct: number;
  methodology: string;
}

export interface VesselActivityResponse {
  zones: {
    zone_id: string;
    zone_name: string;
    violation_ticks: number;
    total_ticks: number;
  }[];
  samples_per_vessel_loop: number;
  methodology: string;
}

export interface GlossaryEntry {
  key: string;
  title: string;
  what_it_is: string;
  why_it_matters: string;
}

export interface RangeShift {
  species: string;
  observed: Array<{ year: number; mean_lat: number; n: number }>;
  projection: Array<{ year: number; projected_mean_lat: number }>;
  slope_deg_lat_per_year: number;
  direction: string;
  conclusion: string;
  confidence: string;
  methodology: string;
  source: string;
}
