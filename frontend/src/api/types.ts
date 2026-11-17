export interface HealthResponse {
  status: string;
  version: string;
  database: { dialect: string; ok: boolean };
  gee: { available: boolean; mode?: string; error?: string | null; project?: string | null };
  stac: { available: boolean; providers: string[] };
  torch: { available: boolean; version?: string; device?: string };
  xgboost: { available: boolean; error?: string | null };
  data: {
    dem: boolean;
    osm: boolean;
    composites: number;
    lakes: number;
  };
}

export interface GeoJSONGeometry {
  type: string;
  coordinates: any;
}

export interface GeoJSONFeature<P = Record<string, any>> {
  type: "Feature";
  id?: string | number;
  geometry: GeoJSONGeometry;
  properties: P;
}

export interface GeoJSONFeatureCollection<P = Record<string, any>> {
  type: "FeatureCollection";
  features: GeoJSONFeature<P>[];
}

export interface StudyRegion {
  name: string;
  bbox: [number, number, number, number];
  geometry: GeoJSONGeometry;
}

export interface ReferencePoint {
  name: string;
  lat: number;
  lon: number;
  type: string;
  elevation_m?: number;
}

export interface TimelinePeriod {
  key: string;
  label: string;
  start: number;
  end: number;
  description?: string;
}

export interface StudyAreaResponse {
  name: string;
  bbox: [number, number, number, number]; // [w, s, e, n]
  geometry: GeoJSONGeometry;
  utm_epsg: number | string;
  regions: Record<string, StudyRegion>;
  reference_points: ReferencePoint[];
  timeline_periods: TimelinePeriod[];
  standard_comparisons: [number, number][];
  disaster_context: string;
}

export interface Job {
  id: number;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  parameters?: Record<string, any>;
  result?: any;
  log?: string | string[];
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface CoverageMission {
  mission: string;
  status: string;
  valid_fraction: number | null;
  scene_count: number;
  composite_id: number | string | null;
}

export interface CoverageYear {
  year: number;
  missions: CoverageMission[];
}

export interface IndicatorPoint {
  year: number;
  value: number | null;
  mission: string;
  valid_fraction?: number | null;
  scene_count?: number;
  window?: [string, string];
  quality_flags?: string[];
}

export interface DashboardSummaryResponse {
  coverage: {
    years: CoverageYear[];
    dem_available: boolean;
    osm_available: boolean;
    terrain_available: boolean;
  };
  lakes: {
    count: number;
    total_area_ha: number;
    reference_year: number | null;
    method: string | null;
  };
  indicators: {
    series: Record<string, IndicatorPoint[]>;
  };
  susceptibility: {
    Low: number;
    Moderate: number;
    High: number;
    "Very High": number;
    method: string | null;
    is_trained_model: boolean;
  };
  recent_jobs: Job[];
  rainfall_available: boolean;
}

export interface BandStatistic {
  band: number;
  min: number | null;
  max: number | null;
  mean: number | null;
  std: number | null;
  valid_pixels: number;
  valid_fraction: number;
}

export interface RasterAsset {
  id: number;
  name: string;
  kind: string;
  category: string;
  path_name?: string;
  crs: string;
  width: number;
  height: number;
  band_count: number;
  dtype: string;
  resolution_x: number;
  resolution_y: number;
  nodata: number | null;
  bounds_wgs84: [number, number, number, number]; // [w, s, e, n] or [[s,w],[n,e]] handled safely
  statistics?: {
    bands?: BandStatistic[];
    band_descriptions?: string[];
    [key: string]: any;
  };
  year?: number | null;
  acquired_start?: string | null;
  acquired_end?: string | null;
  source?: string | null;
  processing?: Record<string, any> | string | null;
  is_original?: boolean;
  parent_id?: number | null;
  created_at?: string;
}

export interface RasterOverlayResponse {
  image_url: string;
  bounds: [[number, number], [number, number]]; // [[S, W], [N, E]]
  legend?: {
    cmap?: string;
    vmin?: number;
    vmax?: number;
    unit?: string;
    categories?: { value: number | string; label: string; color: string }[];
  };
}

export interface VectorLayerSummary {
  key: string;
  name: string;
  category: string;
  feature_count: number;
  source: string;
  attribution?: string;
  url?: string;
}

export interface SatelliteMission {
  mission: string;
  label: string;
  instrument: string;
  gee_collection: string;
  stac_collection: string;
  native_resolution_m: number;
  bands: Record<string, string>;
  operational: [string, string | null];
  notes: string[];
  citation: string;
}

export interface SatelliteScene {
  scene_id: string;
  datetime: string;
  cloud_cover: number | null;
  footprint?: GeoJSONGeometry | null;
  preview_url?: string | null;
  quality_flags?: string[];
}

export interface SatelliteSearchResponse {
  provider: string;
  count: number;
  scenes: SatelliteScene[];
  notes: string[];
}

export interface SatelliteComposite {
  composite_id: number;
  year: number;
  mission: string;
  region: string;
  window: [string, string];
  scene_count: number;
  scenes?: { scene_id: string; datetime: string; cloud_cover: number | null }[];
  valid_fraction: number | null;
  quality_flags: string[];
  resolution_m: number;
  provider: string;
  raster: RasterAsset;
}

export interface VectorAsset {
  id: number;
  name: string;
  original_filename: string;
  crs: string;
  feature_count: number;
  geometry_types: string[];
  columns: string[];
  bounds_wgs84: [number, number, number, number];
  created_at: string;
}

export interface GeoTIFFMetadata {
  id?: number;
  name?: string;
  width: number;
  height: number;
  band_count: number;
  dtypes: string[];
  crs: string;
  epsg: number | null;
  is_projected: boolean;
  resolution: [number, number];
  units: string;
  bounds: [number, number, number, number];
  nodata: number | null;
  band_descriptions: string[];
  statistics: {
    bands: BandStatistic[];
  };
  bounds_wgs84: [number, number, number, number];
  warnings?: string[];
}

export interface LakeFeatureProperties {
  lake_id: number;
  lake_code: string;
  name: string;
  area_ha: number;
  perimeter_m: number;
  elevation_m: number | null;
  year: number;
  mission: string;
  method: string;
  observed_start?: string;
  observed_end?: string;
  first_detected?: number;
  last_detected?: number;
  n_observations?: number;
  susceptibility_category?: "Low" | "Moderate" | "High" | "Very High" | string | null;
}

export interface LakeObservation {
  year: number;
  mission: string;
  method: string;
  area_ha: number;
  perimeter_m: number;
  observed_start?: string;
  observed_end?: string;
  valid_pixel_fraction?: number | null;
  geometry?: GeoJSONGeometry;
}

export interface LakeDetailResponse {
  lake: LakeFeatureProperties & { geometry?: GeoJSONGeometry };
  observations: LakeObservation[];
}

export interface LakeStatisticsResponse {
  annual: {
    year: number;
    mission: string;
    method: string;
    lake_count: number;
    total_area_ha: number;
    valid_fraction: number | null;
  }[];
  per_lake: {
    lake_id: number;
    lake_code: string;
    name: string;
    series: { year: number; area_ha: number }[];
  }[];
}

export interface ChangeIndicatorsResponse {
  region: string;
  indicators: Record<
    string,
    {
      unit: string;
      description: string;
      series: IndicatorPoint[];
    }
  >;
}

export interface ChangeAnalysisResult {
  id: number | string;
  year_a: number;
  year_b: number;
  mission_a: string;
  mission_b: string;
  indicator: string;
  region?: string;
  statistics: {
    area_gain_ha?: number | null;
    area_loss_ha?: number | null;
    stable_ha?: number | null;
    net_change_ha?: number | null;
    mean_difference?: number | null;
    [key: string]: any;
  };
  caveats: string[];
  rasters: {
    difference?: RasterAsset | null;
    transition?: RasterAsset | null;
    before?: RasterAsset | null;
    after?: RasterAsset | null;
  };
  legend?: any;
  created_at?: string;
}

export interface GlacierSummaryResponse {
  series: {
    year: number;
    snow_ice_area_ha: number | null;
    mission: string;
    quality_flags: string[];
  }[];
  outlines: GeoJSONFeatureCollection | null;
  outline_source: string | null;
  notes: string[];
}

export interface DisasterContextResponse {
  context: string;
  mechanisms: {
    key: string;
    label: string;
    description: string;
  }[];
  key_dates: { date: string; event: string }[] | Record<string, string>;
  scenes: {
    pre: any[];
    post: any[];
  };
}

export interface DisasterCompareResponse extends ChangeAnalysisResult {
  indicators?: {
    indicator: string;
    before_value?: number | null;
    after_value?: number | null;
    change?: number | null;
    unit?: string;
    [key: string]: any;
  }[];
  affected_locations?: {
    name: string;
    lat: number;
    lon: number;
    change_summary: string;
  }[];
}

export interface GlofCriterion {
  key: string;
  label: string;
  weight: number;
  scoring: string;
  rationale: string;
  reference: string;
}

export interface GlofMethodologyResponse {
  method: string;
  version: string;
  is_trained_model: boolean;
  description: string;
  criteria: GlofCriterion[];
  classes: { label: string; min: number; max: number }[];
  limitations: string[];
}

export interface GlofFactorScore {
  value: number | string | null;
  unit: string;
  score: number;
  weight: number;
  available: boolean;
}

export interface GlofAssessment {
  lake_id: number;
  lake_code: string;
  name: string;
  method: string;
  is_trained_model: boolean;
  score: number;
  category: "Low" | "Moderate" | "High" | "Very High" | string;
  factors: Record<string, GlofFactorScore>;
  missing_parameters: string[];
  uncertainty: {
    score_range: [number, number];
    completeness: number;
    category_range: string[];
  };
  created_at: string;
}

export interface GlofMlStatusResponse {
  trainable: boolean;
  reason: string;
  required_data: string[];
  label_file_present: boolean;
}

export interface TerrainSummaryResponse {
  available: boolean;
  statistics?: Record<string, any>;
  products: Record<string, RasterAsset>;
  vectors: VectorLayerSummary[];
  dem_source: string | null;
}

export interface FlowpathResponse {
  name: string;
  geometry: GeoJSONGeometry;
  length_m: number;
  elevation_drop_m: number;
  profile: { distance_m: number; elevation_m: number }[];
  method: string;
  caveat: string;
}

export interface FloodResult {
  id: number;
  scenario_id: number;
  variable: "depth" | "velocity" | "wse" | "arrival_time" | "duration" | string;
  raster: RasterAsset;
  model_software: string;
  statistics: {
    max: number | null;
    mean: number | null;
    area_ha_wet: number | null;
  };
  extent_geometry?: GeoJSONGeometry | null;
}

export interface FloodScenario {
  id: number;
  name: string;
  source_lake_id: number | null;
  scenario_type: "hypothetical" | string;
  description: string;
  hydrograph: {
    time_s: number[];
    discharge_m3s: number[];
  } | null;
  hydrograph_source: string;
  assumptions: string[];
  boundary_conditions?: Record<string, any>;
  status: "defined" | "exported" | "results_imported" | string;
  created_at: string;
  results: FloodResult[];
}

export interface InfrastructureSummaryResponse {
  counts: Record<string, number>;
  road_length_km: number;
  source: string;
  retrieved_at: string | null;
}

export interface ExposureAnalysisResponse {
  id: number | string;
  analysis_type: string;
  statistics: {
    buildings: number;
    road_length_km: number;
    bridges: number;
    settlements: string[];
    by_category: Record<string, number>;
  };
  features: GeoJSONFeatureCollection;
  caveat: string;
}

export interface RainfallResponse {
  sources_available: string[];
  series: Record<string, { date: string; precipitation_mm: number }[]>;
  notes: string[] | string;
}

export interface ModelDatasetsResponse {
  segmentation: {
    status: "awaiting_training_data" | "ready" | string;
    image_tiles: number;
    mask_tiles: number;
    verified_masks?: number;
    splits: { train: number; val: number; test: number };
    split_strategy: string;
    directory: string;
    instructions: string[];
  };
  susceptibility: {
    status: string;
    labelled_events: number;
    instructions: string[];
  };
}

export interface ModelRunEvaluation {
  split: string;
  metrics: {
    iou: number;
    dice: number;
    precision: number;
    recall: number;
    f1: number;
    accuracy: number;
  };
  confusion_matrix: [[number, number], [number, number]];
  sample_count: number;
}

export interface ModelRun {
  id: number;
  model_type: "unet" | "deeplabv3plus" | string;
  task: string;
  status: string;
  dataset_summary?: Record<string, any>;
  hyperparameters: Record<string, any>;
  history: {
    epoch: number;
    train_loss: number;
    val_loss: number;
    val_iou: number;
    val_dice: number;
  }[];
  checkpoint_path?: string | null;
  best_epoch?: number | null;
  created_at: string;
  finished_at?: string | null;
  evaluations: ModelRunEvaluation[];
}

export interface ReportItem {
  id: number | string;
  title: string;
  created_at: string;
  download_url: string;
}
