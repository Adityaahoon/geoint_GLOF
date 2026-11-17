import React, { useEffect, useState, useCallback } from "react";
import {
  MountainSnow,
  Play,
  AlertTriangle,
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
import type {
  ChangeAnalysisResult,
  GlacierSummaryResponse,
  RasterOverlayResponse,
} from "../api/types";
import { useAppContext } from "../context/AppContext";
import { GeoMap, CustomRasterOverlay, CustomVectorOverlay } from "../components/GeoMap";

export const GlacierMonitoring: React.FC = () => {
  const { studyArea } = useAppContext();

  const [region, setRegion] = useState<string>("chorabari");
  const [glacierData, setGlacierData] =
    useState<GlacierSummaryResponse | null>(null);
  const [yearA, setYearA] = useState<number>(2000);
  const [yearB, setYearB] = useState<number>(2024);
  const [ndsiResult, setNdsiResult] = useState<ChangeAnalysisResult | null>(
    null
  );
  const [ndsiOverlay, setNdsiOverlay] = useState<RasterOverlayResponse | null>(
    null
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadGlacierSummary = useCallback(async () => {
    setError(null);
    try {
      const res = await api.getGlacierSummary(region);
      setGlacierData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load glacier monitoring summary");
    }
  }, [region]);

  useEffect(() => {
    loadGlacierSummary();
  }, [loadGlacierSummary]);

  useEffect(() => {
    if (!ndsiResult?.rasters?.difference?.id) {
      setNdsiOverlay(null);
      return;
    }
    api
      .getRasterOverlay(ndsiResult.rasters.difference.id, { cmap: "RdBu" })
      .then(setNdsiOverlay)
      .catch(() => setNdsiOverlay(null));
  }, [ndsiResult]);

  const handleCompareNdsi = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.analyseChange({
        year_a: yearA,
        year_b: yearB,
        indicator: "snow_ice",
        region,
      });
      setNdsiResult(res);
    } catch (err: any) {
      setError(err?.message || "NDSI snow/ice comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    if (!ndsiOverlay || !ndsiResult?.rasters?.difference) return [];
    return [
      {
        id: "ndsi-diff",
        label: `NDSI Snow/Ice Difference (${ndsiResult.year_a}→${ndsiResult.year_b})`,
        overlay: ndsiOverlay,
        rasterId: ndsiResult.rasters.difference.id,
      },
    ];
  }, [ndsiOverlay, ndsiResult]);

  const customVectors: CustomVectorOverlay[] = React.useMemo(() => {
    if (!glacierData?.outlines) return [];
    return [
      {
        id: "glacier-outlines",
        label: `Glacier Outlines (${glacierData.outline_source || "RGI / GLIMS"})`,
        data: glacierData.outlines,
        color: "#e0f2fe",
        fillOpacity: 0.25,
        weight: 1.8,
      },
    ];
  }, [glacierData]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Cryosphere & Glacier Monitoring (Chorabari & Companion Glaciers)
          </h1>
          <p className="text-xs text-slate-400">
            Post-monsoon snow and clean-ice surface extent derived from spectral NDSI, glacier inventory outlines, and debris-cover caveats
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Glacier Sub-Basin:</span>
          <select
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            className="bg-ink-900 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
          >
            <option value="chorabari">Chorabari & Companion Glaciers</option>
            <option value="full_aoi">Full Study Area (AOI)</option>
            {studyArea?.regions &&
              Object.entries(studyArea.regions)
                .filter(([k]) => k !== "chorabari")
                .map(([k, r]) => (
                  <option key={k} value={k}>
                    {r.name}
                  </option>
                ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {/* Scientific Notes Banner */}
      {glacierData?.notes && glacierData.notes.length > 0 && (
        <div className="bg-ink-900 border border-white/10 rounded-md p-3 space-y-1 text-xs">
          <div className="font-semibold text-glacier-300 flex items-center gap-1.5">
            <Info className="w-4 h-4 shrink-0" />
            <span>Cryospheric Remote Sensing Notes & Limitations</span>
          </div>
          <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px]">
            {glacierData.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Snow/Ice Area Time Series + NDSI Comparison Controls */}
        <div className="lg:col-span-5 space-y-4 text-xs">
          <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <MountainSnow className="w-3.5 h-3.5 text-glacier-400" />
                <span>Observed Snow & Clean-Ice Area (ha)</span>
              </span>
              {glacierData?.outline_source && (
                <span className="font-mono text-[10px] text-slate-400">
                  Outlines: {glacierData.outline_source}
                </span>
              )}
            </div>

            {glacierData?.series && glacierData.series.length > 0 ? (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={glacierData.series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                    <XAxis
                      dataKey="year"
                      stroke="#64748b"
                      tick={{ fontSize: 11 }}
                    />
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
                      dataKey="snow_ice_area_ha"
                      name="Snow/Ice Area (ha)"
                      stroke="#e0f2fe"
                      strokeWidth={2}
                      dot={{ r: 3.5, fill: "#7dd3fc" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-56 flex items-center justify-center text-slate-500 bg-ink-950 rounded border border-white/5 px-4 text-center">
                No post-monsoon snow/ice series computed yet. Build satellite composites to populate empirical NDSI area observations.
              </div>
            )}
          </div>

          {/* NDSI Comparison Tool */}
          <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
            <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
              NDSI Snow & Ice Epoch Comparison
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">Epoch A</label>
                <select
                  value={yearA}
                  onChange={(e) => setYearA(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                >
                  {Array.from({ length: 27 }, (_, i) => 2000 + i).map((yr) => (
                    <option key={yr} value={yr}>
                      {yr}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Epoch B</label>
                <select
                  value={yearB}
                  onChange={(e) => setYearB(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                >
                  {Array.from({ length: 27 }, (_, i) => 2000 + i).map((yr) => (
                    <option key={yr} value={yr}>
                      {yr}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleCompareNdsi}
              disabled={loading}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>
                {loading ? "Computing NDSI Change..." : "Compute NDSI Overlay"}
              </span>
            </button>

            {ndsiResult && (
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 space-y-1.5 font-mono text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Snow/Ice Gain:</span>
                  <span className="text-hazard-low">
                    +{ndsiResult.statistics.area_gain_ha?.toFixed(2) ?? "—"} ha
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Snow/Ice Loss:</span>
                  <span className="text-hazard-veryhigh">
                    -{ndsiResult.statistics.area_loss_ha?.toFixed(2) ?? "—"} ha
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Net Δ:</span>
                  <span className="text-glacier-300">
                    {ndsiResult.statistics.net_change_ha?.toFixed(2) ?? "—"} ha
                  </span>
                </div>
                {ndsiResult.caveats?.length > 0 && (
                  <div className="text-amber-300 text-[10px] font-sans pt-1 border-t border-white/5">
                    <AlertTriangle className="w-3 h-3 inline mr-1" />
                    {ndsiResult.caveats.join(" ")}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right: Glacier Map */}
        <div className="lg:col-span-7">
          <GeoMap
            height="520px"
            customRasters={customRasters}
            customVectors={customVectors}
            defaultLayers={{
              studyArea: true,
              glaciers: true,
              lakes: true,
              referencePoints: true,
            }}
          />
        </div>
      </div>
    </div>
  );
};
