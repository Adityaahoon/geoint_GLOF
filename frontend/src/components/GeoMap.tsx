import React, { useEffect, useState, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  ImageOverlay,
  GeoJSON,
  CircleMarker,
  Popup,
  useMap,
  useMapEvents,
} from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import {
  Layers,
  Search,
  Download,
  ChevronDown,
  ChevronRight,
  Compass,
  Eye,
  EyeOff,
} from "lucide-react";
import { api } from "../api/client";
import { useAppContext } from "../context/AppContext";
import type {
  GeoJSONFeatureCollection,
  GeoJSONGeometry,
  LakeFeatureProperties,
  RasterOverlayResponse,
  TerrainSummaryResponse,
} from "../api/types";

export interface CustomRasterOverlay {
  id: string;
  label: string;
  overlay: RasterOverlayResponse;
  rasterId?: number;
  defaultOpacity?: number;
}

export interface CustomVectorOverlay {
  id: string;
  label: string;
  data: GeoJSONFeatureCollection | GeoJSONGeometry;
  color?: string;
  fillOpacity?: number;
  weight?: number;
}

export interface GeoMapProps {
  height?: string;
  customRasters?: CustomRasterOverlay[];
  customVectors?: CustomVectorOverlay[];
  defaultLayers?: {
    studyArea?: boolean;
    referencePoints?: boolean;
    lakes?: boolean;
    susceptibility?: boolean;
    glaciers?: boolean;
    rivers?: boolean;
    watersheds?: boolean;
    infrastructure?: boolean;
    terrainProduct?: string | null;
  };
  onLakeSelect?: (lakeId: number) => void;
  selectedLakeId?: number | null;
  yearFilter?: number | null;
  onYearFilterChange?: (year: number | null) => void;
  showLayerControl?: boolean;
}

function MouseTracker({
  onMove,
}: {
  onMove: (coords: { lat: number; lon: number } | null) => void;
}) {
  useMapEvents({
    mousemove(e) {
      onMove({ lat: e.latlng.lat, lon: e.latlng.lng });
    },
    mouseout() {
      onMove(null);
    },
  });
  return null;
}

function MapFlyTo({ target }: { target: { lat: number; lon: number; zoom?: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (target) {
      map.flyTo([target.lat, target.lon], target.zoom ?? 14, { duration: 1.0 });
    }
  }, [target, map]);
  return null;
}

export const SUSCEPTIBILITY_COLORS: Record<string, string> = {
  Low: "#4ade80",
  Moderate: "#facc15",
  High: "#fb923c",
  "Very High": "#ef4444",
};

export const GeoMap: React.FC<GeoMapProps> = ({
  height = "520px",
  customRasters = [],
  customVectors = [],
  defaultLayers,
  onLakeSelect,
  selectedLakeId,
  yearFilter,
  onYearFilterChange,
  showLayerControl = true,
}) => {
  const { studyArea } = useAppContext();

  const [basemap, setBasemap] = useState<"satellite" | "topo" | "dark">("satellite");
  const [panelOpen, setPanelOpen] = useState<boolean>(true);
  const [mouseCoords, setMouseCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [flyTarget, setFlyTarget] = useState<{ lat: number; lon: number; zoom?: number } | null>(
    null
  );

  // Layer visibility toggles
  const [showStudyArea, setShowStudyArea] = useState<boolean>(
    defaultLayers?.studyArea ?? true
  );
  const [showRefPoints, setShowRefPoints] = useState<boolean>(
    defaultLayers?.referencePoints ?? true
  );
  const [showLakes, setShowLakes] = useState<boolean>(
    defaultLayers?.lakes ?? true
  );
  const [showSusceptibility, setShowSusceptibility] = useState<boolean>(
    defaultLayers?.susceptibility ?? false
  );
  const [showGlaciers, setShowGlaciers] = useState<boolean>(
    defaultLayers?.glaciers ?? false
  );
  const [showRivers, setShowRivers] = useState<boolean>(
    defaultLayers?.rivers ?? false
  );
  const [showWatersheds, setShowWatersheds] = useState<boolean>(
    defaultLayers?.watersheds ?? false
  );
  const [showInfra, setShowInfra] = useState<boolean>(
    defaultLayers?.infrastructure ?? false
  );
  const [activeTerrainKey, setActiveTerrainKey] = useState<string | null>(
    defaultLayers?.terrainProduct ?? null
  );

  // Opacity controls
  const [rasterOpacity, setRasterOpacity] = useState<number>(0.85);
  const [vectorOpacity, setVectorOpacity] = useState<number>(0.75);
  const [hiddenCustomIds, setHiddenCustomIds] = useState<Record<string, boolean>>({});

  // Loaded layer datasets
  const [lakesGeoJSON, setLakesGeoJSON] =
    useState<GeoJSONFeatureCollection<LakeFeatureProperties> | null>(null);
  const [glacierGeoJSON, setGlacierGeoJSON] =
    useState<GeoJSONFeatureCollection | null>(null);
  const [riversGeoJSON, setRiversGeoJSON] =
    useState<GeoJSONFeatureCollection | null>(null);
  const [watershedsGeoJSON, setWatershedsGeoJSON] =
    useState<GeoJSONFeatureCollection | null>(null);
  const [infraGeoJSON, setInfraGeoJSON] =
    useState<GeoJSONFeatureCollection | null>(null);
  const [terrainSummary, setTerrainSummary] =
    useState<TerrainSummaryResponse | null>(null);
  const [terrainOverlay, setTerrainOverlay] =
    useState<RasterOverlayResponse | null>(null);

  // Fetch lakes when toggled or year changes
  useEffect(() => {
    if (!showLakes && !showSusceptibility) return;
    api
      .getLakeInventory(yearFilter ?? undefined)
      .then(setLakesGeoJSON)
      .catch(() => {});
  }, [showLakes, showSusceptibility, yearFilter]);

  // Fetch glacier outlines when toggled
  useEffect(() => {
    if (!showGlaciers || glacierGeoJSON) return;
    api
      .getGlacierSummary("chorabari")
      .then((res) => {
        if (res.outlines) setGlacierGeoJSON(res.outlines);
      })
      .catch(() => {});
  }, [showGlaciers, glacierGeoJSON]);

  // Fetch rivers/watersheds when toggled
  useEffect(() => {
    if (!showRivers || riversGeoJSON) return;
    api
      .getVectorGeoJSON("streams")
      .then(setRiversGeoJSON)
      .catch(() => {
        api.getVectorGeoJSON("rivers").then(setRiversGeoJSON).catch(() => {});
      });
  }, [showRivers, riversGeoJSON]);

  useEffect(() => {
    if (!showWatersheds || watershedsGeoJSON) return;
    api
      .getVectorGeoJSON("watersheds")
      .then(setWatershedsGeoJSON)
      .catch(() => {
        api.getVectorGeoJSON("basins").then(setWatershedsGeoJSON).catch(() => {});
      });
  }, [showWatersheds, watershedsGeoJSON]);

  // Fetch infrastructure when toggled
  useEffect(() => {
    if (!showInfra || infraGeoJSON) return;
    api
      .getInfrastructure()
      .then(setInfraGeoJSON)
      .catch(() => {});
  }, [showInfra, infraGeoJSON]);

  // Fetch terrain summary once so user can toggle elevation/slope/hillshade/hand
  useEffect(() => {
    api
      .getTerrainSummary()
      .then(setTerrainSummary)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!activeTerrainKey || !terrainSummary?.products?.[activeTerrainKey]) {
      setTerrainOverlay(null);
      return;
    }
    const asset = terrainSummary.products[activeTerrainKey];
    const cmap =
      activeTerrainKey === "elevation" || activeTerrainKey === "dem"
        ? "terrain"
        : activeTerrainKey === "slope"
        ? "inferno"
        : activeTerrainKey === "hand"
        ? "Blues_r"
        : "gray";
    api
      .getRasterOverlay(asset.id, { cmap })
      .then(setTerrainOverlay)
      .catch(() => setTerrainOverlay(null));
  }, [activeTerrainKey, terrainSummary]);

  // Study area bounds: [w, s, e, n] -> [[s, w], [n, e]]
  const defaultBounds: LatLngBoundsExpression = useMemo(() => {
    if (studyArea?.bbox && studyArea.bbox.length === 4) {
      const [w, s, e, n] = studyArea.bbox;
      return [
        [s, w],
        [n, e],
      ];
    }
    return [
      [30.55, 78.9],
      [30.9, 79.25],
    ];
  }, [studyArea]);

  // Searchable places: reference points + loaded lakes + loaded infrastructure
  const searchablePlaces = useMemo(() => {
    const items: { label: string; category: string; lat: number; lon: number }[] = [];
    if (studyArea?.reference_points) {
      for (const pt of studyArea.reference_points) {
        items.push({
          label: pt.name,
          category: pt.type || "Reference",
          lat: pt.lat,
          lon: pt.lon,
        });
      }
    }
    if (lakesGeoJSON?.features) {
      for (const f of lakesGeoJSON.features) {
        const p = f.properties;
        if (p?.name && f.geometry) {
          // Estimate centroid of polygon/point
          const coords = f.geometry.coordinates;
          if (f.geometry.type === "Point") {
            items.push({
              label: `${p.name} (${p.lake_code})`,
              category: "Glacial Lake",
              lon: coords[0],
              lat: coords[1],
            });
          } else if (f.geometry.type === "Polygon" && coords?.[0]?.[0]) {
            items.push({
              label: `${p.name} (${p.lake_code})`,
              category: "Glacial Lake",
              lon: coords[0][0][0],
              lat: coords[0][0][1],
            });
          }
        }
      }
    }
    if (infraGeoJSON?.features) {
      for (const f of infraGeoJSON.features) {
        const p = f.properties;
        if (p?.name && f.geometry?.type === "Point") {
          items.push({
            label: p.name,
            category: p.category || "OSM",
            lon: f.geometry.coordinates[0],
            lat: f.geometry.coordinates[1],
          });
        }
      }
    }
    return items;
  }, [studyArea, lakesGeoJSON, infraGeoJSON]);

  const filteredPlaces = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    return searchablePlaces
      .filter(
        (p) =>
          p.label.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q)
      )
      .slice(0, 8);
  }, [searchQuery, searchablePlaces]);

  const exportGeoJSON = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/geo+json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="relative w-full bg-ink-950 border border-white/10 rounded-md overflow-hidden"
      style={{ height }}
    >
      <MapContainer
        bounds={defaultBounds}
        className="w-full h-full z-0"
        scrollWheelZoom={true}
      >
        <MouseTracker onMove={setMouseCoords} />
        <MapFlyTo target={flyTarget} />

        {/* Basemaps */}
        {basemap === "satellite" && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics"
            maxZoom={19}
          />
        )}
        {basemap === "topo" && (
          <TileLayer
            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            attribution="Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)"
            maxZoom={17}
          />
        )}
        {basemap === "dark" && (
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution="&copy; OpenStreetMap contributors &copy; CARTO"
            maxZoom={19}
          />
        )}

        {/* Terrain Raster Overlay */}
        {terrainOverlay && (
          <ImageOverlay
            url={terrainOverlay.image_url}
            bounds={terrainOverlay.bounds as LatLngBoundsExpression}
            opacity={rasterOpacity}
            zIndex={300}
          />
        )}

        {/* Custom Raster Overlays from parent pages */}
        {customRasters.map((cr, idx) =>
          !hiddenCustomIds[cr.id] && cr.overlay ? (
            <ImageOverlay
              key={cr.id}
              url={cr.overlay.image_url}
              bounds={cr.overlay.bounds as LatLngBoundsExpression}
              opacity={cr.defaultOpacity ?? rasterOpacity}
              zIndex={350 + idx}
            />
          ) : null
        )}

        {/* Study Area Outline */}
        {showStudyArea && studyArea?.geometry && (
          <GeoJSON
            key="study-area-geom"
            data={studyArea.geometry as any}
            style={{
              color: "#5ec8e5",
              weight: 1.5,
              dashArray: "5 4",
              fillOpacity: 0.02,
            }}
          />
        )}

        {/* Watersheds */}
        {showWatersheds && watershedsGeoJSON && (
          <GeoJSON
            key="watersheds-geom"
            data={watershedsGeoJSON as any}
            style={{
              color: "#a78bfa",
              weight: 1.2,
              fillOpacity: 0.05 * vectorOpacity,
            }}
          />
        )}

        {/* Rivers / Streams */}
        {showRivers && riversGeoJSON && (
          <GeoJSON
            key="rivers-geom"
            data={riversGeoJSON as any}
            style={{
              color: "#38bdf8",
              weight: 1.8,
              opacity: vectorOpacity,
            }}
          />
        )}

        {/* Glacier Outlines */}
        {showGlaciers && glacierGeoJSON && (
          <GeoJSON
            key="glaciers-geom"
            data={glacierGeoJSON as any}
            style={{
              color: "#e0f2fe",
              weight: 1.5,
              fillColor: "#bae6fd",
              fillOpacity: 0.25 * vectorOpacity,
            }}
          />
        )}

        {/* Glacial Lakes & Susceptibility */}
        {(showLakes || showSusceptibility) &&
          lakesGeoJSON &&
          lakesGeoJSON.features?.length > 0 && (
            <GeoJSON
              key={`lakes-${yearFilter ?? "all"}-${showSusceptibility ? "susc" : "std"}-${selectedLakeId ?? "none"}`}
              data={lakesGeoJSON as any}
              style={(feature) => {
                const props = feature?.properties as LakeFeatureProperties | undefined;
                const isSelected =
                  selectedLakeId != null && props?.lake_id === selectedLakeId;
                const catColor =
                  showSusceptibility && props?.susceptibility_category
                    ? SUSCEPTIBILITY_COLORS[props.susceptibility_category] ||
                      "#5ec8e5"
                    : "#5ec8e5";
                return {
                  color: isSelected ? "#ffffff" : catColor,
                  weight: isSelected ? 2.5 : 1.8,
                  fillColor: catColor,
                  fillOpacity: 0.45 * vectorOpacity,
                };
              }}
              onEachFeature={(feature, layer) => {
                const p = feature.properties as LakeFeatureProperties;
                if (!p) return;
                layer.bindPopup(
                  `<div class="space-y-1">
                    <div class="font-semibold text-glacier-300">${p.name || "Glacial Lake"} (${p.lake_code || p.lake_id})</div>
                    <div>Area: <span class="font-mono">${p.area_ha?.toFixed(2) ?? "N/A"} ha</span></div>
                    <div>Elevation: <span class="font-mono">${p.elevation_m ? `${Math.round(p.elevation_m)} m` : "N/A"}</span></div>
                    <div>Year / Mission: <span class="font-mono">${p.year ?? "—"} (${p.mission ?? "—"})</span></div>
                    <div>Method: <span class="font-mono">${p.method ?? "—"}</span></div>
                    ${
                      p.susceptibility_category
                        ? `<div>Screening Category: <span class="font-semibold">${p.susceptibility_category}</span></div>`
                        : ""
                    }
                  </div>`
                );
                layer.on("click", () => {
                  if (onLakeSelect && p.lake_id !== undefined) {
                    onLakeSelect(p.lake_id);
                  }
                });
              }}
            />
          )}

        {/* Infrastructure (OSM) */}
        {showInfra && infraGeoJSON && (
          <GeoJSON
            key="infra-geom"
            data={infraGeoJSON as any}
            style={{
              color: "#f59e0b",
              weight: 1.5,
              opacity: vectorOpacity,
            }}
            pointToLayer={(feature, latlng) => {
              const L = (window as any).L;
              if (!L) return null as any;
              return L.circleMarker(latlng, {
                radius: 4,
                fillColor: "#fbbf24",
                color: "#0b1220",
                weight: 1,
                fillOpacity: 0.9,
              });
            }}
            onEachFeature={(feature, layer) => {
              const p = feature.properties || {};
              layer.bindPopup(
                `<div>
                  <div class="font-semibold text-amber-300">${p.name || p.category || "OSM Feature"}</div>
                  <div class="text-slate-400">Category: ${p.category || "unknown"}</div>
                  ${p.osm_id ? `<div class="text-slate-500 font-mono text-[10px]">OSM #${p.osm_id}</div>` : ""}
                </div>`
              );
            }}
          />
        )}

        {/* Custom Vectors from parent pages */}
        {customVectors.map((cv) =>
          !hiddenCustomIds[cv.id] && cv.data ? (
            <GeoJSON
              key={cv.id}
              data={cv.data as any}
              style={{
                color: cv.color || "#38bdf8",
                weight: cv.weight ?? 2,
                fillColor: cv.color || "#38bdf8",
                fillOpacity: (cv.fillOpacity ?? 0.25) * vectorOpacity,
              }}
            />
          ) : null
        )}

        {/* Reference Points */}
        {showRefPoints &&
          studyArea?.reference_points?.map((pt, i) => (
            <CircleMarker
              key={`${pt.name}-${i}`}
              center={[pt.lat, pt.lon]}
              radius={5}
              pathOptions={{
                color: "#0b1220",
                weight: 1.5,
                fillColor:
                  pt.type === "temple" || pt.type === "settlement"
                    ? "#facc15"
                    : pt.type === "glacier" || pt.type === "lake"
                    ? "#5ec8e5"
                    : "#4ade80",
                fillOpacity: 0.95,
              }}
            >
              <Popup>
                <div className="space-y-0.5">
                  <div className="font-semibold text-slate-100">{pt.name}</div>
                  <div className="text-[11px] text-slate-400 capitalize">
                    Type: {pt.type}
                  </div>
                  <div className="font-mono text-[10px] text-slate-400">
                    {pt.lat.toFixed(4)}°N, {pt.lon.toFixed(4)}°E
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>

      {/* Top-Left Search Box & Year Filter */}
      <div className="absolute top-3 left-12 z-[500] flex items-center gap-2">
        <div className="relative">
          <div className="flex items-center bg-ink-900/95 border border-white/15 rounded px-2.5 py-1 text-xs shadow-lg backdrop-blur">
            <Search className="w-3.5 h-3.5 text-slate-400 mr-1.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search Kedarnath, Chorabari, lakes..."
              className="bg-transparent text-slate-200 placeholder-slate-500 focus:outline-none w-48"
            />
          </div>
          {filteredPlaces.length > 0 && (
            <div className="absolute left-0 right-0 mt-1 bg-ink-900 border border-white/15 rounded shadow-xl max-h-48 overflow-y-auto divide-y divide-white/5">
              {filteredPlaces.map((pl, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setFlyTarget({ lat: pl.lat, lon: pl.lon, zoom: 14 });
                    setSearchQuery("");
                  }}
                  className="w-full text-left px-2.5 py-1.5 hover:bg-ink-800 flex items-center justify-between text-xs"
                >
                  <span className="text-slate-200 truncate">{pl.label}</span>
                  <span className="text-[10px] text-glacier-400 font-mono uppercase ml-2">
                    {pl.category}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {onYearFilterChange && (
          <div className="flex items-center gap-1.5 bg-ink-900/95 border border-white/15 rounded px-2 py-1 text-xs shadow-lg backdrop-blur">
            <span className="text-slate-400">Year:</span>
            <select
              value={yearFilter ?? ""}
              onChange={(e) =>
                onYearFilterChange(e.target.value ? Number(e.target.value) : null)
              }
              className="bg-transparent text-slate-200 font-mono focus:outline-none"
            >
              <option value="" className="bg-ink-900">
                All
              </option>
              {Array.from({ length: 27 }, (_, i) => 2000 + i).map((yr) => (
                <option key={yr} value={yr} className="bg-ink-900">
                  {yr}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Top-Right Layer Control Panel */}
      {showLayerControl && (
        <div className="absolute top-3 right-3 z-[500] w-64 bg-ink-900/95 border border-white/15 rounded shadow-xl backdrop-blur text-xs">
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            className="w-full flex items-center justify-between px-3 py-2 font-medium text-slate-200 border-b border-white/10 hover:bg-white/5"
          >
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-glacier-400" />
              <span>Map Layers & Basemap</span>
            </span>
            {panelOpen ? (
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            )}
          </button>

          {panelOpen && (
            <div className="p-2.5 space-y-3 max-h-[380px] overflow-y-auto">
              {/* Basemap selector */}
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Basemap
                </div>
                <div className="grid grid-cols-3 gap-1">
                  {(
                    [
                      ["satellite", "Esri Sat"],
                      ["topo", "OpenTopo"],
                      ["dark", "CARTO Dark"],
                    ] as const
                  ).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setBasemap(key)}
                      className={`px-2 py-1 rounded text-[11px] border ${
                        basemap === key
                          ? "bg-glacier-400/20 border-glacier-400 text-glacier-300 font-medium"
                          : "bg-ink-950 border-white/10 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Custom Layers passed from active view */}
              {(customRasters.length > 0 || customVectors.length > 0) && (
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Active View Overlays
                  </div>
                  <div className="space-y-1">
                    {customRasters.map((cr) => (
                      <div
                        key={cr.id}
                        className="flex items-center justify-between text-[11px] bg-ink-950/60 px-2 py-1 rounded"
                      >
                        <button
                          onClick={() =>
                            setHiddenCustomIds((p) => ({
                              ...p,
                              [cr.id]: !p[cr.id],
                            }))
                          }
                          className="flex items-center gap-1.5 text-slate-200 truncate"
                        >
                          {hiddenCustomIds[cr.id] ? (
                            <EyeOff className="w-3 h-3 text-slate-500 shrink-0" />
                          ) : (
                            <Eye className="w-3 h-3 text-glacier-400 shrink-0" />
                          )}
                          <span className="truncate">{cr.label}</span>
                        </button>
                        {cr.rasterId && (
                          <a
                            href={api.getRasterDownloadUrl(cr.rasterId)}
                            className="text-glacier-400 hover:text-glacier-300 ml-1"
                            title="Download GeoTIFF"
                          >
                            <Download className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    ))}
                    {customVectors.map((cv) => (
                      <div
                        key={cv.id}
                        className="flex items-center justify-between text-[11px] bg-ink-950/60 px-2 py-1 rounded"
                      >
                        <button
                          onClick={() =>
                            setHiddenCustomIds((p) => ({
                              ...p,
                              [cv.id]: !p[cv.id],
                            }))
                          }
                          className="flex items-center gap-1.5 text-slate-200 truncate"
                        >
                          {hiddenCustomIds[cv.id] ? (
                            <EyeOff className="w-3 h-3 text-slate-500 shrink-0" />
                          ) : (
                            <Eye className="w-3 h-3 text-glacier-400 shrink-0" />
                          )}
                          <span className="truncate">{cv.label}</span>
                        </button>
                        <button
                          onClick={() =>
                            exportGeoJSON(cv.data, `${cv.id}.geojson`)
                          }
                          className="text-glacier-400 hover:text-glacier-300 ml-1"
                          title="Export GeoJSON"
                        >
                          <Download className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Terrain Products */}
              {terrainSummary?.available &&
                Object.keys(terrainSummary.products || {}).length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                      Terrain Raster Product
                    </div>
                    <select
                      value={activeTerrainKey || ""}
                      onChange={(e) =>
                        setActiveTerrainKey(e.target.value || null)
                      }
                      className="w-full bg-ink-950 border border-white/10 rounded px-2 py-1 text-[11px] text-slate-200"
                    >
                      <option value="">None</option>
                      {Object.keys(terrainSummary.products).map((k) => (
                        <option key={k} value={k}>
                          {k.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

              {/* Standard Vector Layers */}
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                  Thematic Layers
                </div>
                <div className="space-y-1 text-[11px]">
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showStudyArea}
                        onChange={(e) => setShowStudyArea(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>Study Area Boundary</span>
                    </span>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showRefPoints}
                        onChange={(e) => setShowRefPoints(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>Reference Landmarks</span>
                    </span>
                  </label>
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={showLakes}
                        onChange={(e) => setShowLakes(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>Glacial Lakes</span>
                    </label>
                    {lakesGeoJSON && (
                      <button
                        onClick={() =>
                          exportGeoJSON(lakesGeoJSON, "glacial_lakes.geojson")
                        }
                        className="text-glacier-400 hover:text-glacier-300"
                        title="Download Lakes GeoJSON"
                      >
                        <Download className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showSusceptibility}
                        onChange={(e) => setShowSusceptibility(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>Colour Lakes by Susceptibility</span>
                    </span>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showGlaciers}
                        onChange={(e) => setShowGlaciers(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>Glacier Outlines</span>
                    </span>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showRivers}
                        onChange={(e) => setShowRivers(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>River Network</span>
                    </span>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showWatersheds}
                        onChange={(e) => setShowWatersheds(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>Watersheds</span>
                    </span>
                  </label>
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={showInfra}
                        onChange={(e) => setShowInfra(e.target.checked)}
                        className="accent-glacier-400"
                      />
                      <span>OSM Infrastructure</span>
                    </span>
                  </label>
                </div>
              </div>

              {/* Opacity Sliders */}
              <div className="space-y-1.5 pt-1 border-t border-white/10 text-[11px]">
                <div className="flex items-center justify-between text-slate-400">
                  <span>Raster Opacity</span>
                  <span className="font-mono">{Math.round(rasterOpacity * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={rasterOpacity}
                  onChange={(e) => setRasterOpacity(Number(e.target.value))}
                  className="w-full accent-glacier-400 cursor-pointer"
                />
                <div className="flex items-center justify-between text-slate-400">
                  <span>Vector Opacity</span>
                  <span className="font-mono">{Math.round(vectorOpacity * 100)}%</span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={vectorOpacity}
                  onChange={(e) => setVectorOpacity(Number(e.target.value))}
                  className="w-full accent-glacier-400 cursor-pointer"
                />
              </div>

              {/* Legend */}
              {showSusceptibility && (
                <div className="pt-1 border-t border-white/10">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
                    Susceptibility Classes
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[10px]">
                    {Object.entries(SUSCEPTIBILITY_COLORS).map(([cat, col]) => (
                      <div key={cat} className="flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-sm shrink-0"
                          style={{ backgroundColor: col }}
                        />
                        <span className="text-slate-300">{cat}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Bottom-Left Mouse Coordinates Bar */}
      <div className="pointer-events-none absolute bottom-2 left-2 z-[500] flex items-center gap-2 bg-ink-950/90 border border-white/10 rounded px-2 py-1 text-[11px] font-mono text-slate-300">
        <Compass className="w-3.5 h-3.5 text-glacier-400" />
        {mouseCoords ? (
          <span>
            {mouseCoords.lat.toFixed(5)}°N, {mouseCoords.lon.toFixed(5)}°E
          </span>
        ) : (
          <span className="text-slate-500">EPS:4326 • Hover map for coords</span>
        )}
      </div>
    </div>
  );
};
