import React, { useEffect, useState, useCallback } from "react";
import {
  TrendingUp,
  AlertTriangle,
  Play,
  Layers,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea,
} from "recharts";
import { api } from "../api/client";
import type {
  ChangeAnalysisResult,
  ChangeIndicatorsResponse,
  IndicatorPoint,
  RasterOverlayResponse,
} from "../api/types";
import { useAppContext } from "../context/AppContext";
import { GeoMap, CustomRasterOverlay } from "../components/GeoMap";
import { SwipeCompare } from "../components/SwipeCompare";

const MISSION_COLORS: Record<string, string> = {
  landsat5: "#38bdf8",
  landsat7: "#facc15",
  landsat8: "#4ade80",
  landsat9: "#2dd4bf",
  sentinel2: "#c084fc",
  modis: "#fb923c",
};

const DEFAULT_COMPARISONS: [number, number][] = [
  [2000, 2012],
  [2012, 2013],
  [2013, 2015],
  [2015, 2020],
  [2020, 2024],
  [2024, 2026],
];

export const HistoricalChangeAnalysis: React.FC = () => {
  const { studyArea } = useAppContext();

  const [region, setRegion] = useState<string>("full_aoi");
  const [indicatorsData, setIndicatorsData] =
    useState<ChangeIndicatorsResponse | null>(null);
  const [yearA, setYearA] = useState<number>(2012);
  const [yearB, setYearB] = useState<number>(2013);
  const [indicator, setIndicator] = useState<string>("water");

  const [analysisResult, setAnalysisResult] =
    useState<ChangeAnalysisResult | null>(null);
  const [pastResults, setPastResults] = useState<ChangeAnalysisResult[]>([]);
  const [analysing, setAnalysing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Overlays for current analysisResult
  const [beforeOverlay, setBeforeOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [afterOverlay, setAfterOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [diffOverlay, setDiffOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [transOverlay, setTransOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [viewMode, setViewMode] = useState<"map" | "swipe">("map");

  const loadIndicatorsAndResults = useCallback(async () => {
    try {
      const [indRes, prevRes] = await Promise.all([
        api.getChangeIndicators(region).catch(() => null),
        api.getChangeResults().catch(() => []),
      ]);
      setIndicatorsData(indRes);
      setPastResults(prevRes);
      if (prevRes.length > 0 && !analysisResult) {
        setAnalysisResult(prevRes[0]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load change detection indicators");
    }
  }, [region, analysisResult]);

  useEffect(() => {
    loadIndicatorsAndResults();
  }, [loadIndicatorsAndResults]);

  // Fetch raster overlays when analysisResult changes
  useEffect(() => {
    if (!analysisResult?.rasters) {
      setBeforeOverlay(null);
      setAfterOverlay(null);
      setDiffOverlay(null);
      setTransOverlay(null);
      return;
    }
    const { before, after, difference, transition } = analysisResult.rasters;
    if (before?.id) {
      api.getRasterOverlay(before.id).then(setBeforeOverlay).catch(() => {});
    } else setBeforeOverlay(null);
    if (after?.id) {
      api.getRasterOverlay(after.id).then(setAfterOverlay).catch(() => {});
    } else setAfterOverlay(null);
    if (difference?.id) {
      api
        .getRasterOverlay(difference.id, { cmap: "RdBu_r" })
        .then(setDiffOverlay)
        .catch(() => {});
    } else setDiffOverlay(null);
    if (transition?.id) {
      api
        .getRasterOverlay(transition.id, { categorical: indicator })
        .then(setTransOverlay)
        .catch(() => {});
    } else setTransOverlay(null);
  }, [analysisResult, indicator]);

  const runPairComparison = async (a: number, b: number, ind = indicator) => {
    setYearA(a);
    setYearB(b);
    setAnalysing(true);
    setError(null);
    try {
      const res = await api.analyseChange({
        year_a: a,
        year_b: b,
        indicator: ind,
        region,
      });
      setAnalysisResult(res);
      api.getChangeResults().then(setPastResults).catch(() => {});
    } catch (err: any) {
      setError(err?.message || "Change analysis failed");
    } finally {
      setAnalysing(false);
    }
  };

  const comparisons =
    studyArea?.standard_comparisons?.length
      ? studyArea.standard_comparisons
      : DEFAULT_COMPARISONS;

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    const list: CustomRasterOverlay[] = [];
    if (diffOverlay && analysisResult?.rasters?.difference) {
      list.push({
        id: "change-diff",
        label: `Difference (${analysisResult.year_a}→${analysisResult.year_b})`,
        overlay: diffOverlay,
        rasterId: analysisResult.rasters.difference.id,
      });
    }
    if (transOverlay && analysisResult?.rasters?.transition) {
      list.push({
        id: "change-trans",
        label: `Transition Class (${analysisResult.indicator})`,
        overlay: transOverlay,
        rasterId: analysisResult.rasters.transition.id,
      });
    }
    if (afterOverlay && analysisResult?.rasters?.after) {
      list.push({
        id: "change-after",
        label: `After (${analysisResult.year_b})`,
        overlay: afterOverlay,
        rasterId: analysisResult.rasters.after.id,
      });
    }
    if (beforeOverlay && analysisResult?.rasters?.before) {
      list.push({
        id: "change-before",
        label: `Before (${analysisResult.year_a})`,
        overlay: beforeOverlay,
        rasterId: analysisResult.rasters.before.id,
      });
    }
    return list;
  }, [analysisResult, beforeOverlay, afterOverlay, diffOverlay, transOverlay]);

  const renderIndicatorChart = (
    key: string,
    title: string,
    defaultColor: string
  ) => {
    const entry = indicatorsData?.indicators?.[key];
    const series = entry?.series || [];

    return (
      <div
        key={key}
        className="bg-ink-900 border border-white/10 rounded-md p-3 space-y-1.5"
      >
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200">{title}</span>
          <span className="font-mono text-[10px] text-slate-400">
            {entry?.unit || ""}
          </span>
        </div>
        {series.length > 0 ? (
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                <ReferenceArea
                  x1={2000}
                  x2={2012}
                  fill="#38bdf8"
                  fillOpacity={0.04}
                />
                <ReferenceArea
                  x1={2012}
                  x2={2014}
                  fill="#ef4444"
                  fillOpacity={0.08}
                />
                <ReferenceArea
                  x1={2014}
                  x2={2019}
                  fill="#facc15"
                  fillOpacity={0.04}
                />
                <ReferenceArea
                  x1={2019}
                  x2={2026}
                  fill="#4ade80"
                  fillOpacity={0.04}
                />
                <XAxis dataKey="year" stroke="#64748b" tick={{ fontSize: 10 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const pt = payload[0].payload as IndicatorPoint;
                    return (
                      <div className="bg-ink-950 border border-white/15 rounded p-2 text-[11px] shadow-xl space-y-0.5">
                        <div className="font-semibold text-slate-100">
                          Year: {pt.year} {pt.year === 2026 ? "(Year-to-Date)" : ""}
                        </div>
                        <div className="font-mono text-glacier-300">
                          Value: {pt.value != null ? pt.value.toFixed(3) : "N/A"}{" "}
                          {entry?.unit || ""}
                        </div>
                        <div className="text-slate-400">
                          Mission: <span className="font-mono">{pt.mission}</span>
                        </div>
                        {pt.valid_fraction != null && (
                          <div className="text-slate-400">
                            Valid Coverage:{" "}
                            <span className="font-mono">
                              {(pt.valid_fraction * 100).toFixed(1)}%
                            </span>
                          </div>
                        )}
                        {pt.quality_flags && pt.quality_flags.length > 0 && (
                          <div className="text-amber-300 font-mono text-[10px]">
                            Flags: {pt.quality_flags.join(", ")}
                          </div>
                        )}
                      </div>
                    );
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={defaultColor}
                  strokeWidth={2}
                  dot={(props: any) => {
                    const { cx, cy, payload } = props;
                    if (cx == null || cy == null) return <g />;
                    const col =
                      MISSION_COLORS[payload?.mission] || defaultColor;
                    return (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={3.5}
                        fill={col}
                        stroke="#070b14"
                        strokeWidth={1}
                      />
                    );
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-40 flex items-center justify-center text-[11px] text-slate-500 bg-ink-950 rounded border border-white/5 px-3 text-center">
            No observed data points for {title} yet. Build yearly composites to populate indicator trajectories.
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Historical Change Analysis (2000–2026 YTD)
          </h1>
          <p className="text-xs text-slate-400">
            Multi-decadal surface water, snow/ice, vegetation (NDVI), and exposed sediment trajectories across 4 distinct epochs
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Region:</span>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="bg-ink-900 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
          >
            <option value="full_aoi">Full Study Area (AOI)</option>
            {studyArea?.regions &&
              Object.entries(studyArea.regions).map(([k, r]) => (
                <option key={k} value={k}>
                  {r.name}
                </option>
              ))}
          </select>
        </div>
      </div>

      {/* 4 Timeline Periods Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
        <div className="bg-sky-500/10 border border-sky-500/30 rounded p-2.5">
          <div className="font-mono text-[10px] text-sky-300 uppercase">
            2000–2012 • Period I
          </div>
          <div className="font-semibold text-slate-100 mt-0.5">
            Pre-Disaster Baseline
          </div>
          <div className="text-[11px] text-slate-400">
            Landsat 5 TM & Landsat 7 ETM+ (SLC-off post-May 2003)
          </div>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded p-2.5">
          <div className="font-mono text-[10px] text-red-300 uppercase">
            June 2013 • Period II
          </div>
          <div className="font-semibold text-slate-100 mt-0.5">
            2013 Kedarnath Disaster
          </div>
          <div className="text-[11px] text-slate-400">
            Chorabari lake breach, extreme rainfall & valley-floor scouring
          </div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded p-2.5">
          <div className="font-mono text-[10px] text-amber-300 uppercase">
            2014–2019 • Period III
          </div>
          <div className="font-semibold text-slate-100 mt-0.5">
            Post-Disaster Stabilization & Recovery
          </div>
          <div className="text-[11px] text-slate-400">
            Landsat 8 OLI & Sentinel-2 MSI (from 2017)
          </div>
        </div>
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded p-2.5">
          <div className="font-mono text-[10px] text-emerald-300 uppercase">
            2020–2026 YTD • Period IV
          </div>
          <div className="font-semibold text-slate-100 mt-0.5">
            Recent Regime (2026 Year-to-Date)
          </div>
          <div className="text-[11px] text-slate-400">
            Sentinel-2 10m + Landsat 8/9; 2026 flagged as partial year-to-date
          </div>
        </div>
      </div>

      {/* 4 Indicator Time-Series Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {renderIndicatorChart("water_area_ha", "Surface Water Area (ha)", "#5ec8e5")}
        {renderIndicatorChart("snow_ice_area_ha", "Snow & Ice Cover (ha)", "#e0f2fe")}
        {renderIndicatorChart("ndvi_mean", "Mean Vegetation Index (NDVI)", "#4ade80")}
        {renderIndicatorChart(
          "exposed_ground_area_ha",
          "Exposed Ground / Debris (ha)",
          "#fb923c"
        )}
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {/* Standard Epoch Comparisons & Custom Pair Form */}
      <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-glacier-400" />
            <span className="font-semibold uppercase tracking-wider text-slate-200">
              Epoch Pair Change Detection
            </span>
          </div>

          {/* Standard Comparison Quick Buttons */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-slate-400 text-[11px] mr-1">
              Standard Pairs:
            </span>
            {comparisons.map(([a, b]) => (
              <button
                key={`${a}-${b}`}
                onClick={() => runPairComparison(a, b)}
                disabled={analysing}
                className={`px-2.5 py-1 rounded font-mono text-[11px] border transition-colors ${
                  yearA === a && yearB === b
                    ? "bg-glacier-400/20 border-glacier-400 text-glacier-300"
                    : "bg-ink-950 border-white/10 text-slate-300 hover:bg-ink-800"
                }`}
              >
                {a} vs {b}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Pair Controls */}
        <div className="flex flex-wrap items-end gap-3 pt-2 border-t border-white/10">
          <div>
            <label className="block text-slate-400 mb-1">Baseline Year (A)</label>
            <select
              value={yearA}
              onChange={(e) => setYearA(Number(e.target.value))}
              className="bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 font-mono text-slate-200"
            >
              {Array.from({ length: 27 }, (_, i) => 2000 + i).map((yr) => (
                <option key={yr} value={yr}>
                  {yr}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-slate-400 mb-1">Comparison Year (B)</label>
            <select
              value={yearB}
              onChange={(e) => setYearB(Number(e.target.value))}
              className="bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 font-mono text-slate-200"
            >
              {Array.from({ length: 27 }, (_, i) => 2000 + i).map((yr) => (
                <option key={yr} value={yr}>
                  {yr} {yr === 2026 ? "(YTD)" : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-slate-400 mb-1">Thematic Indicator</label>
            <select
              value={indicator}
              onChange={(e) => setIndicator(e.target.value)}
              className="bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
            >
              <option value="water">Surface Water (MNDWI)</option>
              <option value="vegetation">Vegetation Cover (NDVI)</option>
              <option value="snow_ice">Snow & Ice Cover (NDSI)</option>
              <option value="exposed_ground">Exposed Ground / Sediment</option>
              <option value="nbr">Normalized Burn / Disturbance Ratio (NBR)</option>
            </select>
          </div>
          <button
            onClick={() => runPairComparison(yearA, yearB, indicator)}
            disabled={analysing}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{analysing ? "Computing..." : "Analyse Change"}</span>
          </button>

          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={() => setViewMode("map")}
              className={`px-2.5 py-1.5 rounded border text-xs ${
                viewMode === "map"
                  ? "bg-glacier-400/20 border-glacier-400 text-glacier-300"
                  : "bg-ink-950 border-white/10 text-slate-400"
              }`}
            >
              Difference Map
            </button>
            <button
              onClick={() => setViewMode("swipe")}
              className={`px-2.5 py-1.5 rounded border text-xs ${
                viewMode === "swipe"
                  ? "bg-glacier-400/20 border-glacier-400 text-glacier-300"
                  : "bg-ink-950 border-white/10 text-slate-400"
              }`}
            >
              Swipe Before/After
            </button>
          </div>
        </div>
      </div>

      {/* Results & Caveats Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 space-y-3 text-xs">
          {analysisResult ? (
            <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="font-semibold uppercase tracking-wider text-slate-200">
                  Change Statistics ({analysisResult.year_a} →{" "}
                  {analysisResult.year_b})
                </span>
                <span className="font-mono text-glacier-300 uppercase">
                  {analysisResult.indicator}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 font-mono">
                <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500 uppercase">
                    Area Gain (ha)
                  </div>
                  <div className="text-sm font-semibold text-hazard-low mt-0.5">
                    {analysisResult.statistics.area_gain_ha != null
                      ? `+${analysisResult.statistics.area_gain_ha.toFixed(2)}`
                      : "—"}
                  </div>
                </div>
                <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500 uppercase">
                    Area Loss (ha)
                  </div>
                  <div className="text-sm font-semibold text-hazard-veryhigh mt-0.5">
                    {analysisResult.statistics.area_loss_ha != null
                      ? `-${analysisResult.statistics.area_loss_ha.toFixed(2)}`
                      : "—"}
                  </div>
                </div>
                <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500 uppercase">
                    Net Change (ha)
                  </div>
                  <div className="text-sm font-semibold text-glacier-300 mt-0.5">
                    {analysisResult.statistics.net_change_ha != null
                      ? analysisResult.statistics.net_change_ha.toFixed(2)
                      : "—"}
                  </div>
                </div>
                <div className="bg-ink-950 p-2.5 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500 uppercase">
                    Mean Index Δ
                  </div>
                  <div className="text-sm font-semibold text-slate-200 mt-0.5">
                    {analysisResult.statistics.mean_difference != null
                      ? analysisResult.statistics.mean_difference.toFixed(4)
                      : "—"}
                  </div>
                </div>
              </div>

              <div className="text-[11px] text-slate-400 font-mono">
                Sensors: {analysisResult.mission_a} ({analysisResult.year_a}) vs.{" "}
                {analysisResult.mission_b} ({analysisResult.year_b})
              </div>

              {/* Prominent Caveats */}
              {analysisResult.caveats && analysisResult.caveats.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded p-2.5 space-y-1">
                  <div className="font-semibold text-amber-300 flex items-center gap-1.5 text-[11px]">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>Methodological & Sensor Caveats</span>
                  </div>
                  <ul className="list-disc list-inside text-[11px] text-amber-200/90 space-y-0.5">
                    {analysisResult.caveats.map((c, idx) => (
                      <li key={idx}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-ink-900 border border-white/10 rounded-md p-6 text-center text-slate-500 text-xs">
              Select a standard comparison pair above or click "Analyse Change" to compute pixel-wise transitions and area statistics.
            </div>
          )}

          {/* Prior Analyses List */}
          {pastResults.length > 0 && (
            <div className="bg-ink-900 border border-white/10 rounded-md p-3 space-y-2">
              <div className="font-semibold uppercase tracking-wider text-slate-300 text-[11px] flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-glacier-400" />
                <span>Saved Change Analyses ({pastResults.length})</span>
              </div>
              <div className="max-h-40 overflow-y-auto divide-y divide-white/5 font-mono text-[11px]">
                {pastResults.map((pr) => (
                  <button
                    key={pr.id}
                    onClick={() => setAnalysisResult(pr)}
                    className={`w-full text-left py-1.5 px-2 flex items-center justify-between hover:bg-white/5 rounded ${
                      analysisResult?.id === pr.id ? "bg-glacier-400/15" : ""
                    }`}
                  >
                    <span className="text-slate-200">
                      {pr.year_a} → {pr.year_b} ({pr.indicator})
                    </span>
                    <span className="text-glacier-300">
                      {pr.statistics?.net_change_ha != null
                        ? `${pr.statistics.net_change_ha.toFixed(1)} ha`
                        : ""}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-8">
          {viewMode === "swipe" ? (
            <SwipeCompare
              beforeOverlay={beforeOverlay}
              afterOverlay={afterOverlay}
              beforeLabel={
                analysisResult
                  ? `${analysisResult.year_a} (${analysisResult.mission_a})`
                  : "Before"
              }
              afterLabel={
                analysisResult
                  ? `${analysisResult.year_b} (${analysisResult.mission_b})`
                  : "After"
              }
              height="450px"
            />
          ) : (
            <GeoMap height="450px" customRasters={customRasters} />
          )}
        </div>
      </div>
    </div>
  );
};
