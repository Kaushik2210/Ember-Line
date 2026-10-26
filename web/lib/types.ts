// Shapes of the EMBERLINE API payloads (see api/emberline/serialize.py and routes.py).

export type Metric = "frp_sum_mw" | "active_1km" | "det_count";
export type ModelChoice = "auto" | "huber" | "theilsen" | "quantile" | "isotonic";
export type DayNight = "both" | "D" | "N";
export type BBox = [number, number, number, number];

export interface Region {
  id: string;
  name: string;
  bbox: BBox;
  blurb: string;
  default_start: string;
  default_end: string;
}

export interface QualityPolicy {
  modis_min_conf: number;
  viirs_classes: string[];
  fire_types: number[];
  keep_null_type: boolean;
  persistent_mask: boolean;
  persistent_min_frac: number;
  persistent_cell_deg: number;
  persistent_min_record_days: number;
  daynight: DayNight;
}

export interface GridSpec {
  kind: "regular" | "h3";
  size_deg: number;
  h3_res: number;
}

export interface AnalyzeRequest {
  bbox?: BBox;
  geojson?: unknown;
  region_id?: string;
  start: string;
  end: string;
  quality_policy: Partial<QualityPolicy>;
  grid: Partial<GridSpec>;
  metric: Metric;
  model: ModelChoice;
  synthetic?: boolean;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "done" | "error";
  stage: string | null;
  error: string | null;
  cached: boolean;
}

export interface JobEvent {
  stage: string;
  status: string;
  error?: string | null;
}

export interface CvRow {
  model: string;
  selectable: boolean;
  r2_log: number | null;
  mae_log: number | null;
  mae_raw: number | null;
  bias_rel: number | null;
  spearman: number | null;
  coverage: number | null;
}

export interface WeeklyPair {
  week: string;
  modis: number;
  viirs: number;
  /** Prediction from a model fitted without that week's year. */
  predicted: number | null;
  lo: number | null;
  hi: number | null;
}

export interface NormalizationInfo {
  pairs: WeeklyPair[];
  chosen: string;
  cv: CvRow[];
  n_weeks: number;
  years: number[];
  interval_halfwidth_log1p: number | null;
  level: number;
  used_before?: string;
}

export interface TableRow {
  [key: string]: string | number | null;
}

export interface Markers {
  start_doy: number;
  peak_doy: number;
  end_doy: number;
  length_days: number;
  total: number;
}

export interface AnomalyEvent {
  start: string;
  end: string;
  days: number;
  direction: "high" | "low";
  peak_z: number;
  mean_z: number;
  excess: number;
  caveat: string;
  text: string;
}

export interface SeasonRank {
  season: string;
  total: number;
  year0: number;
  z: number;
  rank: number;
  text: string;
}

export interface Annotation {
  when: string;
  precision: string;
  kind: string;
  title: string;
  detail: string;
  affects: string[];
  source: string;
}

export interface PlatformRow {
  sensor: string;
  platform: string;
  first: string;
  last: string;
  detections: number;
}

export type Matrix = (number | null)[][];

export interface ResultPayload {
  meta: Record<string, unknown> & {
    acknowledgment: string;
    run_utc: string;
    emberline_version: string;
    sources: { modis: string; viirs: string };
    versions: Record<string, string>;
    model: { chosen: string | null; fitted_on: string; validation: string; interval: string | null };
  };
  bbox: BBox;
  synthetic: boolean;
  quality: {
    counts: Record<string, number>;
    notes: string[];
    platforms: PlatformRow[];
    annotations: Annotation[];
  };
  daily: { dates: string[]; modis: (number | null)[]; viirs: (number | null)[] };
  validation: {
    overpass: Record<string, number>;
    frp_ratio: Record<string, number>;
    tables: { by_frp: TableRow[]; by_daynight: TableRow[]; by_scan: TableRow[] };
    normalization: NormalizationInfo | null;
    normalization_terra_only?: NormalizationInfo;
  };
  harmonized: {
    modis_basis: string[] | null;
    dates: string[];
    value: (number | null)[];
    lo: (number | null)[];
    hi: (number | null)[];
    reconstructed: number[];
  } | null;
  calendar: {
    years: number[];
    days_per_year: number;
    harmonized: Matrix;
    lo: Matrix;
    hi: Matrix;
    modis: Matrix;
    viirs: Matrix;
    reconstructed: Matrix;
  } | null;
  seasonality: {
    climatology: { doy: number[]; p10: number[]; p25: number[]; median: number[]; p75: number[]; p90: number[] };
    markers: Markers | null;
    segments: Markers[];
    stl: { week: string[]; trend: number[]; seasonal: number[]; resid: number[] } | null;
  } | null;
  anomalies: { events: AnomalyEvent[]; seasons: SeasonRank[] };
}

export interface HotspotFeature {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: {
    sensor: "modis" | "viirs";
    platform?: string;
    frp?: number | null;
    daynight?: string;
    time?: string;
    confidence?: string | number | null;
    count?: number;
    frp_sum?: number;
    cell_deg?: number;
  };
}

export interface HotspotCollection {
  type: "FeatureCollection";
  features: HotspotFeature[];
  properties: { aggregated: boolean; total: number; cell_deg?: number };
}

export interface AvailabilityInfo {
  sources: Record<string, { min: string; max: string }>;
  note: string;
}
