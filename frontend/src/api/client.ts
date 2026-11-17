import type {
  ChangeAnalysisResult,
  ChangeIndicatorsResponse,
  DashboardSummaryResponse,
  DisasterCompareResponse,
  DisasterContextResponse,
  ExposureAnalysisResponse,
  FloodResult,
  FloodScenario,
  FlowpathResponse,
  GeoJSONFeatureCollection,
  GeoTIFFMetadata,
  GlacierSummaryResponse,
  GlofAssessment,
  GlofMethodologyResponse,
  GlofMlStatusResponse,
  HealthResponse,
  InfrastructureSummaryResponse,
  Job,
  LakeDetailResponse,
  LakeFeatureProperties,
  LakeStatisticsResponse,
  ModelDatasetsResponse,
  ModelRun,
  RainfallResponse,
  RasterAsset,
  RasterOverlayResponse,
  ReportItem,
  SatelliteComposite,
  SatelliteMission,
  SatelliteSearchResponse,
  StudyAreaResponse,
  TerrainSummaryResponse,
  VectorAsset,
  VectorLayerSummary,
} from "./types";

const API_BASE = "/api";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = path.startsWith("http")
    ? path
    : path.startsWith("/api")
    ? path
    : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const headers = new Headers(options?.headers || {});
  if (
    options?.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson && typeof errJson.detail === "string") {
        detail = errJson.detail;
      } else if (errJson && Array.isArray(errJson.detail)) {
        detail = errJson.detail
          .map((d: any) => d.msg || JSON.stringify(d))
          .join("; ");
      } else if (errJson && errJson.message) {
        detail = errJson.message;
      }
    } catch {
      // fallback to statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  // System
  getHealth: () => apiFetch<HealthResponse>("/health"),
  getStudyArea: () => apiFetch<StudyAreaResponse>("/study-area"),
  getDashboardSummary: () =>
    apiFetch<DashboardSummaryResponse>("/dashboard/summary"),
  getJobs: (limit = 50) => apiFetch<Job[]>(`/jobs?limit=${limit}`),
  getJob: (id: number) => apiFetch<Job>(`/jobs/${id}`),

  // Rasters & Vectors
  getRasters: (params?: { kind?: string; category?: string; year?: number }) => {
    const q = new URLSearchParams();
    if (params?.kind) q.set("kind", params.kind);
    if (params?.category) q.set("category", params.category);
    if (params?.year !== undefined) q.set("year", String(params.year));
    const qs = q.toString();
    return apiFetch<RasterAsset[]>(`/rasters${qs ? `?${qs}` : ""}`);
  },
  getRaster: (id: number) => apiFetch<RasterAsset>(`/rasters/${id}`),
  getRasterOverlay: (
    id: number,
    params?: {
      bands?: string;
      cmap?: string;
      vmin?: number;
      vmax?: number;
      categorical?: string;
    }
  ) => {
    const q = new URLSearchParams();
    if (params?.bands) q.set("bands", params.bands);
    if (params?.cmap) q.set("cmap", params.cmap);
    if (params?.vmin !== undefined) q.set("vmin", String(params.vmin));
    if (params?.vmax !== undefined) q.set("vmax", String(params.vmax));
    if (params?.categorical) q.set("categorical", params.categorical);
    const qs = q.toString();
    return apiFetch<RasterOverlayResponse>(
      `/rasters/${id}/overlay${qs ? `?${qs}` : ""}`
    );
  },
  getRasterDownloadUrl: (id: number) => `/api/rasters/${id}/download`,
  getVectors: () => apiFetch<VectorLayerSummary[]>("/vectors"),
  getVectorGeoJSON: (key: string) =>
    apiFetch<GeoJSONFeatureCollection>(`/vectors/${key}`),

  // Satellite
  getMissions: () => apiFetch<SatelliteMission[]>("/satellite/missions"),
  searchScenes: (body: {
    mission: string;
    start_date: string;
    end_date: string;
    region?: string;
    max_cloud?: number;
    provider?: string;
  }) =>
    apiFetch<SatelliteSearchResponse>("/satellite/collections", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  buildComposite: (body: {
    year: number;
    mission: string;
    region?: string;
    season_start?: string;
    season_end?: string;
    max_cloud?: number;
    resolution?: number | null;
    max_scenes?: number;
    provider?: string;
  }) =>
    apiFetch<{ job_id: number }>("/satellite/composite", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  buildCompositeBatch: (body: {
    start_year: number;
    end_year: number;
    mission?: string;
    region?: string;
    season_start?: string;
    season_end?: string;
    max_cloud?: number;
  }) =>
    apiFetch<{ job_id: number }>("/satellite/composite/batch", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getComposites: (region?: string) =>
    apiFetch<SatelliteComposite[]>(
      `/satellite/composites${region ? `?region=${encodeURIComponent(region)}` : ""}`
    ),
  exportComposite: (
    body:
      | { composite_id: number }
      | { year: number; mission: string; region?: string; provider?: string }
  ) =>
    apiFetch<{ download_url?: string; task_id?: string; state?: string }>(
      "/satellite/export",
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),

  // GeoTIFF Workspace
  uploadGeotiffFiles: (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return apiFetch<{ type: "raster" | "vector"; asset: any }>(
      "/geotiff/upload",
      {
        method: "POST",
        body: fd,
      }
    );
  },
  getUploads: () =>
    apiFetch<{ rasters: RasterAsset[]; vectors: VectorAsset[] }>(
      "/geotiff/uploads"
    ),
  getGeotiffMetadata: (id: number) =>
    apiFetch<GeoTIFFMetadata>(`/geotiff/metadata/${id}`),
  processGeotiff: (body: {
    asset_id: number;
    operation: "reproject" | "clip" | "resample" | "index" | "statistics";
    params: Record<string, any>;
  }) =>
    apiFetch<{ asset: RasterAsset }>("/geotiff/process", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getUploadedVectorGeoJSON: (id: number) =>
    apiFetch<GeoJSONFeatureCollection>(`/vectors/uploads/${id}`),

  // Lakes
  detectLakes: (body: {
    composite_id: number;
    method: "mndwi_otsu" | "unet";
    min_area_ha?: number;
    max_slope_deg?: number;
    threshold?: number | null;
  }) =>
    apiFetch<{ job_id: number }>("/lakes/detect", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getLakeInventory: (year?: number) =>
    apiFetch<GeoJSONFeatureCollection<LakeFeatureProperties>>(
      `/lakes/inventory${year !== undefined ? `?year=${year}` : ""}`
    ),
  getLakeDetail: (id: number) => apiFetch<LakeDetailResponse>(`/lakes/${id}`),
  getLakeStatistics: () => apiFetch<LakeStatisticsResponse>("/lakes/statistics"),

  // Change detection / Glacier / Disaster
  getChangeIndicators: (region = "full_aoi") =>
    apiFetch<ChangeIndicatorsResponse>(
      `/change-detection/indicators?region=${encodeURIComponent(region)}`
    ),
  analyseChange: (body: {
    year_a: number;
    year_b: number;
    indicator: string;
    region?: string;
  }) =>
    apiFetch<ChangeAnalysisResult>("/change-detection/analyse", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getChangeResults: () =>
    apiFetch<ChangeAnalysisResult[]>("/change-detection/results"),
  getGlacierSummary: (region = "chorabari") =>
    apiFetch<GlacierSummaryResponse>(
      `/glacier/summary?region=${encodeURIComponent(region)}`
    ),
  getDisasterContext: () =>
    apiFetch<DisasterContextResponse>("/disaster/context"),
  compareDisaster: (body: {
    pre_year: number;
    post_year: number;
    region?: string;
  }) =>
    apiFetch<DisasterCompareResponse>("/disaster/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // GLOF Susceptibility
  getGlofMethodology: () =>
    apiFetch<GlofMethodologyResponse>("/glof/methodology"),
  runGlofAssessment: () =>
    apiFetch<{ job_id: number }>("/glof/assess", { method: "POST" }),
  getGlofAssessments: () => apiFetch<GlofAssessment[]>("/glof/assessments"),
  getGlofMlStatus: () => apiFetch<GlofMlStatusResponse>("/glof/ml-status"),

  // Terrain
  fetchDem: (source = "copernicus") =>
    apiFetch<{ job_id: number }>("/terrain/fetch-dem", {
      method: "POST",
      body: JSON.stringify({ source }),
    }),
  analyseTerrain: (stream_threshold_km2 = 1.0) =>
    apiFetch<{ job_id: number }>("/terrain/analyse", {
      method: "POST",
      body: JSON.stringify({ stream_threshold_km2 }),
    }),
  getTerrainSummary: () =>
    apiFetch<TerrainSummaryResponse>("/terrain/summary"),
  computeFlowpath: (body: { lake_id?: number; lon?: number; lat?: number }) =>
    apiFetch<FlowpathResponse>("/terrain/flowpath", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Flood Scenarios
  getFloodScenarios: () => apiFetch<FloodScenario[]>("/flood/scenarios"),
  createFloodScenario: (body: {
    name: string;
    source_lake_id?: number | null;
    description?: string;
    hydrograph?: { time_s: number[]; discharge_m3s: number[] } | null;
    hydrograph_source: string;
    assumptions: string[];
    downstream_length_km?: number;
    manning_n?: number;
  }) =>
    apiFetch<FloodScenario>("/flood/scenarios", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  exportFloodScenario: (id: number) =>
    apiFetch<{ download_url: string }>(`/flood/scenarios/${id}/export`, {
      method: "POST",
    }),
  uploadFloodResult: (
    scenarioId: number,
    file: File,
    variable: string,
    modelSoftware: string
  ) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("variable", variable);
    fd.append("model_software", modelSoftware);
    return apiFetch<FloodResult>(`/flood/scenarios/${scenarioId}/results`, {
      method: "POST",
      body: fd,
    });
  },

  // Exposure
  fetchOsm: () =>
    apiFetch<{ job_id: number }>("/exposure/fetch-osm", { method: "POST" }),
  getInfrastructure: (category?: string) =>
    apiFetch<GeoJSONFeatureCollection>(
      `/exposure/infrastructure${
        category ? `?category=${encodeURIComponent(category)}` : ""
      }`
    ),
  getInfrastructureSummary: () =>
    apiFetch<InfrastructureSummaryResponse>(
      "/exposure/infrastructure/summary"
    ),
  analyseExposure: (
    body:
      | { scenario_id: number }
      | {
          mode: "flowpath_corridor";
          lake_id: number;
          buffer_m?: number;
          hand_max_m?: number;
        }
  ) =>
    apiFetch<ExposureAnalysisResponse>("/exposure/analyse", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Rainfall
  getRainfall: (source?: string) =>
    apiFetch<RainfallResponse>(
      `/rainfall${source ? `?source=${encodeURIComponent(source)}` : ""}`
    ),
  fetchRainfall: (body: {
    source: "chirps" | "gpm" | "nasa_power" | string;
    start_year?: number;
    end_year?: number;
  }) =>
    apiFetch<{ job_id: number }>("/rainfall/fetch", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Model Lab
  getModelDatasets: () => apiFetch<ModelDatasetsResponse>("/models/datasets"),
  prepareTiles: (body: { composite_id: number; tile_size?: number }) =>
    apiFetch<{ job_id: number }>("/models/prepare-tiles", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  trainModel: (body: {
    model_type: "unet" | "deeplabv3plus";
    epochs?: number;
    batch_size?: number;
    learning_rate?: number;
    tile_size?: number;
  }) =>
    apiFetch<{ job_id: number; run_id: number }>("/models/train", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getModelRuns: () => apiFetch<ModelRun[]>("/models/runs"),
  evaluateModel: (body: { run_id: number; split?: string }) =>
    apiFetch<{ job_id: number }>("/models/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Reports
  generateReport: (body: { title?: string; sections: string[] }) =>
    apiFetch<{ report_id: number | string; download_url: string }>(
      "/reports/generate",
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),
  getReports: () => apiFetch<ReportItem[]>("/reports"),
};
