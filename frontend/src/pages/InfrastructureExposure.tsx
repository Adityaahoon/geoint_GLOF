import React, { useEffect, useState, useCallback } from "react";
import {
  Building2,
  Play,
  AlertTriangle,
  Download,
  RefreshCw,
} from "lucide-react";
import { api } from "../api/client";
import type {
  ExposureAnalysisResponse,
  FloodScenario,
  InfrastructureSummaryResponse,
  LakeFeatureProperties,
} from "../api/types";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";
import { GeoMap, CustomVectorOverlay } from "../components/GeoMap";

const OSM_CATEGORIES = [
  "all",
  "settlement",
  "building",
  "road",
  "bridge",
  "hospital",
  "school",
  "public",
  "helipad",
  "power",
];

export const InfrastructureExposure: React.FC = () => {
  const [summary, setSummary] =
    useState<InfrastructureSummaryResponse | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [scenarios, setScenarios] = useState<FloodScenario[]>([]);
  const [lakes, setLakes] = useState<LakeFeatureProperties[]>([]);

  // Analysis Mode State
  const [mode, setMode] = useState<"flowpath_corridor" | "scenario">(
    "flowpath_corridor"
  );
  const [lakeId, setLakeId] = useState<number | "">("");
  const [bufferM, setBufferM] = useState<number>(250);
  const [handMaxM, setHandMaxM] = useState<number>(20);
  const [scenarioId, setScenarioId] = useState<number | "">("");

  const [exposureRes, setExposureRes] =
    useState<ExposureAnalysisResponse | null>(null);
  const [analysing, setAnalysing] = useState<boolean>(false);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [sumData, scList, lakeInv] = await Promise.all([
        api.getInfrastructureSummary().catch(() => null),
        api.getFloodScenarios().catch(() => []),
        api.getLakeInventory().catch(() => null),
      ]);
      setSummary(sumData);
      setScenarios(scList);
      if (scList.length > 0 && scenarioId === "") {
        setScenarioId(scList[0].id);
      }
      const props = (lakeInv?.features || []).map((f) => f.properties);
      setLakes(props);
      if (props.length > 0 && lakeId === "") {
        setLakeId(props[0].lake_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load infrastructure exposure data");
    }
  }, [scenarioId, lakeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    loadData();
  });

  const handleFetchOsm = async () => {
    setError(null);
    try {
      const res = await api.fetchOsm();
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start OpenStreetMap fetch job");
    }
  };

  const handleRunExposure = async (e: React.FormEvent) => {
    e.preventDefault();
    setAnalysing(true);
    setError(null);
    try {
      if (mode === "scenario") {
        if (scenarioId === "") {
          setError("Please select a flood scenario with imported results.");
          setAnalysing(false);
          return;
        }
        const res = await api.analyseExposure({
          scenario_id: Number(scenarioId),
        });
        setExposureRes(res);
      } else {
        if (lakeId === "") {
          setError("Please select a source glacial lake first.");
          setAnalysing(false);
          return;
        }
        const res = await api.analyseExposure({
          mode: "flowpath_corridor",
          lake_id: Number(lakeId),
          buffer_m: bufferM,
          hand_max_m: handMaxM,
        });
        setExposureRes(res);
      }
    } catch (err: any) {
      setError(err?.message || "Exposure screening failed");
    } finally {
      setAnalysing(false);
    }
  };

  const customVectors: CustomVectorOverlay[] = React.useMemo(() => {
    if (!exposureRes?.features) return [];
    return [
      {
        id: "potential-exposure-features",
        label: `Potential Exposure Features (${
          exposureRes.features.features?.length ?? 0
        })`,
        data: exposureRes.features,
        color: "#ef4444",
        fillOpacity: 0.4,
        weight: 2.5,
      },
    ];
  }, [exposureRes]);

  const totalOsmFeatures = summary?.counts
    ? Object.values(summary.counts).reduce((a, b) => a + b, 0)
    : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold text-slate-100">
              Downstream Infrastructure & Settlement Exposure Screening
            </h1>
            <span className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 font-mono text-[10px] font-semibold uppercase">
              POTENTIAL EXPOSURE, NOT CONFIRMED DAMAGE
            </span>
          </div>
          <p className="text-xs text-slate-400">
            OpenStreetMap baseline inventory intersected with hypothetical flood extents or topographic HAND flowpath corridors
          </p>
        </div>
        <button
          onClick={handleFetchOsm}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 text-xs font-medium disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? "animate-spin" : ""}`} />
          <span>Fetch / Update OSM Infrastructure</span>
        </button>
      </div>

      {/* Mandatory Scientific Disclaimer */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-md p-2.5 flex items-center gap-2 text-xs text-amber-200">
        <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0" />
        <span>
          <strong>Methodological Note:</strong> All outputs on this page represent{" "}
          <span className="underline font-semibold">
            potential exposure, not confirmed damage
          </span>
          . OpenStreetMap completeness varies across high-mountain valleys.
        </span>
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {(activeJobId !== null || jobError) && (
        <JobProgress
          job={job}
          error={jobError}
          onDismiss={() => setActiveJobId(null)}
        />
      )}

      {/* OSM Baseline Category Counts */}
      <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5 text-glacier-400" />
            <span>
              OpenStreetMap Baseline Inventory ({totalOsmFeatures} features •{" "}
              {summary?.road_length_km?.toFixed(1) ?? "0.0"} km roads)
            </span>
          </div>
          {summary?.retrieved_at && (
            <span className="font-mono text-[10px] text-slate-400">
              Retrieved: {summary.retrieved_at} ({summary.source || "Overpass API"})
            </span>
          )}
        </div>

        {summary && totalOsmFeatures > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-1.5 font-mono">
            {OSM_CATEGORIES.map((cat) => {
              const count =
                cat === "all"
                  ? totalOsmFeatures
                  : summary.counts?.[cat] ?? 0;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`p-2 rounded border text-left transition-colors ${
                    selectedCategory === cat
                      ? "bg-glacier-400/15 border-glacier-400 text-glacier-300"
                      : "bg-ink-950 border-white/5 text-slate-300 hover:border-white/20"
                  }`}
                >
                  <div className="text-[10px] uppercase text-slate-400 truncate">
                    {cat}
                  </div>
                  <div className="text-sm font-semibold mt-0.5">{count}</div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="text-slate-500 py-4 text-center bg-ink-950 rounded border border-white/5">
            No OpenStreetMap infrastructure loaded yet. Click "Fetch / Update OSM Infrastructure" above.
          </div>
        )}
      </div>

      {/* Main Grid: Exposure Analysis Config & Results (5 cols) + Map (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5 space-y-4 text-xs">
          <form
            onSubmit={handleRunExposure}
            className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3"
          >
            <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
              Run Potential Exposure Screening
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                Screening Mode
              </label>
              <select
                value={mode}
                onChange={(e) =>
                  setMode(e.target.value as "flowpath_corridor" | "scenario")
                }
                className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
              >
                <option value="flowpath_corridor">
                  Topographic Flow-Path + HAND Corridor Screening
                </option>
                <option value="scenario">
                  Imported Hydraulic Scenario Extent Overlay
                </option>
              </select>
            </div>

            {mode === "flowpath_corridor" ? (
              <>
                <div>
                  <label className="block text-slate-400 mb-1">
                    Source Glacial Lake
                  </label>
                  <select
                    value={lakeId}
                    onChange={(e) =>
                      setLakeId(e.target.value ? Number(e.target.value) : "")
                    }
                    className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value="">Select mapped lake...</option>
                    {lakes.map((l) => (
                      <option key={l.lake_id} value={l.lake_id}>
                        {l.name} ({l.lake_code} • {l.area_ha?.toFixed(2)} ha)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-slate-400 mb-1">
                      Lateral Buffer (m)
                    </label>
                    <input
                      type="number"
                      min={50}
                      max={2000}
                      step={50}
                      value={bufferM}
                      onChange={(e) => setBufferM(Number(e.target.value))}
                      className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">
                      Max HAND Elevation (m)
                    </label>
                    <input
                      type="number"
                      min={5}
                      max={100}
                      step={5}
                      value={handMaxM}
                      onChange={(e) => setHandMaxM(Number(e.target.value))}
                      className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                    />
                  </div>
                </div>
              </>
            ) : (
              <div>
                <label className="block text-slate-400 mb-1">
                  Hypothetical Flood Scenario
                </label>
                <select
                  value={scenarioId}
                  onChange={(e) =>
                    setScenarioId(e.target.value ? Number(e.target.value) : "")
                  }
                  className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
                >
                  <option value="">Select flood scenario...</option>
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      #{s.id} • {s.name} ({s.status})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              type="submit"
              disabled={analysing}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>
                {analysing
                  ? "Screening Potential Exposure..."
                  : "Compute Potential Exposure"}
              </span>
            </button>
          </form>

          {/* Exposure Results Panel */}
          {exposureRes && (
            <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="font-semibold uppercase tracking-wider text-amber-300">
                  Potential Exposure Summary (Not Confirmed Damage)
                </span>
                <button
                  onClick={() => {
                    const blob = new Blob(
                      [JSON.stringify(exposureRes.features, null, 2)],
                      { type: "application/geo+json" }
                    );
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "potential_exposure.geojson";
                    a.click();
                  }}
                  className="text-glacier-400 hover:text-glacier-300 flex items-center gap-1 text-[11px]"
                >
                  <Download className="w-3 h-3" />
                  <span>GeoJSON</span>
                </button>
              </div>

              <div className="grid grid-cols-3 gap-2 font-mono">
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">
                    Potentially Exposed Buildings
                  </div>
                  <div className="text-sm font-semibold text-hazard-high mt-0.5">
                    {exposureRes.statistics.buildings ?? 0}
                  </div>
                </div>
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">
                    Road Segments (km)
                  </div>
                  <div className="text-sm font-semibold text-amber-300 mt-0.5">
                    {exposureRes.statistics.road_length_km?.toFixed(2) ?? "0.00"}
                  </div>
                </div>
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Bridges</div>
                  <div className="text-sm font-semibold text-hazard-veryhigh mt-0.5">
                    {exposureRes.statistics.bridges ?? 0}
                  </div>
                </div>
              </div>

              {exposureRes.statistics.settlements &&
                exposureRes.statistics.settlements.length > 0 && (
                  <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                    <div className="text-[10px] uppercase text-slate-400 mb-1">
                      Potentially Exposed Settlements:
                    </div>
                    <div className="text-slate-200 font-medium">
                      {exposureRes.statistics.settlements.join(", ")}
                    </div>
                  </div>
                )}

              <div className="text-[11px] text-amber-200/90 bg-amber-500/10 border border-amber-500/20 rounded p-2">
                {exposureRes.caveat}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-7">
          <GeoMap
            height="500px"
            customVectors={customVectors}
            defaultLayers={{
              studyArea: true,
              infrastructure: true,
              lakes: true,
              rivers: true,
              referencePoints: true,
            }}
          />
        </div>
      </div>
    </div>
  );
};
