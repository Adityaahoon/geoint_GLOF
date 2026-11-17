import React, { useEffect, useState, useCallback } from "react";
import {
  Droplets,
  Download,
  Upload,
  Plus,
  AlertTriangle,
  Route,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { api } from "../api/client";
import type {
  FloodScenario,
  FlowpathResponse,
  LakeFeatureProperties,
  RasterOverlayResponse,
} from "../api/types";
import { GeoMap, CustomRasterOverlay, CustomVectorOverlay } from "../components/GeoMap";

export const FloodSimulation: React.FC = () => {
  const [scenarios, setScenarios] = useState<FloodScenario[]>([]);
  const [lakes, setLakes] = useState<LakeFeatureProperties[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(
    null
  );

  // Create Scenario Form State
  const [name, setName] = useState<string>("");
  const [sourceLakeId, setSourceLakeId] = useState<number | "">("");
  const [description, setDescription] = useState<string>("");
  const [hydrographSource, setHydrographSource] = useState<string>("");
  const [hydrographRows, setHydrographRows] = useState<
    { time_s: number; discharge_m3s: number }[]
  >([
    { time_s: 0, discharge_m3s: 0 },
    { time_s: 900, discharge_m3s: 450 },
    { time_s: 1800, discharge_m3s: 1200 },
    { time_s: 3600, discharge_m3s: 350 },
    { time_s: 7200, discharge_m3s: 50 },
  ]);
  const [assumptionsText, setAssumptionsText] = useState<string>(
    "Moraine overtopping wave; Clear-water 2D shallow-water equations; Constant Manning n=0.06 along Mandakini channel"
  );
  const [downstreamKm, setDownstreamKm] = useState<number>(25);
  const [manningN, setManningN] = useState<number>(0.06);

  // Upload Hydraulic Result State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadVariable, setUploadVariable] = useState<string>("depth");
  const [modelSoftware, setModelSoftware] = useState<string>("HEC-RAS 6.5 2D");
  const [uploading, setUploading] = useState<boolean>(false);

  // Flowpath & Map Overlay State
  const [flowpath, setFlowpath] = useState<FlowpathResponse | null>(null);
  const [activeResultId, setActiveResultId] = useState<number | null>(null);
  const [resultOverlay, setResultOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadScenariosAndLakes = useCallback(async () => {
    try {
      const [scList, lakeInv] = await Promise.all([
        api.getFloodScenarios().catch(() => []),
        api.getLakeInventory().catch(() => null),
      ]);
      setScenarios(scList);
      if (scList.length > 0 && selectedScenarioId === null) {
        setSelectedScenarioId(scList[0].id);
      }
      const props = (lakeInv?.features || []).map((f) => f.properties);
      setLakes(props);
      if (props.length > 0 && sourceLakeId === "") {
        setSourceLakeId(props[0].lake_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load flood scenarios");
    }
  }, [selectedScenarioId, sourceLakeId]);

  useEffect(() => {
    loadScenariosAndLakes();
  }, [loadScenariosAndLakes]);

  const selectedScenario =
    scenarios.find((s) => s.id === selectedScenarioId) ||
    scenarios[0] ||
    null;

  // Load overlay for activeResultId
  useEffect(() => {
    const resList = selectedScenario?.results || [];
    const target =
      resList.find((r) => r.id === activeResultId) || resList[0] || null;
    if (!target?.raster?.id) {
      setResultOverlay(null);
      return;
    }
    const cmap =
      target.variable === "depth"
        ? "Blues"
        : target.variable === "velocity"
        ? "plasma"
        : "viridis";
    api
      .getRasterOverlay(target.raster.id, { cmap })
      .then(setResultOverlay)
      .catch(() => setResultOverlay(null));
  }, [selectedScenario, activeResultId]);

  const handleCreateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Scenario name is required.");
      return;
    }
    if (!hydrographSource.trim()) {
      setError(
        "Citation / Source for the breach hydrograph is strictly required for scientific reproducibility."
      );
      return;
    }
    setError(null);
    try {
      const created = await api.createFloodScenario({
        name: name.trim(),
        source_lake_id: sourceLakeId !== "" ? Number(sourceLakeId) : null,
        description: description.trim(),
        hydrograph: {
          time_s: hydrographRows.map((r) => Number(r.time_s)),
          discharge_m3s: hydrographRows.map((r) => Number(r.discharge_m3s)),
        },
        hydrograph_source: hydrographSource.trim(),
        assumptions: assumptionsText
          .split(";")
          .map((s) => s.trim())
          .filter(Boolean),
        downstream_length_km: downstreamKm,
        manning_n: manningN,
      });
      setScenarios((prev) => [created, ...prev]);
      setSelectedScenarioId(created.id);
      setName("");
    } catch (err: any) {
      setError(err?.message || "Failed to create hypothetical flood scenario");
    }
  };

  const handleExportHecRas = async (scenarioId: number) => {
    setError(null);
    try {
      const res = await api.exportFloodScenario(scenarioId);
      if (res.download_url) {
        window.open(res.download_url, "_blank");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to export HEC-RAS package");
    }
  };

  const handleUploadResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedScenario || !uploadFile) return;
    setUploading(true);
    setError(null);
    try {
      const uploaded = await api.uploadFloodResult(
        selectedScenario.id,
        uploadFile,
        uploadVariable,
        modelSoftware
      );
      setActiveResultId(uploaded.id);
      setUploadFile(null);
      await loadScenariosAndLakes();
    } catch (err: any) {
      setError(err?.message || "Failed to import hydraulic result GeoTIFF");
    } finally {
      setUploading(false);
    }
  };

  const handleTraceFlowpath = async (lakeId?: number | null) => {
    const targetLakeId =
      lakeId ?? selectedScenario?.source_lake_id ?? (sourceLakeId !== "" ? Number(sourceLakeId) : undefined);
    setError(null);
    try {
      const fp = await api.computeFlowpath(
        targetLakeId !== undefined
          ? { lake_id: targetLakeId }
          : { lat: 30.748, lon: 79.061 } // Chorabari default fallback
      );
      setFlowpath(fp);
    } catch (err: any) {
      setError(
        err?.message ||
          "Failed to trace terrain flowpath (ensure DEM and terrain analysis are completed)"
      );
    }
  };

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    if (!resultOverlay || !selectedScenario?.results?.length) return [];
    const target =
      selectedScenario.results.find((r) => r.id === activeResultId) ||
      selectedScenario.results[0];
    if (!target) return [];
    return [
      {
        id: `flood-res-${target.id}`,
        label: `HYPOTHETICAL ${target.variable.toUpperCase()} (${
          target.model_software
        })`,
        overlay: resultOverlay,
        rasterId: target.raster?.id,
      },
    ];
  }, [resultOverlay, selectedScenario, activeResultId]);

  const customVectors: CustomVectorOverlay[] = React.useMemo(() => {
    const list: CustomVectorOverlay[] = [];
    if (flowpath?.geometry) {
      list.push({
        id: "steepest-descent-flowpath",
        label: `Terrain Flow Path (${(flowpath.length_m / 1000).toFixed(1)} km)`,
        data: flowpath.geometry,
        color: "#38bdf8",
        weight: 3,
      });
    }
    return list;
  }, [flowpath]);

  return (
    <div className="space-y-4">
      {/* Header + Mandatory HYPOTHETICAL SCENARIO Badge */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold text-slate-100">
              Downstream GLOF Routing & HEC-RAS 2D Integration
            </h1>
            <span className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 font-mono text-[10px] font-semibold uppercase">
              HYPOTHETICAL SCENARIO WORKFLOW
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Export terrain domains & breach hydrographs for external 2D hydrodynamic solvers (HEC-RAS / BASEMENT / r.avaflow) and import simulated rasters
          </p>
        </div>
        <button
          onClick={() => handleTraceFlowpath()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-glacier-400/15 hover:bg-glacier-400/25 border border-glacier-400/30 text-glacier-300 text-xs"
        >
          <Route className="w-3.5 h-3.5" />
          <span>Trace Steepest-Descent Flow Path</span>
        </button>
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {/* Top Grid: Create Scenario & Scenario List (5 cols) + Map & Imported Results (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column */}
        <div className="lg:col-span-5 space-y-4 text-xs">
          {/* Scenario Selector & Export */}
          <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
            <div className="flex items-center justify-between border-b border-white/10 pb-2">
              <span className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <Droplets className="w-3.5 h-3.5 text-glacier-400" />
                <span>Hypothetical Scenarios ({scenarios.length})</span>
              </span>
            </div>

            {scenarios.length > 0 ? (
              <div className="space-y-2.5">
                <select
                  value={selectedScenario?.id ?? ""}
                  onChange={(e) => setSelectedScenarioId(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200 font-medium"
                >
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.id}>
                      [HYPOTHETICAL] #{s.id} • {s.name} ({s.status})
                    </option>
                  ))}
                </select>

                {selectedScenario && (
                  <div className="bg-ink-950 border border-white/5 rounded p-2.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 font-mono text-[10px] uppercase">
                        Type: {selectedScenario.scenario_type || "hypothetical"}
                      </span>
                      <button
                        onClick={() => handleExportHecRas(selectedScenario.id)}
                        className="flex items-center gap-1 px-2.5 py-1 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 text-[11px]"
                      >
                        <Download className="w-3 h-3" />
                        <span>Export HEC-RAS Package (.zip)</span>
                      </button>
                    </div>
                    <div className="text-[11px] text-slate-300">
                      <strong className="text-slate-400">Hydrograph Citation:</strong>{" "}
                      {selectedScenario.hydrograph_source}
                    </div>
                    {selectedScenario.assumptions?.length > 0 && (
                      <div className="text-[11px] text-slate-400">
                        <strong>Assumptions:</strong>{" "}
                        {selectedScenario.assumptions.join(" • ")}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-500 py-4 text-center bg-ink-950 rounded border border-white/5">
                No hypothetical scenarios defined yet. Create one below.
              </div>
            )}

            {/* Import External Hydraulic Solver Result Form */}
            {selectedScenario && (
              <form
                onSubmit={handleUploadResult}
                className="pt-2 border-t border-white/10 space-y-2"
              >
                <div className="font-semibold text-slate-300 text-[11px]">
                  Import External Hydraulic Solver Raster (.tif)
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-slate-400 text-[10px] mb-0.5">
                      Variable
                    </label>
                    <select
                      value={uploadVariable}
                      onChange={(e) => setUploadVariable(e.target.value)}
                      className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 text-slate-200"
                    >
                      <option value="depth">Max Flood Depth (m)</option>
                      <option value="velocity">Max Flow Velocity (m/s)</option>
                      <option value="wse">Water Surface Elevation (m)</option>
                      <option value="arrival_time">Wave Arrival Time (hr)</option>
                      <option value="duration">Inundation Duration (hr)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-400 text-[10px] mb-0.5">
                      Solver Software
                    </label>
                    <input
                      type="text"
                      value={modelSoftware}
                      onChange={(e) => setModelSoftware(e.target.value)}
                      className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 text-slate-200"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    accept=".tif,.tiff"
                    onChange={(e) =>
                      setUploadFile(e.target.files?.[0] || null)
                    }
                    className="flex-1 text-[11px] text-slate-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-ink-800 file:text-slate-200"
                  />
                  <button
                    type="submit"
                    disabled={!uploadFile || uploading}
                    className="px-3 py-1 rounded bg-glacier-400/20 border border-glacier-400/40 text-glacier-300 flex items-center gap-1 disabled:opacity-40"
                  >
                    <Upload className="w-3 h-3" />
                    <span>{uploading ? "..." : "Import"}</span>
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Create New Hypothetical Scenario Form */}
          <form
            onSubmit={handleCreateScenario}
            className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5"
          >
            <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2 flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-glacier-400" />
              <span>Define New Hypothetical Breach Scenario</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">
                  Scenario Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Chorabari Hypothetical 50% Breach"
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 text-slate-200"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Source Lake</label>
                <select
                  value={sourceLakeId}
                  onChange={(e) =>
                    setSourceLakeId(e.target.value ? Number(e.target.value) : "")
                  }
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 text-slate-200"
                >
                  <option value="">Select mapped lake...</option>
                  {lakes.map((l) => (
                    <option key={l.lake_id} value={l.lake_id}>
                      {l.name} ({l.area_ha?.toFixed(2)} ha)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-amber-300 font-medium mb-1">
                Hydrograph Citation / Literature Source (Required) *
              </label>
              <input
                type="text"
                required
                value={hydrographSource}
                onChange={(e) => setHydrographSource(e.target.value)}
                placeholder="e.g., Rafiq et al. (2019) / Froehlich (2008) parametric breach relation"
                className="w-full bg-ink-950 border border-amber-500/40 rounded px-2.5 py-1.5 text-slate-200"
              />
            </div>

            {/* Editable Hydrograph Table */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-400">
                  Inflow Breach Hydrograph Table (t [s], Q [m³/s])
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setHydrographRows((r) => [
                      ...r,
                      {
                        time_s: (r[r.length - 1]?.time_s ?? 0) + 1800,
                        discharge_m3s: 0,
                      },
                    ])
                  }
                  className="text-[10px] text-glacier-400 hover:underline"
                >
                  + Add Row
                </button>
              </div>
              <div className="max-h-28 overflow-y-auto bg-ink-950 border border-white/5 rounded p-1.5 space-y-1 font-mono text-[11px]">
                {hydrographRows.map((row, idx) => (
                  <div key={idx} className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      value={row.time_s}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setHydrographRows((prev) =>
                          prev.map((item, i) =>
                            i === idx ? { ...item, time_s: val } : item
                          )
                        );
                      }}
                      className="bg-ink-900 border border-white/10 rounded px-2 py-0.5 text-slate-200"
                      placeholder="Time (s)"
                    />
                    <input
                      type="number"
                      value={row.discharge_m3s}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setHydrographRows((prev) =>
                          prev.map((item, i) =>
                            i === idx ? { ...item, discharge_m3s: val } : item
                          )
                        );
                      }}
                      className="bg-ink-900 border border-white/10 rounded px-2 py-0.5 text-glacier-300"
                      placeholder="Q (m³/s)"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">
                Explicit Physical Assumptions (semicolon-separated)
              </label>
              <input
                type="text"
                value={assumptionsText}
                onChange={(e) => setAssumptionsText(e.target.value)}
                className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 text-slate-200"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">
                  Downstream Domain (km)
                </label>
                <input
                  type="number"
                  value={downstreamKm}
                  onChange={(e) => setDownstreamKm(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 font-mono text-slate-200"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">
                  Channel Manning's n
                </label>
                <input
                  type="number"
                  step="0.005"
                  value={manningN}
                  onChange={(e) => setManningN(Number(e.target.value))}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 font-mono text-slate-200"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-1.5 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium"
            >
              Save Hypothetical Scenario
            </button>
          </form>
        </div>

        {/* Right Column: Map, Empty State / Results, and Flowpath Elevation Profile */}
        <div className="lg:col-span-7 space-y-4 text-xs">
          {/* Mandatory Empty State when no hydraulic results are imported */}
          {(!selectedScenario ||
            !selectedScenario.results ||
            selectedScenario.results.length === 0) && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-md p-3 flex items-center justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-300 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-amber-200">
                    No hydraulic results imported – results are never generated from the DEM alone
                  </div>
                  <p className="text-[11px] text-amber-100/80 mt-0.5">
                    To adhere to physical hydrodynamics, GlacioGuard AI never fabricates flood depth or velocity rasters via simple DEM thresholding. Export the HEC-RAS 2D package on the left, run the shallow-water solver externally, and upload the resulting GeoTIFF.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Imported Results Selector if available */}
          {selectedScenario?.results && selectedScenario.results.length > 0 && (
            <div className="bg-ink-900 border border-white/10 rounded-md p-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Imported Solver Raster:</span>
                {selectedScenario.results.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => setActiveResultId(r.id)}
                    className={`px-2.5 py-1 rounded font-mono text-[11px] border ${
                      (activeResultId ?? selectedScenario.results[0].id) === r.id
                        ? "bg-glacier-400/20 border-glacier-400 text-glacier-300"
                        : "bg-ink-950 border-white/10 text-slate-400"
                    }`}
                  >
                    {r.variable.toUpperCase()} (max:{" "}
                    {r.statistics?.max?.toFixed(2) ?? "—"})
                  </button>
                ))}
              </div>
            </div>
          )}

          <GeoMap
            height="420px"
            customRasters={customRasters}
            customVectors={customVectors}
            defaultLayers={{
              studyArea: true,
              lakes: true,
              rivers: true,
              referencePoints: true,
            }}
          />

          {/* Flowpath Longitudinal Elevation Profile & Hydrograph Chart */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="bg-ink-900 border border-white/10 rounded-md p-3 space-y-2">
              <div className="font-semibold uppercase tracking-wider text-slate-200">
                Steepest-Descent Longitudinal Profile
              </div>
              {flowpath?.profile && flowpath.profile.length > 0 ? (
                <>
                  <div className="h-40">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={flowpath.profile}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                        <XAxis
                          dataKey="distance_m"
                          stroke="#64748b"
                          tick={{ fontSize: 10 }}
                          tickFormatter={(v) => `${(v / 1000).toFixed(1)}km`}
                        />
                        <YAxis
                          stroke="#64748b"
                          tick={{ fontSize: 10 }}
                          domain={["auto", "auto"]}
                          unit="m"
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#0b1220",
                            borderColor: "rgba(255,255,255,0.15)",
                            fontSize: 11,
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="elevation_m"
                          name="Elevation (m)"
                          stroke="#5ec8e5"
                          fill="#5ec8e5"
                          fillOpacity={0.2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="text-[10px] text-amber-300/90">
                    Caveat: {flowpath.caveat}
                  </div>
                </>
              ) : (
                <div className="h-40 flex items-center justify-center text-slate-500 bg-ink-950 rounded border border-white/5 text-center px-3">
                  Click "Trace Steepest-Descent Flow Path" at the top right to extract the topographic channel profile from the DEM.
                </div>
              )}
            </div>

            <div className="bg-ink-900 border border-white/10 rounded-md p-3 space-y-2">
              <div className="font-semibold uppercase tracking-wider text-slate-200">
                Hypothetical Breach Hydrograph
              </div>
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={
                      selectedScenario?.hydrograph
                        ? selectedScenario.hydrograph.time_s.map((t, i) => ({
                            time_s: t,
                            discharge_m3s:
                              selectedScenario.hydrograph!.discharge_m3s[i] ?? 0,
                          }))
                        : hydrographRows
                    }
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a2638" />
                    <XAxis
                      dataKey="time_s"
                      stroke="#64748b"
                      tick={{ fontSize: 10 }}
                      unit="s"
                    />
                    <YAxis
                      stroke="#64748b"
                      tick={{ fontSize: 10 }}
                      unit=" m³/s"
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0b1220",
                        borderColor: "rgba(255,255,255,0.15)",
                        fontSize: 11,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="discharge_m3s"
                      name="Discharge (m³/s)"
                      stroke="#fb923c"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
