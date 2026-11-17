import React, { useEffect, useState, useCallback } from "react";
import {
  Waves,
  Play,
  Download,
  Info,
  TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import type {
  GeoJSONFeatureCollection,
  LakeDetailResponse,
  LakeFeatureProperties,
  LakeStatisticsResponse,
  ModelRun,
  RasterOverlayResponse,
  SatelliteComposite,
} from "../api/types";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";
import { GeoMap, CustomRasterOverlay } from "../components/GeoMap";

export const GlacialLakeDetection: React.FC = () => {
  const [composites, setComposites] = useState<SatelliteComposite[]>([]);
  const [selectedCompositeId, setSelectedCompositeId] = useState<number | null>(
    null
  );
  const [method, setMethod] = useState<"mndwi_otsu" | "unet">("mndwi_otsu");
  const [minAreaHa, setMinAreaHa] = useState<number>(1.0);
  const [maxSlopeDeg, setMaxSlopeDeg] = useState<number>(20);
  const [manualThreshold, setManualThreshold] = useState<string>("");

  const [completedRuns, setCompletedRuns] = useState<ModelRun[]>([]);
  const [inventory, setInventory] =
    useState<GeoJSONFeatureCollection<LakeFeatureProperties> | null>(null);
  const [stats, setStats] = useState<LakeStatisticsResponse | null>(null);
  const [selectedLakeId, setSelectedLakeId] = useState<number | null>(null);
  const [lakeDetail, setLakeDetail] = useState<LakeDetailResponse | null>(null);
  const [compositeOverlay, setCompositeOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [filterYear, setFilterYear] = useState<number | null>(null);

  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [compList, invData, statData, runsData] = await Promise.all([
        api.getComposites().catch(() => []),
        api.getLakeInventory(filterYear ?? undefined).catch(() => null),
        api.getLakeStatistics().catch(() => null),
        api.getModelRuns().catch(() => []),
      ]);
      setComposites(compList);
      if (compList.length > 0 && selectedCompositeId === null) {
        setSelectedCompositeId(compList[0].composite_id);
      }
      setInventory(invData);
      setStats(statData);
      setCompletedRuns(
        runsData.filter((r) => r.status === "completed")
      );
      if (
        invData?.features?.length &&
        selectedLakeId === null &&
        invData.features[0].properties?.lake_id !== undefined
      ) {
        setSelectedLakeId(invData.features[0].properties.lake_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load lake detection data");
    }
  }, [filterYear, selectedCompositeId, selectedLakeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Load composite raster overlay when selectedCompositeId changes
  useEffect(() => {
    const comp = composites.find((c) => c.composite_id === selectedCompositeId);
    if (!comp?.raster?.id) {
      setCompositeOverlay(null);
      return;
    }
    api
      .getRasterOverlay(comp.raster.id)
      .then(setCompositeOverlay)
      .catch(() => setCompositeOverlay(null));
  }, [selectedCompositeId, composites]);

  // Load individual lake detail when selectedLakeId changes
  useEffect(() => {
    if (selectedLakeId === null) {
      setLakeDetail(null);
      return;
    }
    api
      .getLakeDetail(selectedLakeId)
      .then(setLakeDetail)
      .catch(() => setLakeDetail(null));
  }, [selectedLakeId]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    loadData();
  });

  const handleRunDetection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompositeId) {
      setError("Please select a satellite composite first.");
      return;
    }
    setError(null);
    try {
      const res = await api.detectLakes({
        composite_id: selectedCompositeId,
        method,
        min_area_ha: minAreaHa,
        max_slope_deg: maxSlopeDeg,
        threshold: manualThreshold.trim() !== "" ? Number(manualThreshold) : null,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start lake detection");
    }
  };

  const handleExportGeoJSON = () => {
    if (!inventory) return;
    const blob = new Blob([JSON.stringify(inventory, null, 2)], {
      type: "application/geo+json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `glacioguard_lakes_${filterYear ?? "all"}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    const comp = composites.find((c) => c.composite_id === selectedCompositeId);
    if (!comp || !compositeOverlay) return [];
    return [
      {
        id: `comp-${comp.composite_id}`,
        label: `Composite ${comp.year} (${comp.mission})`,
        overlay: compositeOverlay,
        rasterId: comp.raster?.id,
      },
    ];
  }, [selectedCompositeId, compositeOverlay, composites]);

  const unetAvailable = completedRuns.length > 0;
  const features = inventory?.features || [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Glacial Lake Detection & Multi-Year Inventory
          </h1>
          <p className="text-xs text-slate-400">
            Automated water body delineation using spectral MNDWI + adaptive Otsu thresholding and terrain slope masking
          </p>
        </div>
        {features.length > 0 && (
          <button
            onClick={handleExportGeoJSON}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Inventory GeoJSON ({features.length})</span>
          </button>
        )}
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

      {/* Top Row: Detection Config (4 cols) + Map (8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
            Detection Parameters
          </div>

          <form onSubmit={handleRunDetection} className="space-y-3">
            <div>
              <label className="block text-slate-400 mb-1">
                Input Satellite Composite
              </label>
              {composites.length > 0 ? (
                <select
                  value={selectedCompositeId ?? ""}
                  onChange={(e) => setSelectedCompositeId(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200 font-mono"
                >
                  {composites.map((c) => (
                    <option key={c.composite_id} value={c.composite_id}>
                      #{c.composite_id} • {c.year} ({c.mission} • {c.resolution_m}m)
                    </option>
                  ))}
                </select>
              ) : (
                <div className="bg-ink-950 border border-amber-500/30 text-amber-300 rounded p-2 text-[11px]">
                  No composites available yet. Build a composite in Satellite Explorer or Overview Dashboard first.
                </div>
              )}
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                Segmentation Method
              </label>
              <select
                value={method}
                onChange={(e) =>
                  setMethod(e.target.value as "mndwi_otsu" | "unet")
                }
                className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
              >
                <option value="mndwi_otsu">
                  Spectral MNDWI + Otsu Threshold + Terrain Mask (Active)
                </option>
                <option value="unet" disabled={!unetAvailable}>
                  U-Net Deep Learning Segmentation{" "}
                  {unetAvailable
                    ? "(Trained Checkpoint Ready)"
                    : "(Disabled — awaiting trained model in Model Lab)"}
                </option>
              </select>
              {!unetAvailable && (
                <div className="mt-1 flex items-center gap-1 text-[10px] text-slate-500">
                  <Info className="w-3 h-3 text-glacier-400 shrink-0" />
                  <span>
                    U-Net inference is disabled until verified masks are trained in Model Lab.
                  </span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">
                  Min Lake Area (ha)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.05"
                  value={minAreaHa}
                  onChange={(e) => setMinAreaHa(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Max Slope Mask (°)
                </label>
                <input
                  type="number"
                  step="1"
                  min="5"
                  max="45"
                  value={maxSlopeDeg}
                  onChange={(e) => setMaxSlopeDeg(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                Manual MNDWI Threshold (leave blank for adaptive Otsu)
              </label>
              <input
                type="number"
                step="0.02"
                min="-0.5"
                max="0.8"
                value={manualThreshold}
                onChange={(e) => setManualThreshold(e.target.value)}
                placeholder="Auto (Otsu)"
                className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 font-mono text-slate-200 placeholder-slate-600"
              />
            </div>

            <button
              type="submit"
              disabled={isRunning || !selectedCompositeId}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-40"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Run Glacial Lake Delineation</span>
            </button>
          </form>

          {/* Annual Lake Statistics Summary */}
          {stats?.annual && stats.annual.length > 0 && (
            <div className="pt-2 border-t border-white/10 space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-300">
                Annual Observed Totals
              </div>
              <div className="max-h-36 overflow-y-auto divide-y divide-white/5 font-mono text-[11px]">
                {stats.annual.map((a, i) => (
                  <div
                    key={i}
                    className="py-1 flex items-center justify-between text-slate-300"
                  >
                    <span>
                      {a.year} ({a.mission})
                    </span>
                    <span className="text-glacier-300">
                      {a.lake_count} lakes • {a.total_area_ha.toFixed(2)} ha
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Map */}
        <div className="lg:col-span-8">
          <GeoMap
            height="470px"
            customRasters={customRasters}
            selectedLakeId={selectedLakeId}
            onLakeSelect={(id) => setSelectedLakeId(id)}
            yearFilter={filterYear}
            onYearFilterChange={setFilterYear}
            defaultLayers={{
              studyArea: true,
              lakes: true,
              referencePoints: true,
            }}
          />
        </div>
      </div>

      {/* Bottom Row: Mapped Lakes Table (7 cols) + Lake Detail & Area Time Series (5 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <Waves className="w-3.5 h-3.5 text-glacier-400" />
              <span>Observed Glacial Lake Inventory ({features.length})</span>
            </h2>
          </div>

          {features.length > 0 ? (
            <div className="overflow-x-auto max-h-80">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1.5 px-2">Code / Name</th>
                    <th className="py-1.5 px-2">Area (ha)</th>
                    <th className="py-1.5 px-2">Elev (m)</th>
                    <th className="py-1.5 px-2">Year</th>
                    <th className="py-1.5 px-2">Mission</th>
                    <th className="py-1.5 px-2">Method</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                  {features.map((f, idx) => {
                    const p = f.properties;
                    const isSel = p.lake_id === selectedLakeId;
                    return (
                      <tr
                        key={`${p.lake_id}-${idx}`}
                        onClick={() => setSelectedLakeId(p.lake_id)}
                        className={`cursor-pointer hover:bg-white/5 ${
                          isSel ? "bg-glacier-400/15" : ""
                        }`}
                      >
                        <td className="py-1.5 px-2 font-sans font-medium text-slate-200">
                          <div>{p.name || "Unnamed Lake"}</div>
                          <div className="text-[10px] font-mono text-slate-500">
                            {p.lake_code || `ID #${p.lake_id}`}
                          </div>
                        </td>
                        <td className="py-1.5 px-2 text-glacier-300 font-semibold">
                          {p.area_ha != null ? p.area_ha.toFixed(2) : "—"}
                        </td>
                        <td className="py-1.5 px-2 text-slate-300">
                          {p.elevation_m != null ? Math.round(p.elevation_m) : "—"}
                        </td>
                        <td className="py-1.5 px-2 text-slate-300">{p.year ?? "—"}</td>
                        <td className="py-1.5 px-2 text-slate-400">{p.mission ?? "—"}</td>
                        <td className="py-1.5 px-2 text-slate-400">{p.method ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 py-10 text-center bg-ink-950 rounded border border-white/5">
              No glacial lakes detected yet. Choose a satellite composite above and run lake delineation.
            </div>
          )}
        </div>

        {/* Lake Detail & Area Time Series Panel */}
        <div className="lg:col-span-5 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <h2 className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-glacier-400" />
              <span>Lake Multi-Year Observation Detail</span>
            </h2>
          </div>

          {lakeDetail ? (
            <div className="space-y-3">
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 grid grid-cols-2 gap-2">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Lake Name / Code</div>
                  <div className="font-semibold text-slate-200">
                    {lakeDetail.lake.name} ({lakeDetail.lake.lake_code})
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Latest Observed Area</div>
                  <div className="font-mono text-glacier-300 font-semibold">
                    {lakeDetail.lake.area_ha?.toFixed(2)} ha
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Elevation</div>
                  <div className="font-mono text-slate-300">
                    {lakeDetail.lake.elevation_m
                      ? `${Math.round(lakeDetail.lake.elevation_m)} m a.s.l.`
                      : "N/A"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Observations</div>
                  <div className="font-mono text-slate-300">
                    {lakeDetail.observations?.length ?? 0} epochs
                  </div>
                </div>
              </div>

              {lakeDetail.observations && lakeDetail.observations.length > 0 ? (
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={lakeDetail.observations}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                      <XAxis dataKey="year" stroke="#64748b" tick={{ fontSize: 11 }} />
                      <YAxis
                        stroke="#64748b"
                        tick={{ fontSize: 11 }}
                        unit=" ha"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#0b1220",
                          borderColor: "rgba(255,255,255,0.15)",
                          fontSize: 12,
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="area_ha"
                        name="Surface Area (ha)"
                        stroke="#5ec8e5"
                        strokeWidth={2}
                        dot={{ r: 3.5, fill: "#5ec8e5" }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-slate-500 py-6 text-center bg-ink-950 rounded">
                  Single-epoch observation. Run detection on additional yearly composites to build a multi-year trajectory.
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500 py-10 text-center bg-ink-950 rounded border border-white/5">
              Select a glacial lake from the table or map to inspect its multi-temporal surface area series.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
