import React, { useEffect, useState, useCallback } from "react";
import {
  AlertOctagon,
  Play,
  CloudRain,
  MapPin,
  AlertTriangle,
  Info,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import type {
  DisasterCompareResponse,
  DisasterContextResponse,
  RainfallResponse,
  RasterOverlayResponse,
} from "../api/types";
import { useAppContext } from "../context/AppContext";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";
import { GeoMap, CustomRasterOverlay } from "../components/GeoMap";
import { SwipeCompare } from "../components/SwipeCompare";

const DEFAULT_MECHANISMS = [
  {
    key: "glof",
    label: "1. Chorabari Tal Glacial Lake Outburst (GLOF)",
    description:
      "Breach of the moraine-dammed Chorabari Tal (~3,960 m a.s.l.) on the morning of 17 June 2013 released a sudden high-velocity water-debris wave into the upper Mandakini channel.",
  },
  {
    key: "rainfall_flash_flood",
    label: "2. Extreme Orographic Rainfall & Snowmelt Flash Flood",
    description:
      "Multi-day extreme precipitation (14–17 June 2013, >300 mm over 48h) falling on seasonal snowpack generated intense basin-wide runoff prior to and concurrent with the lake breach.",
  },
  {
    key: "landslides_debris_flows",
    label: "3. Widespread Hillslope Landslides & Debris Flows",
    description:
      "Saturated paraglacial moraines and steep valley walls experienced massive slope failures, supplying vast sediment volumes and scouring the Mandakini corridor through Rambara and Gaurikund.",
  },
  {
    key: "combined_exposure",
    label: "4. Compound Multi-Hazard Exposure in Constrained Valley",
    description:
      "Convergence of flood waves, hyperconcentrated debris flows, and channel avulsion across dense pilgrimage infrastructure on the Kedarnath outwash fan and Mandakini valley floor.",
  },
];

export const DisasterImpactAnalysis: React.FC = () => {
  const { studyArea } = useAppContext();

  const [disasterCtx, setDisasterCtx] =
    useState<DisasterContextResponse | null>(null);
  const [preYear, setPreYear] = useState<number>(2012);
  const [postYear, setPostYear] = useState<number>(2013);
  const [region, setRegion] = useState<string>("mandakini_corridor");

  const [compareRes, setCompareRes] =
    useState<DisasterCompareResponse | null>(null);
  const [comparing, setComparing] = useState<boolean>(false);
  const [rainfall, setRainfall] = useState<RainfallResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);

  const [beforeOverlay, setBeforeOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [afterOverlay, setAfterOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [diffOverlay, setDiffOverlay] =
    useState<RasterOverlayResponse | null>(null);

  const loadContextAndRainfall = useCallback(async () => {
    try {
      const [ctx, rain] = await Promise.all([
        api.getDisasterContext().catch(() => null),
        api.getRainfall().catch(() => null),
      ]);
      setDisasterCtx(ctx);
      setRainfall(rain);
    } catch {
      // handled gracefully
    }
  }, []);

  useEffect(() => {
    loadContextAndRainfall();
  }, [loadContextAndRainfall]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    api.getRainfall().then(setRainfall).catch(() => {});
  });

  // Load overlays when compareRes updates
  useEffect(() => {
    if (!compareRes?.rasters) {
      setBeforeOverlay(null);
      setAfterOverlay(null);
      setDiffOverlay(null);
      return;
    }
    const { before, after, difference } = compareRes.rasters;
    if (before?.id) {
      api.getRasterOverlay(before.id).then(setBeforeOverlay).catch(() => {});
    }
    if (after?.id) {
      api.getRasterOverlay(after.id).then(setAfterOverlay).catch(() => {});
    }
    if (difference?.id) {
      api
        .getRasterOverlay(difference.id, { cmap: "RdBu_r" })
        .then(setDiffOverlay)
        .catch(() => {});
    }
  }, [compareRes]);

  const handleRunCompare = async () => {
    setComparing(true);
    setError(null);
    try {
      const res = await api.compareDisaster({
        pre_year: preYear,
        post_year: postYear,
        region,
      });
      setCompareRes(res);
    } catch (err: any) {
      setError(err?.message || "Failed to run pre/post disaster comparison");
    } finally {
      setComparing(false);
    }
  };

  const handleFetchRainfall = async () => {
    setError(null);
    try {
      const res = await api.fetchRainfall({
        source: "nasa_power",
        start_year: 2013,
        end_year: 2013,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start rainfall ingestion job");
    }
  };

  const mechanisms =
    disasterCtx?.mechanisms?.length
      ? disasterCtx.mechanisms
      : DEFAULT_MECHANISMS;

  // Extract June 2013 rainfall series if available
  const june2013Rainfall = React.useMemo(() => {
    if (!rainfall?.series) return [];
    const firstKey = Object.keys(rainfall.series)[0];
    if (!firstKey) return [];
    const pts = rainfall.series[firstKey] || [];
    const junePts = pts.filter((p) => p.date.startsWith("2013-06"));
    return junePts.length > 0 ? junePts : pts.slice(0, 60);
  }, [rainfall]);

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    const arr: CustomRasterOverlay[] = [];
    if (diffOverlay && compareRes?.rasters?.difference) {
      arr.push({
        id: "disaster-diff",
        label: `Geomorphic Change Difference (${preYear}→${postYear})`,
        overlay: diffOverlay,
        rasterId: compareRes.rasters.difference.id,
      });
    }
    if (afterOverlay && compareRes?.rasters?.after) {
      arr.push({
        id: "disaster-after",
        label: `Post-Event (${postYear})`,
        overlay: afterOverlay,
        rasterId: compareRes.rasters.after.id,
      });
    }
    return arr;
  }, [diffOverlay, afterOverlay, compareRes, preYear, postYear]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            June 2013 Kedarnath Compound Disaster Impact Analysis
          </h1>
          <p className="text-xs text-slate-400">
            Pre- and post-event satellite surface change assessment across Chorabari Tal, Kedarnath town, Rambara, and Mandakini corridor
          </p>
        </div>
      </div>

      {/* Scientific Causation Disclaimer Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-md p-3 flex items-start gap-2.5 text-xs">
        <Info className="w-4 h-4 text-amber-300 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-amber-200">
            Scientific Attribution & Causation Disclaimer
          </div>
          <p className="text-amber-100/85 leading-relaxed">
            Optical and multispectral satellite imagery measures post-event geomorphic and land-cover change (debris fan deposition, vegetation stripping, channel widening, and Chorabari lake drainage). Remote sensing alone cannot isolate the exact hydrodynamic contribution of a single physical mechanism; the June 2013 catastrophe resulted from the compound interaction of four distinct processes detailed below.
          </p>
        </div>
      </div>

      {/* Context & 4 Distinct Mechanisms */}
      <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
        <div className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
          <AlertOctagon className="w-4 h-4 text-hazard-veryhigh" />
          <span>2013 Kedarnath Compound Event Context & Four Physical Mechanisms</span>
        </div>
        <p className="text-slate-300 leading-relaxed">
          {disasterCtx?.context ||
            studyArea?.disaster_context ||
            "During 15–17 June 2013, extreme orographic rainfall combined with rapid snowmelt and the breach of Chorabari Tal triggered catastrophic flooding and debris flows along the Mandakini River valley."}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          {mechanisms.map((m) => (
            <div
              key={m.key}
              className="bg-ink-950 border border-white/10 rounded p-3 space-y-1.5"
            >
              <div className="font-semibold text-glacier-300 text-xs">
                {m.label}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                {m.description}
              </p>
            </div>
          ))}
        </div>
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

      {/* Pre/Post Comparison Controls */}
      <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 flex flex-wrap items-end gap-3 text-xs">
        <div>
          <label className="block text-slate-400 mb-1">Pre-Event Baseline Year</label>
          <select
            value={preYear}
            onChange={(e) => setPreYear(Number(e.target.value))}
            className="bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 font-mono text-slate-200"
          >
            <option value={2011}>2011 (Post-Monsoon)</option>
            <option value={2012}>2012 (Immediate Pre-Disaster)</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-400 mb-1">Post-Event Year</label>
          <select
            value={postYear}
            onChange={(e) => setPostYear(Number(e.target.value))}
            className="bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 font-mono text-slate-200"
          >
            <option value={2013}>2013 (Post-Monsoon 2013)</option>
            <option value={2014}>2014 (1-Year Post-Event)</option>
          </select>
        </div>

        <div>
          <label className="block text-slate-400 mb-1">Target Corridor / Region</label>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
          >
            <option value="mandakini_corridor">Mandakini Valley Corridor</option>
            <option value="chorabari">Chorabari Glacier & Lake Basin</option>
            <option value="kedarnath_town">Kedarnath Town Outwash Fan</option>
            <option value="full_aoi">Full Study Area (AOI)</option>
          </select>
        </div>

        <button
          onClick={handleRunCompare}
          disabled={comparing}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5" />
          <span>
            {comparing ? "Running Comparison..." : "Run Pre/Post Disaster Compare"}
          </span>
        </button>
      </div>

      {/* Swipe Slider + Difference Map Side-by-Side */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-6">
          <SwipeCompare
            beforeOverlay={beforeOverlay}
            afterOverlay={afterOverlay}
            beforeLabel={`Pre-Disaster (${preYear})`}
            afterLabel={`Post-Disaster (${postYear})`}
            height="400px"
          />
        </div>
        <div className="lg:col-span-6">
          <GeoMap height="442px" customRasters={customRasters} />
        </div>
      </div>

      {/* Bottom Row: Affected Locations & Stats + June 2013 Rainfall Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Affected Locations & Change Summary */}
        <div className="lg:col-span-6 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-glacier-400" />
            <span>Affected Corridor Locations & Observed Footprint</span>
          </div>

          {compareRes ? (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 font-mono">
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Area Gain (ha)</div>
                  <div className="text-slate-200 font-semibold mt-0.5">
                    {compareRes.statistics?.area_gain_ha?.toFixed(2) ?? "—"}
                  </div>
                </div>
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Area Loss (ha)</div>
                  <div className="text-slate-200 font-semibold mt-0.5">
                    {compareRes.statistics?.area_loss_ha?.toFixed(2) ?? "—"}
                  </div>
                </div>
                <div className="bg-ink-950 p-2 rounded border border-white/5">
                  <div className="text-[10px] text-slate-500">Net Δ (ha)</div>
                  <div className="text-glacier-300 font-semibold mt-0.5">
                    {compareRes.statistics?.net_change_ha?.toFixed(2) ?? "—"}
                  </div>
                </div>
              </div>

              {compareRes.affected_locations &&
                compareRes.affected_locations.length > 0 && (
                  <div className="divide-y divide-white/5 max-h-48 overflow-y-auto">
                    {compareRes.affected_locations.map((loc, idx) => (
                      <div key={idx} className="py-2 space-y-0.5">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-200">
                            {loc.name}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">
                            {loc.lat.toFixed(4)}°N, {loc.lon.toFixed(4)}°E
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {loc.change_summary}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

              {compareRes.caveats && compareRes.caveats.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded p-2 text-[11px] text-amber-200 space-y-0.5">
                  <div className="font-semibold flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>Observation Caveats</span>
                  </div>
                  {compareRes.caveats.map((c, i) => (
                    <div key={i}>• {c}</div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-slate-500 py-8 text-center bg-ink-950 rounded border border-white/5">
              Click "Run Pre/Post Disaster Compare" to compute corridor disturbance statistics and location summaries.
            </div>
          )}
        </div>

        {/* Rainfall Around June 2013 */}
        <div className="lg:col-span-6 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="flex items-center justify-between">
            <div className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <CloudRain className="w-3.5 h-3.5 text-glacier-400" />
              <span>Meteorological Precipitation Context (2013)</span>
            </div>
            <button
              onClick={handleFetchRainfall}
              disabled={isRunning}
              className="px-2.5 py-1 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-[11px] disabled:opacity-50"
            >
              Fetch Rainfall Data
            </button>
          </div>

          {june2013Rainfall.length > 0 ? (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={june2013Rainfall}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 10 }}
                    unit=" mm"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0b1220",
                      borderColor: "rgba(255,255,255,0.15)",
                      fontSize: 12,
                    }}
                  />
                  <Bar
                    dataKey="precipitation_mm"
                    name="Daily Precipitation (mm)"
                    fill="#38bdf8"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-slate-500 py-10 text-center bg-ink-950 rounded border border-white/5 px-4">
              No precipitation series loaded yet. Click "Fetch Rainfall Data" to retrieve daily precipitation observations for the Kedarnath basin.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
