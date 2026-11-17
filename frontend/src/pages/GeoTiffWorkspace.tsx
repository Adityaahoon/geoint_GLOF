import React, { useEffect, useState, useCallback } from "react";
import {
  Upload,
  FileSpreadsheet,
  Download,
  Wrench,
  Eye,
  Info,
  AlertTriangle,
} from "lucide-react";
import { api } from "../api/client";
import type {
  GeoJSONFeatureCollection,
  GeoTIFFMetadata,
  RasterAsset,
  RasterOverlayResponse,
  VectorAsset,
} from "../api/types";
import { useAppContext } from "../context/AppContext";
import { GeoMap, CustomRasterOverlay, CustomVectorOverlay } from "../components/GeoMap";

export const GeoTiffWorkspace: React.FC = () => {
  const { studyArea } = useAppContext();

  const [rasters, setRasters] = useState<RasterAsset[]>([]);
  const [vectors, setVectors] = useState<VectorAsset[]>([]);
  const [selectedRasterId, setSelectedRasterId] = useState<number | null>(null);
  const [selectedVectorId, setSelectedVectorId] = useState<number | null>(null);

  const [metadata, setMetadata] = useState<GeoTIFFMetadata | null>(null);
  const [rasterOverlay, setRasterOverlay] =
    useState<RasterOverlayResponse | null>(null);
  const [vectorGeoJSON, setVectorGeoJSON] =
    useState<GeoJSONFeatureCollection | null>(null);

  // Upload & Processing States
  const [uploading, setUploading] = useState<boolean>(false);
  const [processing, setProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Processing Tool Form State
  const [operation, setOperation] = useState<
    "reproject" | "clip" | "resample" | "index" | "statistics"
  >("reproject");
  const [dstCrs, setDstCrs] = useState<string>("EPSG:32644");
  const [resampling, setResampling] = useState<string>("bilinear");
  const [targetRes, setTargetRes] = useState<number>(30);
  const [clipRegion, setClipRegion] = useState<string>("full_aoi");
  const [indexName, setIndexName] = useState<string>("mndwi");
  const [bandGreen, setBandGreen] = useState<number>(2);
  const [bandRed, setBandRed] = useState<number>(3);
  const [bandNir, setBandNir] = useState<number>(4);
  const [bandSwir, setBandSwir] = useState<number>(5);

  const loadUploads = useCallback(async () => {
    try {
      const res = await api.getUploads();
      setRasters(res.rasters || []);
      setVectors(res.vectors || []);
      if (res.rasters?.length && selectedRasterId === null) {
        setSelectedRasterId(res.rasters[0].id);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load uploaded assets");
    }
  }, [selectedRasterId]);

  useEffect(() => {
    loadUploads();
  }, [loadUploads]);

  // Fetch metadata & overlay when selectedRasterId changes
  useEffect(() => {
    if (selectedRasterId === null) {
      setMetadata(null);
      setRasterOverlay(null);
      return;
    }
    api
      .getGeotiffMetadata(selectedRasterId)
      .then(setMetadata)
      .catch(() => setMetadata(null));
    api
      .getRasterOverlay(selectedRasterId)
      .then(setRasterOverlay)
      .catch(() => setRasterOverlay(null));
  }, [selectedRasterId]);

  // Fetch vector GeoJSON when selectedVectorId changes
  useEffect(() => {
    if (selectedVectorId === null) {
      setVectorGeoJSON(null);
      return;
    }
    api
      .getUploadedVectorGeoJSON(selectedVectorId)
      .then(setVectorGeoJSON)
      .catch(() => setVectorGeoJSON(null));
  }, [selectedVectorId]);

  const handleFilesSelected = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const files = Array.from(fileList);
      const res = await api.uploadGeotiffFiles(files);
      await loadUploads();
      if (res.type === "raster" && res.asset?.id) {
        setSelectedRasterId(res.asset.id);
      } else if (res.type === "vector" && res.asset?.id) {
        setSelectedVectorId(res.asset.id);
      }
    } catch (err: any) {
      setError(err?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleRunProcess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRasterId) {
      setError("Select a raster asset first.");
      return;
    }
    setProcessing(true);
    setError(null);
    try {
      let params: Record<string, any> = {};
      if (operation === "reproject") {
        params = { dst_crs: dstCrs, resampling };
      } else if (operation === "clip") {
        params = { region: clipRegion };
      } else if (operation === "resample") {
        params = { resolution: targetRes, resampling };
      } else if (operation === "index") {
        params = {
          index: indexName,
          band_map: {
            green: bandGreen,
            red: bandRed,
            nir: bandNir,
            swir: bandSwir,
          },
        };
      }
      const res = await api.processGeotiff({
        asset_id: selectedRasterId,
        operation,
        params,
      });
      await loadUploads();
      if (res.asset?.id) {
        setSelectedRasterId(res.asset.id);
      }
    } catch (err: any) {
      setError(err?.message || "Geoprocessing operation failed");
    } finally {
      setProcessing(false);
    }
  };

  const customRasters: CustomRasterOverlay[] = React.useMemo(() => {
    const r = rasters.find((x) => x.id === selectedRasterId);
    if (!r || !rasterOverlay) return [];
    return [
      {
        id: `ws-raster-${r.id}`,
        label: r.name,
        overlay: rasterOverlay,
        rasterId: r.id,
      },
    ];
  }, [selectedRasterId, rasterOverlay, rasters]);

  const customVectors: CustomVectorOverlay[] = React.useMemo(() => {
    const v = vectors.find((x) => x.id === selectedVectorId);
    if (!v || !vectorGeoJSON) return [];
    return [
      {
        id: `ws-vec-${v.id}`,
        label: v.name,
        data: vectorGeoJSON,
        color: "#facc15",
      },
    ];
  }, [selectedVectorId, vectorGeoJSON, vectors]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold text-slate-100">
            GeoTIFF & Vector Geoprocessing Workspace
          </h1>
          <p className="text-xs text-slate-400">
            Ingest external GeoTIFFs, Shapefiles (.shp+.shx+.dbf+.prj or .zip), GeoJSON, or GeoPackage; inspect CRS/band metadata and run non-destructive processing
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-glacier-300 bg-glacier-400/10 border border-glacier-400/30 rounded px-2.5 py-1">
          <Info className="w-3.5 h-3.5 shrink-0" />
          <span>Original uploaded files are immutable; processing creates derived assets.</span>
        </div>
      </div>

      {error && (
        <div className="bg-hazard-veryhigh/10 border border-hazard-veryhigh/30 text-hazard-veryhigh px-3 py-2 rounded text-xs">
          {error}
        </div>
      )}

      {/* Drag and Drop Upload Zone */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFilesSelected(e.dataTransfer.files);
        }}
        className="bg-ink-900 border-2 border-dashed border-white/15 hover:border-glacier-400/50 rounded-md p-4 text-center transition-colors"
      >
        <label className="cursor-pointer flex flex-col items-center justify-center gap-1.5 text-xs">
          <Upload className="w-5 h-5 text-glacier-400" />
          <span className="font-medium text-slate-200">
            {uploading
              ? "Uploading & Inspecting Geospatial Asset..."
              : "Drag & drop .tif, .tiff, .geojson, .gpkg, .zip, or .shp (+ .shx, .dbf, .prj) files here, or click to browse"}
          </span>
          <input
            type="file"
            multiple
            accept=".tif,.tiff,.shp,.shx,.dbf,.prj,.zip,.geojson,.json,.gpkg"
            onChange={(e) => handleFilesSelected(e.target.files)}
            className="hidden"
          />
        </label>
      </div>

      {/* Main Grid: Uploads & Geoprocessing Tools (5 cols) + Map & Metadata (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5 space-y-4 text-xs">
          {/* Uploaded Assets List */}
          <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-2.5">
            <div className="font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
              <FileSpreadsheet className="w-3.5 h-3.5 text-glacier-400" />
              <span>
                Workspace Rasters ({rasters.length}) & Vectors ({vectors.length})
              </span>
            </div>

            {rasters.length > 0 || vectors.length > 0 ? (
              <div className="max-h-56 overflow-y-auto divide-y divide-white/5 font-mono text-[11px]">
                {rasters.map((r) => (
                  <div
                    key={`r-${r.id}`}
                    onClick={() => setSelectedRasterId(r.id)}
                    className={`py-2 px-2 flex items-center justify-between cursor-pointer hover:bg-white/5 rounded ${
                      selectedRasterId === r.id ? "bg-glacier-400/15" : ""
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="text-slate-200 truncate font-sans font-medium">
                        {r.name}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {r.crs} • {r.width}×{r.height} • {r.band_count}b ({r.dtype}) •{" "}
                        {r.is_original ? "Original" : `Derived (Parent #${r.parent_id})`}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0 ml-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedRasterId(r.id);
                        }}
                        className="p-1 rounded bg-white/5 hover:bg-white/10 text-glacier-300"
                        title="Preview on Map"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <a
                        href={api.getRasterDownloadUrl(r.id)}
                        onClick={(e) => e.stopPropagation()}
                        className="p-1 rounded bg-white/5 hover:bg-white/10 text-slate-300"
                        title="Download GeoTIFF"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                ))}

                {vectors.map((v) => (
                  <div
                    key={`v-${v.id}`}
                    onClick={() => setSelectedVectorId(v.id)}
                    className={`py-2 px-2 flex items-center justify-between cursor-pointer hover:bg-white/5 rounded ${
                      selectedVectorId === v.id ? "bg-amber-400/15" : ""
                    }`}
                  >
                    <div>
                      <div className="text-amber-300 font-sans font-medium">
                        [Vector] {v.name}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {v.crs} • {v.feature_count} features (
                        {v.geometry_types?.join(", ")})
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-500 py-6 text-center bg-ink-950 rounded border border-white/5">
                No files uploaded yet. Drag and drop a GeoTIFF or vector file above.
              </div>
            )}
          </div>

          {/* Geoprocessing Tools Form */}
          <form
            onSubmit={handleRunProcess}
            className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3"
          >
            <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2 flex items-center gap-1.5">
              <Wrench className="w-3.5 h-3.5 text-glacier-400" />
              <span>Non-Destructive Geoprocessing Tools</span>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Operation</label>
              <select
                value={operation}
                onChange={(e) => setOperation(e.target.value as any)}
                className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
              >
                <option value="reproject">Reproject CRS</option>
                <option value="clip">Clip to Study Sub-Region</option>
                <option value="resample">Resample Spatial Resolution</option>
                <option value="index">Compute Normalized Spectral Index</option>
                <option value="statistics">Recompute Band Statistics</option>
              </select>
            </div>

            {operation === "reproject" && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1">Target CRS</label>
                  <select
                    value={dstCrs}
                    onChange={(e) => setDstCrs(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                  >
                    <option value="EPSG:32644">EPSG:32644 (UTM 44N)</option>
                    <option value="EPSG:4326">EPSG:4326 (WGS84)</option>
                    <option value="EPSG:3857">EPSG:3857 (Web Mercator)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Resampling</label>
                  <select
                    value={resampling}
                    onChange={(e) => setResampling(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 text-slate-200"
                  >
                    <option value="bilinear">Bilinear</option>
                    <option value="nearest">Nearest Neighbour</option>
                    <option value="cubic">Cubic Convolution</option>
                  </select>
                </div>
              </div>
            )}

            {operation === "clip" && (
              <div>
                <label className="block text-slate-400 mb-1">
                  Target Region Polygon
                </label>
                <select
                  value={clipRegion}
                  onChange={(e) => setClipRegion(e.target.value)}
                  className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
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
            )}

            {operation === "resample" && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-slate-400 mb-1">
                    Resolution (m)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={targetRes}
                    onChange={(e) => setTargetRes(Number(e.target.value))}
                    className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 font-mono text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Resampling</label>
                  <select
                    value={resampling}
                    onChange={(e) => setResampling(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1.5 text-slate-200"
                  >
                    <option value="bilinear">Bilinear</option>
                    <option value="nearest">Nearest Neighbour</option>
                    <option value="cubic">Cubic</option>
                  </select>
                </div>
              </div>
            )}

            {operation === "index" && (
              <div className="space-y-2">
                <div>
                  <label className="block text-slate-400 mb-1">
                    Spectral Index
                  </label>
                  <select
                    value={indexName}
                    onChange={(e) => setIndexName(e.target.value)}
                    className="w-full bg-ink-950 border border-white/10 rounded px-2.5 py-1.5 text-slate-200"
                  >
                    <option value="mndwi">MNDWI (Green, SWIR)</option>
                    <option value="ndwi">NDWI (Green, NIR)</option>
                    <option value="ndvi">NDVI (NIR, Red)</option>
                    <option value="ndsi">NDSI (Green, SWIR)</option>
                    <option value="nbr">NBR (NIR, SWIR)</option>
                  </select>
                </div>
                <div className="grid grid-cols-4 gap-1.5 font-mono text-[11px]">
                  <div>
                    <label className="block text-[10px] text-slate-500">
                      Green Band
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={bandGreen}
                      onChange={(e) => setBandGreen(Number(e.target.value))}
                      className="w-full bg-ink-950 border border-white/10 rounded px-1.5 py-1 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500">
                      Red Band
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={bandRed}
                      onChange={(e) => setBandRed(Number(e.target.value))}
                      className="w-full bg-ink-950 border border-white/10 rounded px-1.5 py-1 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500">
                      NIR Band
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={bandNir}
                      onChange={(e) => setBandNir(Number(e.target.value))}
                      className="w-full bg-ink-950 border border-white/10 rounded px-1.5 py-1 text-slate-200"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-slate-500">
                      SWIR Band
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={bandSwir}
                      onChange={(e) => setBandSwir(Number(e.target.value))}
                      className="w-full bg-ink-950 border border-white/10 rounded px-1.5 py-1 text-slate-200"
                    />
                  </div>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={!selectedRasterId || processing}
              className="w-full py-2 px-3 rounded bg-glacier-400/20 hover:bg-glacier-400/30 border border-glacier-400/40 text-glacier-300 font-medium disabled:opacity-40"
            >
              {processing
                ? "Processing Derived Raster..."
                : "Execute & Save New Derived GeoTIFF"}
            </button>
          </form>
        </div>

        {/* Right Column: Map Preview + Full Metadata Inspector */}
        <div className="lg:col-span-7 space-y-4 text-xs">
          <GeoMap
            height="380px"
            customRasters={customRasters}
            customVectors={customVectors}
          />

          {/* Metadata Inspector */}
          <div className="bg-ink-900 border border-white/10 rounded-md p-3.5 space-y-3">
            <div className="font-semibold uppercase tracking-wider text-slate-200 border-b border-white/10 pb-2">
              GeoTIFF Metadata & Band Statistics Inspector
            </div>

            {metadata ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
                  <div className="bg-ink-950 p-2 rounded border border-white/5">
                    <div className="text-[10px] text-slate-500">Dimensions</div>
                    <div className="text-slate-200 mt-0.5">
                      {metadata.width} × {metadata.height} px
                    </div>
                  </div>
                  <div className="bg-ink-950 p-2 rounded border border-white/5">
                    <div className="text-[10px] text-slate-500">CRS / EPSG</div>
                    <div className="text-glacier-300 mt-0.5">
                      {metadata.crs} ({metadata.is_projected ? "Projected" : "Geographic"})
                    </div>
                  </div>
                  <div className="bg-ink-950 p-2 rounded border border-white/5">
                    <div className="text-[10px] text-slate-500">Resolution</div>
                    <div className="text-slate-200 mt-0.5">
                      {metadata.resolution?.[0]?.toFixed(2)} ×{" "}
                      {metadata.resolution?.[1]?.toFixed(2)} {metadata.units}
                    </div>
                  </div>
                  <div className="bg-ink-950 p-2 rounded border border-white/5">
                    <div className="text-[10px] text-slate-500">Bands / NoData</div>
                    <div className="text-slate-200 mt-0.5">
                      {metadata.band_count} bands • NoData:{" "}
                      {metadata.nodata ?? "None"}
                    </div>
                  </div>
                </div>

                {metadata.warnings && metadata.warnings.length > 0 && (
                  <div className="bg-amber-500/10 border border-amber-500/30 rounded p-2 text-[11px] text-amber-200">
                    <AlertTriangle className="w-3.5 h-3.5 inline mr-1" />
                    {metadata.warnings.join(" • ")}
                  </div>
                )}

                {metadata.statistics?.bands &&
                  metadata.statistics.bands.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse font-mono text-[11px]">
                        <thead>
                          <tr className="border-b border-white/10 text-[10px] uppercase text-slate-400">
                            <th className="py-1 px-2">Band</th>
                            <th className="py-1 px-2">Description</th>
                            <th className="py-1 px-2">Min</th>
                            <th className="py-1 px-2">Max</th>
                            <th className="py-1 px-2">Mean</th>
                            <th className="py-1 px-2">Std</th>
                            <th className="py-1 px-2">Valid %</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {metadata.statistics.bands.map((b, i) => (
                            <tr key={b.band}>
                              <td className="py-1 px-2 text-glacier-300">
                                #{b.band}
                              </td>
                              <td className="py-1 px-2 text-slate-300">
                                {metadata.band_descriptions?.[i] ||
                                  `Band ${b.band}`}
                              </td>
                              <td className="py-1 px-2 text-slate-200">
                                {b.min != null ? b.min.toFixed(3) : "—"}
                              </td>
                              <td className="py-1 px-2 text-slate-200">
                                {b.max != null ? b.max.toFixed(3) : "—"}
                              </td>
                              <td className="py-1 px-2 text-slate-200">
                                {b.mean != null ? b.mean.toFixed(3) : "—"}
                              </td>
                              <td className="py-1 px-2 text-slate-400">
                                {b.std != null ? b.std.toFixed(3) : "—"}
                              </td>
                              <td className="py-1 px-2 text-slate-300">
                                {(b.valid_fraction * 100).toFixed(1)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
              </div>
            ) : (
              <div className="text-slate-500 py-6 text-center">
                Select a raster asset from the workspace list to inspect its CRS, dimensions, and per-band statistics.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
