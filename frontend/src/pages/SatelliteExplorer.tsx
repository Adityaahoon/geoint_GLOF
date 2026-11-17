import React, { useEffect, useState, useCallback } from "react";
import {
  Search,
  Layers,
  Download,
  AlertTriangle,
  Eye,
  Play,
  SlidersHorizontal,
} from "lucide-react";
import { api } from "../api/client";
import type {
  RasterOverlayResponse,
  SatelliteComposite,
  SatelliteMission,
  SatelliteSearchResponse,
} from "../api/types";
import { useAppContext } from "../context/AppContext";
import { useJob } from "../hooks/useJob";
import { JobProgress } from "../components/JobProgress";
import { GeoMap, CustomRasterOverlay, CustomVectorOverlay } from "../components/GeoMap";
import { SwipeCompare } from "../components/SwipeCompare";

export const SatelliteExplorer: React.FC = () => {
  const { studyArea, selectedYear, setSelectedYear } = useAppContext();

  const [missions, setMissions] = useState<SatelliteMission[]>([]);
  const [selectedMission, setSelectedMission] = useState<string>("sentinel2");
  const [region, setRegion] = useState<string>("full_aoi");
  const [startDate, setStartDate] = useState<string>(`${selectedYear}-09-15`);
  const [endDate, setEndDate] = useState<string>(`${selectedYear}-11-15`);
  const [maxCloud, setMaxCloud] = useState<number>(60);
  const [provider, setProvider] = useState<string>("auto");

  const [searchResult, setSearchResult] = useState<SatelliteSearchResponse | null>(
    null
  );
  const [searching, setSearching] = useState<boolean>(false);
  const [composites, setComposites] = useState<SatelliteComposite[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);

  // Map overlay & Swipe compare states
  const [activeCompositeId, setActiveCompositeId] = useState<number | null>(null);
  const [activeOverlay, setActiveOverlay] = useState<RasterOverlayResponse | null>(
    null
  );
  const [compareBeforeId, setCompareBeforeId] = useState<number | null>(null);
  const [compareAfterId, setCompareAfterId] = useState<number | null>(null);
  const [beforeOverlay, setBeforeOverlay] = useState<RasterOverlayResponse | null>(
    null
  );
  const [afterOverlay, setAfterOverlay] = useState<RasterOverlayResponse | null>(
    null
  );
  const [showSwipe, setShowSwipe] = useState<boolean>(false);

  const loadInitial = useCallback(async () => {
    try {
      const [mList, compList] = await Promise.all([
        api.getMissions(),
        api.getComposites(),
      ]);
      setMissions(mList);
      if (mList.length > 0 && !mList.some((m) => m.mission === selectedMission)) {
        setSelectedMission(mList[0].mission);
      }
      setComposites(compList);
      if (compList.length > 0 && activeCompositeId === null) {
        setActiveCompositeId(compList[0].composite_id);
      }
      if (compList.length >= 2 && compareBeforeId === null && compareAfterId === null) {
        setCompareBeforeId(compList[0].composite_id);
        setCompareAfterId(compList[compList.length - 1].composite_id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load satellite missions/composites");
    }
  }, [selectedMission, activeCompositeId, compareBeforeId, compareAfterId]);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    setStartDate(`${selectedYear}-09-15`);
    setEndDate(`${selectedYear}-11-15`);
  }, [selectedYear]);

  const { job, error: jobError, isRunning } = useJob(activeJobId, () => {
    api.getComposites().then(setComposites).catch(() => {});
  });

  // Load overlay for activeCompositeId
  useEffect(() => {
    const comp = composites.find((c) => c.composite_id === activeCompositeId);
    if (!comp?.raster?.id) {
      setActiveOverlay(null);
      return;
    }
    api
      .getRasterOverlay(comp.raster.id)
      .then(setActiveOverlay)
      .catch(() => setActiveOverlay(null));
  }, [activeCompositeId, composites]);

  // Load overlays for SwipeCompare
  useEffect(() => {
    const compA = composites.find((c) => c.composite_id === compareBeforeId);
    if (compA?.raster?.id) {
      api
        .getRasterOverlay(compA.raster.id)
        .then(setBeforeOverlay)
        .catch(() => setBeforeOverlay(null));
    } else {
      setBeforeOverlay(null);
    }
  }, [compareBeforeId, composites]);

  useEffect(() => {
    const compB = composites.find((c) => c.composite_id === compareAfterId);
    if (compB?.raster?.id) {
      api
        .getRasterOverlay(compB.raster.id)
        .then(setAfterOverlay)
        .catch(() => setAfterOverlay(null));
    } else {
      setAfterOverlay(null);
    }
  }, [compareAfterId, composites]);

  const currentMissionObj = missions.find((m) => m.mission === selectedMission);

  const handleSearchScenes = async (e: React.FormEvent) => {
    e.preventDefault();
    setSearching(true);
    setError(null);
    try {
      const res = await api.searchScenes({
        mission: selectedMission,
        start_date: startDate,
        end_date: endDate,
        region,
        max_cloud: maxCloud,
        provider,
      });
      setSearchResult(res);
    } catch (err: any) {
      setError(err?.message || "Scene search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleBuildComposite = async () => {
    setError(null);
    try {
      const res = await api.buildComposite({
        year: selectedYear,
        mission: selectedMission,
        region,
        season_start: startDate.slice(5) || "09-15",
        season_end: endDate.slice(5) || "11-15",
        max_cloud: maxCloud,
        provider,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      setError(err?.message || "Failed to start composite job");
    }
  };

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    const comp = composites.find((c) => c.composite_id === activeCompositeId);
    if (!comp || !activeOverlay) return [];
    return [
      {
        id: `comp-${comp.composite_id}`,
        label: `Composite ${comp.year} (${comp.mission})`,
        overlay: activeOverlay,
        rasterId: comp.raster?.id,
      },
    ];
  }, [activeCompositeId, activeOverlay, composites]);

  const customVectors: CustomVectorOverlay[] = React.useMemo(() => {
    if (!searchResult?.scenes) return [];
    const features = searchResult.scenes
      .filter((s) => s.footprint)
      .map((s) => ({
        type: "Feature" as const,
        geometry: s.footprint!,
        properties: { scene_id: s.scene_id, datetime: s.datetime },
      }));
    if (features.length === 0) return [];
    return [
      {
        id: "scene-footprints",
        label: `Scene Footprints (${features.length})`,
        data: { type: "FeatureCollection", features },
        color: "#facc15",
        fillOpacity: 0.05,
        weight: 1.2,
      },
    ];
  }, [searchResult]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            Historical Satellite Explorer (2000–2026)
          </h1>
          <p className="text-xs text-slate-400">
            Multi-sensor catalog discovery (Landsat 5/7/8/9, Sentinel-2, MODIS), seasonal cloud-free compositing, and swipe comparison
          </p>
        </div>
        <button
          onClick={() => setShowSwipe(!showSwipe)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-xs font-medium ${
            showSwipe
              ? "bg-glacier-400/20 border-glacier-400 text-glacier-300"
              : "bg-ink-900 border-white/10 text-slate-300 hover:bg-ink-800"
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>{showSwipe ? "Show Standard Map" : "Before/After Swipe Mode"}</span>
        </button>
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

      {/* Search & Build Composite Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3 text-xs">
          <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
            Mission & Acquisition Parameters
          </div>

          <form onSubmit={handleSearchScenes} className="space-y-2.5">
            <div>
              <label className="block text-slate-400 mb-1">Satellite Mission</label>
              <select
                value={selectedMission}
                onChange={(e) => setSelectedMission(e.target.value)}
                className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
              >
                {missions.map((m) => (
                  <option key={m.mission} value={m.mission}>
                    {m.label} ({m.native_resolution_m}m • {m.operational[0]}–
                    {m.operational[1] || "present"})
                  </option>
                ))}
              </select>
            </div>

            {/* Mission Notes (e.g., Landsat 7 SLC-off) */}
            {currentMissionObj && (
              <div className="bg-ink-950 border border-white/5 rounded p-2.5 space-y-1 text-[11px]">
                <div className="flex items-center justify-between text-slate-300 font-mono">
                  <span>Instrument: {currentMissionObj.instrument}</span>
                  <span>Res: {currentMissionObj.native_resolution_m}m</span>
                </div>
                {currentMissionObj.notes?.map((n, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-1.5 text-amber-300/90 mt-1"
                  >
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>{n}</span>
                  </div>
                ))}
                <div className="text-[10px] text-slate-500 pt-1">
                  Citation: {currentMissionObj.citation}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">Target Year</label>
                <select
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(Number(e.target.value))}
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
                <label className="block text-slate-400 mb-1">Sub-Region</label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 text-slate-200"
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

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 font-mono text-slate-200"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 font-mono text-slate-200"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-slate-400 mb-1">
                  Max Cloud Cover ({maxCloud}%)
                </label>
                <input
                  type="range"
                  min={5}
                  max={100}
                  step={5}
                  value={maxCloud}
                  onChange={(e) => setMaxCloud(Number(e.target.value))}
                  className="w-full accent-glacier-400"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 text-slate-200"
                >
                  <option value="auto">Auto (GEE / STAC)</option>
                  <option value="stac">STAC Open Catalog</option>
                  <option value="gee">Google Earth Engine</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <button
                type="submit"
                disabled={searching}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-ink-800 hover:bg-ink-700 border border-white/15 text-slate-200 font-medium"
              >
                <Search className="w-3.5 h-3.5 text-glacier-400" />
                <span>{searching ? "Searching..." : "Search Scenes"}</span>
              </button>
              <button
                type="button"
                onClick={handleBuildComposite}
                disabled={isRunning}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Build Composite</span>
              </button>
            </div>
          </form>
        </div>

        {/* Map or Swipe Comparison Area */}
        <div className="lg:col-span-8 space-y-3">
          {showSwipe ? (
            <div className="space-y-2">
              <div className="bg-ink-900 border border-white/10 rounded-md p-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Before Composite:</span>
                  <select
                    value={compareBeforeId ?? ""}
                    onChange={(e) => setCompareBeforeId(Number(e.target.value))}
                    className="bg-ink-950 border border-white/10 rounded px-2 py-1 text-slate-200 font-mono"
                  >
                    <option value="">Select composite...</option>
                    {composites.map((c) => (
                      <option key={c.composite_id} value={c.composite_id}>
                        #{c.composite_id} • {c.year} ({c.mission})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">After Composite:</span>
                  <select
                    value={compareAfterId ?? ""}
                    onChange={(e) => setCompareAfterId(Number(e.target.value))}
                    className="bg-ink-950 border border-white/10 rounded px-2 py-1 text-slate-200 font-mono"
                  >
                    <option value="">Select composite...</option>
                    {composites.map((c) => (
                      <option key={c.composite_id} value={c.composite_id}>
                        #{c.composite_id} • {c.year} ({c.mission})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <SwipeCompare
                beforeOverlay={beforeOverlay}
                afterOverlay={afterOverlay}
                beforeLabel={
                  composites.find((c) => c.composite_id === compareBeforeId)
                    ? `${
                        composites.find((c) => c.composite_id === compareBeforeId)!
                          .year
                      } (${
                        composites.find((c) => c.composite_id === compareBeforeId)!
                          .mission
                      })`
                    : "Before"
                }
                afterLabel={
                  composites.find((c) => c.composite_id === compareAfterId)
                    ? `${
                        composites.find((c) => c.composite_id === compareAfterId)!
                          .year
                      } (${
                        composites.find((c) => c.composite_id === compareAfterId)!
                          .mission
                      })`
                    : "After"
                }
                height="430px"
              />
            </div>
          ) : (
            <GeoMap
              height="480px"
              customRasters={customRasters}
              customVectors={customVectors}
            />
          )}
        </div>
      </div>

      {/* Built Composites Table & Scene Search Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Built Composites List */}
        <div className="lg:col-span-6 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-glacier-400" />
              <span>Generated Cloud-Free Composites ({composites.length})</span>
            </h2>
          </div>

          {composites.length > 0 ? (
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1.5 px-2">Year</th>
                    <th className="py-1.5 px-2">Mission</th>
                    <th className="py-1.5 px-2">Scenes</th>
                    <th className="py-1.5 px-2">Valid %</th>
                    <th className="py-1.5 px-2">Quality Flags</th>
                    <th className="py-1.5 px-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                  {composites.map((comp) => (
                    <tr
                      key={comp.composite_id}
                      className={`hover:bg-white/5 ${
                        activeCompositeId === comp.composite_id
                          ? "bg-glacier-400/10"
                          : ""
                      }`}
                    >
                      <td className="py-1.5 px-2 font-semibold text-slate-200">
                        {comp.year}
                      </td>
                      <td className="py-1.5 px-2 text-glacier-300">
                        {comp.mission} ({comp.resolution_m}m)
                      </td>
                      <td className="py-1.5 px-2 text-slate-300">
                        {comp.scene_count}
                      </td>
                      <td className="py-1.5 px-2 text-slate-300">
                        {comp.valid_fraction != null
                          ? `${(comp.valid_fraction * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                      <td className="py-1.5 px-2">
                        {comp.quality_flags && comp.quality_flags.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {comp.quality_flags.map((qf, i) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 text-[10px]"
                              >
                                {qf}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-slate-500">nominal</span>
                        )}
                      </td>
                      <td className="py-1.5 px-2 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => setActiveCompositeId(comp.composite_id)}
                            className="p-1 rounded bg-white/5 hover:bg-white/10 text-glacier-300"
                            title="Display on Map"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          {comp.raster?.id && (
                            <a
                              href={api.getRasterDownloadUrl(comp.raster.id)}
                              className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300"
                              title="Download GeoTIFF"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 py-8 text-center bg-ink-950 rounded border border-white/5">
              No satellite composites built yet. Select a mission and year and click "Build Composite".
            </div>
          )}
        </div>

        {/* Discovered Scenes Table */}
        <div className="lg:col-span-6 bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold uppercase tracking-wider text-slate-200">
              Catalog Scene Search Results{" "}
              {searchResult ? `(${searchResult.count} via ${searchResult.provider})` : ""}
            </h2>
          </div>

          {searchResult?.notes && searchResult.notes.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded p-2 text-[11px] text-amber-200 space-y-0.5">
              {searchResult.notes.map((n, i) => (
                <div key={i}>• {n}</div>
              ))}
            </div>
          )}

          {searchResult && searchResult.scenes.length > 0 ? (
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                    <th className="py-1.5 px-2">Preview</th>
                    <th className="py-1.5 px-2">Scene ID</th>
                    <th className="py-1.5 px-2">Acquisition Date</th>
                    <th className="py-1.5 px-2">Cloud %</th>
                    <th className="py-1.5 px-2">Flags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-[11px]">
                  {searchResult.scenes.map((sc) => (
                    <tr key={sc.scene_id} className="hover:bg-white/5">
                      <td className="py-1.5 px-2">
                        {sc.preview_url ? (
                          <img
                            src={sc.preview_url}
                            alt={sc.scene_id}
                            className="w-10 h-10 object-cover rounded border border-white/10"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded bg-ink-950 border border-white/5 flex items-center justify-center text-[9px] text-slate-500">
                            N/A
                          </div>
                        )}
                      </td>
                      <td className="py-1.5 px-2 text-slate-200 max-w-[160px] truncate" title={sc.scene_id}>
                        {sc.scene_id}
                      </td>
                      <td className="py-1.5 px-2 text-slate-300">
                        {sc.datetime?.slice(0, 10)}
                      </td>
                      <td className="py-1.5 px-2 text-slate-300">
                        {sc.cloud_cover != null ? `${sc.cloud_cover.toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-1.5 px-2">
                        {sc.quality_flags?.length ? (
                          <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 text-[10px]">
                            {sc.quality_flags.join(", ")}
                          </span>
                        ) : (
                          <span className="text-slate-500">ok</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 py-8 text-center bg-ink-950 rounded border border-white/5">
              Click "Search Scenes" to query available acquisitions from STAC / Earth Engine for your date & cloud criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
