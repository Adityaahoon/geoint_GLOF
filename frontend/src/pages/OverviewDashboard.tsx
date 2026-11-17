import React, { useEffect, useState, useCallback } from "react";
import {
  CheckCircle2,
  Circle,
  Play,
  RefreshCw,
  Waves,
  ShieldAlert,
  Satellite,
  Mountain,
  Building2,
  Clock,
  Info,
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
import type { DashboardSummaryResponse, SatelliteComposite } from "../api/types";
import { useAppContext } from "../context/AppContext";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";
import { GeoMap, SUSCEPTIBILITY_COLORS } from "../components/GeoMap";

export const OverviewDashboard: React.FC = () => {
  const { selectedYear, setSelectedYear, refreshHealth } = useAppContext();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [composites, setComposites] = useState<SatelliteComposite[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumData, compData] = await Promise.all([
        api.getDashboardSummary(),
        api.getComposites().catch(() => []),
      ]);
      setSummary(sumData);
      setComposites(compData);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard summary");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    loadDashboard();
    refreshHealth();
  });

  const triggerJob = async (fn: () => Promise<{ job_id: number }>) => {
    setActionError(null);
    try {
      const res = await fn();
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setActionError(err?.message || "Action failed");
    }
  };

  const hasComposites =
    composites.length > 0 ||
    (summary?.coverage?.years?.some((y) =>
      y.missions?.some((m) => m.composite_id != null)
    ) ??
      false);

  const firstCompositeId =
    composites[0]?.composite_id ??
    summary?.coverage?.years
      ?.flatMap((y) => y.missions)
      .find((m) => m.composite_id != null)?.composite_id;

  const totalSusceptibilityCount = summary?.susceptibility
    ? (summary.susceptibility.Low || 0) +
      (summary.susceptibility.Moderate || 0) +
      (summary.susceptibility.High || 0) +
      (summary.susceptibility["Very High"] || 0)
    : 0;

  const waterSeries =
    summary?.indicators?.series?.water_area_ha ||
    summary?.indicators?.series?.ndvi_mean ||
    [];

  return (
    <div className="space-y-4">
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Kedarnath GLOF & Environmental Intelligence Overview (2000–2026)
          </h1>
          <p className="text-xs text-slate-400">
            Multi-sensor satellite observation, terrain hydrology, and preliminary multi-criteria GLOF screening
          </p>
        </div>
        <button
          onClick={loadDashboard}
          disabled={loading}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-ink-800 hover:bg-ink-700 border border-white/10 text-xs text-slate-200"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {actionError && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {actionError}
        </div>
      )}

      {(activeJobId !== null || jobError) && (
        <JobProgress
          job={job}
          error={jobError}
          onDismiss={() => setActiveJobId(null)}
        />
      )}

      {/* Top KPI Cards (strictly from /dashboard/summary) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Mapped Lakes Card */}
        <div className="bg-ink-900 border border-white/10 rounded-md p-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Observed Glacial Lakes</span>
            <Waves className="w-4 h-4 text-glacier-400" />
          </div>
          {summary && summary.lakes.count > 0 ? (
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono text-slate-100">
                {summary.lakes.count}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5 flex items-center justify-between">
                <span>
                  Ref Year: <strong className="text-slate-200 font-mono">{summary.lakes.reference_year ?? "—"}</strong>
                </span>
                <span className="font-mono text-glacier-300">
                  {summary.lakes.method || "observed"}
                </span>
              </div>
            </div>
          ) : (
            <div className="mt-2 text-xs text-slate-500">
              No glacial lakes mapped yet. Run lake detection on a satellite composite below.
            </div>
          )}
        </div>

        {/* Total Lake Area Card */}
        <div className="bg-ink-900 border border-white/10 rounded-md p-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Mapped Lake Surface Area</span>
            <Satellite className="w-4 h-4 text-glacier-400" />
          </div>
          {summary && summary.lakes.count > 0 ? (
            <div className="mt-2">
              <div className="text-2xl font-semibold font-mono text-glacier-300">
                {summary.lakes.total_area_ha.toFixed(2)}{" "}
                <span className="text-xs font-normal text-slate-400">ha</span>
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                Observed surface water extent ({summary.lakes.reference_year ?? "latest"})
              </div>
            </div>
          ) : (
            <div className="mt-2 text-xs text-slate-500">
              Awaiting lake detection output.
            </div>
          )}
        </div>

        {/* Susceptibility Screening Summary */}
        <div className="bg-ink-900 border border-white/10 rounded-md p-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>GLOF Screening Categories</span>
            <ShieldAlert className="w-4 h-4 text-hazard-high" />
          </div>
          {summary && totalSusceptibilityCount > 0 ? (
            <div className="mt-2 space-y-1.5">
              <div className="grid grid-cols-4 gap-1 text-center font-mono text-xs">
                {(["Low", "Moderate", "High", "Very High"] as const).map((cat) => (
                  <div
                    key={cat}
                    className="bg-ink-950 rounded py-1 border border-white/5"
                  >
                    <div
                      className="font-semibold"
                      style={{ color: SUSCEPTIBILITY_COLORS[cat] }}
                    >
                      {summary.susceptibility[cat] ?? 0}
                    </div>
                    <div className="text-[9px] text-slate-400 truncate px-0.5">
                      {cat}
                    </div>
                  </div>
                ))}
              </div>
              <div className="text-[10px] text-amber-300/90 flex items-center gap-1">
                <Info className="w-3 h-3 shrink-0" />
                <span className="truncate">
                  {summary.susceptibility.is_trained_model
                    ? `Trained Model (${summary.susceptibility.method})`
                    : "Preliminary multi-criteria index (not probability)"}
                </span>
              </div>
            </div>
          ) : (
            <div className="mt-2 text-xs text-slate-500">
              No GLOF susceptibility screening computed yet.
            </div>
          )}
        </div>

        {/* Baseline Layers Status */}
        <div className="bg-ink-900 border border-white/10 rounded-md p-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Core Baseline Datasets</span>
            <Mountain className="w-4 h-4 text-glacier-400" />
          </div>
          <div className="mt-2 grid grid-cols-2 gap-1.5 text-[11px] font-mono">
            <div className="bg-ink-950 px-2 py-1 rounded border border-white/5 flex items-center justify-between">
              <span className="text-slate-400">DEM</span>
              <span
                className={
                  summary?.coverage?.dem_available
                    ? "text-hazard-low"
                    : "text-slate-500"
                }
              >
                {summary?.coverage?.dem_available ? "Ready" : "Missing"}
              </span>
            </div>
            <div className="bg-ink-950 px-2 py-1 rounded border border-white/5 flex items-center justify-between">
              <span className="text-slate-400">Terrain</span>
              <span
                className={
                  summary?.coverage?.terrain_available
                    ? "text-hazard-low"
                    : "text-slate-500"
                }
              >
                {summary?.coverage?.terrain_available ? "Ready" : "Missing"}
              </span>
            </div>
            <div className="bg-ink-950 px-2 py-1 rounded border border-white/5 flex items-center justify-between">
              <span className="text-slate-400">OSM</span>
              <span
                className={
                  summary?.coverage?.osm_available
                    ? "text-hazard-low"
                    : "text-slate-500"
                }
              >
                {summary?.coverage?.osm_available ? "Ready" : "Missing"}
              </span>
            </div>
            <div className="bg-ink-950 px-2 py-1 rounded border border-white/5 flex items-center justify-between">
              <span className="text-slate-400">Rainfall</span>
              <span
                className={
                  summary?.rainfall_available
                    ? "text-hazard-low"
                    : "text-slate-500"
                }
              >
                {summary?.rainfall_available ? "Ready" : "Missing"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Map (left 8 cols) + Getting Started / Pipeline Checklist (right 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8">
          <GeoMap
            height="480px"
            yearFilter={selectedYear}
            onYearFilterChange={(y) => {
              if (y) setSelectedYear(y);
            }}
            defaultLayers={{
              studyArea: true,
              referencePoints: true,
              lakes: true,
              susceptibility: true,
            }}
          />
        </div>

        {/* Getting Started & Pipeline Checklist */}
        <div className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 flex flex-col justify-between space-y-3">
          <div className="space-y-2.5">
            <div className="border-b border-white/10 pb-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-glacier-300">
                Scientific Pipeline Checklist
              </h2>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Execute ingestion and analysis stages in sequence to populate empirical metrics.
              </p>
            </div>

            <div className="space-y-2 text-xs">
              {/* Step 1: Fetch DEM */}
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 flex items-center justify-between gap-2">
                <div className="flex items-start gap-2">
                  {summary?.coverage?.dem_available ? (
                    <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">
                      1. Fetch Copernicus GLO-30 DEM
                    </div>
                    <div className="text-[11px] text-slate-400">
                      30m elevation baseline for Kedarnath study area
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => triggerJob(() => api.fetchDem("copernicus"))}
                  disabled={isRunning}
                  className="shrink-0 px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] flex items-center gap-1 disabled:opacity-50"
                >
                  <Play className="w-3 h-3" />
                  <span>Fetch</span>
                </button>
              </div>

              {/* Step 2: Terrain Analysis */}
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 flex items-center justify-between gap-2">
                <div className="flex items-start gap-2">
                  {summary?.coverage?.terrain_available ? (
                    <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">
                      2. Run Terrain & Hydrology Analysis
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Slope, aspect, hillshade, flow accumulation, HAND
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => triggerJob(() => api.analyseTerrain(1.0))}
                  disabled={isRunning}
                  className="shrink-0 px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] flex items-center gap-1 disabled:opacity-50"
                >
                  <Play className="w-3 h-3" />
                  <span>Run</span>
                </button>
              </div>

              {/* Step 3: Build Composites */}
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 flex items-center justify-between gap-2">
                <div className="flex items-start gap-2">
                  {hasComposites ? (
                    <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">
                      3. Build Post-Monsoon Composite ({selectedYear})
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Cloud-masked optical composite (Sep 15 – Nov 15)
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() =>
                      triggerJob(() =>
                        api.buildComposite({
                          year: selectedYear,
                          mission: selectedYear >= 2017 ? "sentinel2" : selectedYear >= 2013 ? "landsat8" : "landsat5",
                          region: "full_aoi",
                        })
                      )
                    }
                    disabled={isRunning}
                    className="px-2 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] flex items-center gap-1 disabled:opacity-50"
                    title="Build composite for selected year"
                  >
                    <Play className="w-3 h-3" />
                    <span>{selectedYear}</span>
                  </button>
                  <button
                    onClick={() =>
                      triggerJob(() =>
                        api.buildCompositeBatch({
                          start_year: 2000,
                          end_year: 2026,
                          mission: "auto",
                          region: "full_aoi",
                        })
                      )
                    }
                    disabled={isRunning}
                    className="px-2 py-1 rounded bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 text-[11px] disabled:opacity-50"
                    title="Batch build 2000–2026 composites"
                  >
                    Batch
                  </button>
                </div>
              </div>

              {/* Step 4: Detect Lakes */}
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 flex items-center justify-between gap-2">
                <div className="flex items-start gap-2">
                  {(summary?.lakes?.count ?? 0) > 0 ? (
                    <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">
                      4. Detect Glacial Lakes (MNDWI + Otsu)
                    </div>
                    <div className="text-[11px] text-slate-400">
                      {firstCompositeId
                        ? `Uses composite #${firstCompositeId}`
                        : "Requires at least one satellite composite"}
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    if (!firstCompositeId) {
                      setActionError(
                        "Build a satellite composite first before running lake detection."
                      );
                      return;
                    }
                    triggerJob(() =>
                      api.detectLakes({
                        composite_id: Number(firstCompositeId),
                        method: "mndwi_otsu",
                        min_area_ha: 1.0,
                        max_slope_deg: 20,
                      })
                    );
                  }}
                  disabled={isRunning || !firstCompositeId}
                  className="shrink-0 px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] flex items-center gap-1 disabled:opacity-40"
                >
                  <Play className="w-3 h-3" />
                  <span>Detect</span>
                </button>
              </div>

              {/* Step 5: Fetch OSM */}
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 flex items-center justify-between gap-2">
                <div className="flex items-start gap-2">
                  {summary?.coverage?.osm_available ? (
                    <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">
                      5. Fetch OpenStreetMap Infrastructure
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Settlements, roads, bridges, temples, helipads
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => triggerJob(() => api.fetchOsm())}
                  disabled={isRunning}
                  className="shrink-0 px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] flex items-center gap-1 disabled:opacity-50"
                >
                  <Building2 className="w-3 h-3" />
                  <span>Fetch</span>
                </button>
              </div>

              {/* Step 6: Run GLOF Screening */}
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 flex items-center justify-between gap-2">
                <div className="flex items-start gap-2">
                  {totalSusceptibilityCount > 0 ? (
                    <CheckCircle2 className="w-4 h-4 text-hazard-low shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="font-medium text-slate-200">
                      6. Run Multi-Criteria GLOF Screening
                    </div>
                    <div className="text-[11px] text-slate-400">
                      Evaluates lake area, growth, dam slope & downstream exposure
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => triggerJob(() => api.runGlofAssessment())}
                  disabled={isRunning}
                  className="shrink-0 px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] flex items-center gap-1 disabled:opacity-50"
                >
                  <Play className="w-3 h-3" />
                  <span>Screen</span>
                </button>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 border-t border-white/10 pt-2">
            Scientific Integrity Note: All dashboard metrics reflect actual processed assets stored in the workspace.
          </div>
        </div>
      </div>

      {/* Data Coverage Matrix (2000–2026) */}
      <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Multi-Mission Temporal Coverage Matrix (2000–2026)
            </h2>
            <p className="text-[11px] text-slate-400">
              Click any year column to set the active reference year. Green cells indicate ingested post-monsoon composites.
            </p>
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="flex items-center gap-1 text-slate-400">
              <span className="w-2.5 h-2.5 rounded-sm bg-hazard-low/60 border border-hazard-low" />
              Composite Ready
            </span>
            <span className="flex items-center gap-1 text-slate-400">
              <span className="w-2.5 h-2.5 rounded-sm bg-ink-950 border border-white/10" />
              Not Built
            </span>
          </div>
        </div>

        {summary?.coverage?.years && summary.coverage.years.length > 0 ? (
          <div className="overflow-x-auto">
            <div className="inline-grid grid-flow-col auto-cols-[minmax(36px,1fr)] gap-1 min-w-full pb-1">
              {summary.coverage.years.map((cy) => {
                const readyMissions =
                  cy.missions?.filter((m) => m.composite_id != null || m.status === "available" || m.status === "ready") || [];
                const isSelected = cy.year === selectedYear;
                return (
                  <button
                    key={cy.year}
                    onClick={() => setSelectedYear(cy.year)}
                    className={`flex flex-col items-center p-1.5 rounded border text-center transition-colors ${
                      isSelected
                        ? "bg-glacier-400/15 border-glacier-400"
                        : "bg-ink-950 border-white/5 hover:border-white/20"
                    }`}
                    title={
                      readyMissions.length > 0
                        ? `${cy.year}: ${readyMissions
                            .map(
                              (m) =>
                                `${m.mission} (${m.scene_count} scenes, valid: ${
                                  m.valid_fraction != null
                                    ? `${Math.round(m.valid_fraction * 100)}%`
                                    : "N/A"
                                })`
                            )
                            .join(", ")}`
                        : `${cy.year}: No composite built yet`
                    }
                  >
                    <span className="font-mono text-[10px] text-slate-300">
                      {String(cy.year).slice(-2)}
                    </span>
                    <div
                      className={`w-full h-3 mt-1 rounded-sm ${
                        readyMissions.length > 0
                          ? "bg-hazard-low/70 border border-hazard-low"
                          : "bg-ink-900 border border-white/5"
                      }`}
                    />
                    <span className="font-mono text-[9px] text-slate-500 mt-0.5">
                      {readyMissions.length > 0 ? readyMissions[0].mission.slice(0, 3).toUpperCase() : "—"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500 py-4 text-center bg-ink-950 rounded border border-white/5">
            No temporal coverage records available yet. Build satellite composites to populate the 2000–2026 matrix.
          </div>
        )}
      </div>

      {/* Bottom Row: Indicator Trend + Recent Jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7 bg-ink-900 border border-white/10 rounded-md p-3.5">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
              Observed Surface Indicator Trajectory
            </h2>
            <span className="text-[11px] text-slate-400 font-mono">
              Source: /dashboard/summary
            </span>
          </div>
          {waterSeries.length > 0 ? (
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={waterSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                  <XAxis
                    dataKey="year"
                    stroke="#64748b"
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0b1220",
                      borderColor: "rgba(255,255,255,0.15)",
                      fontSize: 12,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="Observed Value"
                    stroke="#5ec8e5"
                    strokeWidth={2}
                    dot={{ r: 3, fill: "#5ec8e5" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-xs text-slate-500 bg-ink-950 rounded border border-white/5 p-4 text-center">
              No multi-year indicator time series computed yet. Build composites across multiple years to plot empirical surface trends.
            </div>
          )}
        </div>

        {/* Recent Processing Jobs */}
        <div className="lg:col-span-5 bg-ink-900 border border-white/10 rounded-md p-3.5">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-glacier-400" />
              <span>Recent Processing Jobs</span>
            </h2>
          </div>

          {summary?.recent_jobs && summary.recent_jobs.length > 0 ? (
            <div className="divide-y divide-white/5 max-h-52 overflow-y-auto text-xs">
              {summary.recent_jobs.map((jb) => (
                <div
                  key={jb.id}
                  className="py-2 flex items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <div className="font-mono text-slate-200 truncate">
                      #{jb.id} • {jb.job_type}
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {jb.created_at}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase ${
                        jb.status === "completed"
                          ? "bg-hazard-low/15 text-hazard-low"
                          : jb.status === "failed"
                          ? "bg-hazard-veryhigh/15 text-hazard-veryhigh"
                          : "bg-glacier-400/15 text-glacier-300"
                      }`}
                    >
                      {jb.status}
                    </span>
                    {(jb.status === "running" || jb.status === "queued") && (
                      <button
                        onClick={() => setActiveJobId(jb.id)}
                        className="text-[10px] text-glacier-400 hover:underline"
                      >
                        Track
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-52 flex items-center justify-center text-xs text-slate-500 bg-ink-950 rounded border border-white/5">
              No processing jobs have been executed yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
