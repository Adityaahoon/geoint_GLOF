"""Terrain & hydrology pipeline: DEM -> derivatives, streams, watersheds, HAND, flow paths."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import LineString, Point, mapping
from shapely.ops import unary_union

from ..config import get_settings
from ..study_area import REFERENCE_POINTS
from . import hydrology as hy
from .raster_service import register_raster, write_raster

settings = get_settings()
TERRAIN_DIR = settings.processed_dir / "terrain"


def latest_dem(db):
    from ..models import RasterAsset
    return db.query(RasterAsset).filter(RasterAsset.kind == "dem").order_by(RasterAsset.id.desc()).first()


def _upsert_vector_layer(db, key, name, category, path, n, source, params=None, attribution=None):
    from ..models import VectorLayer
    vl = db.query(VectorLayer).filter_by(key=key).first()
    if vl is None:
        vl = VectorLayer(key=key)
        db.add(vl)
    vl.name, vl.category, vl.path, vl.feature_count = name, category, str(path), n
    vl.source, vl.parameters, vl.attribution = source, params, attribution
    db.commit()
    return vl


def run_terrain_analysis(db, dem_asset, stream_threshold_km2: float = 1.0, log=lambda m, p=None: None) -> dict:
    from ..models import TerrainAnalysis
    TERRAIN_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dem_asset.path) as src:
        if not src.crs.is_projected:
            raise ValueError("Terrain analysis requires a projected DEM (UTM). Reproject first.")
        z = src.read(1, masked=True).astype("float64").filled(np.nan)
        transform, crs = src.transform, src.crs
        res = abs(src.res[0])
    cell_area = res * res
    log("Computing slope, aspect, hillshade, ruggedness", 0.05)
    slope, aspect = hy.slope_aspect(z, res)
    hs = hy.hillshade(z, res)
    tri = hy.terrain_ruggedness(z)
    log("Hydrological conditioning (Priority-Flood + ε)", 0.2)
    filled = hy.priority_flood_fill(z)
    fill_depth = (filled - z).astype("float32")
    log("D8 flow direction", 0.45)
    fdir = hy.d8_flow_direction(filled, res)
    log("Flow accumulation", 0.55)
    acc, order = hy.flow_accumulation(filled, fdir)
    thr_cells = stream_threshold_km2 * 1e6 / cell_area
    stream = acc >= thr_cells
    log("Strahler order & HAND", 0.7)
    sorder = hy.strahler_order(stream, fdir, order)
    hand_arr = hy.hand(filled, z, stream, fdir, order)
    np.save(TERRAIN_DIR / "fdir.npy", fdir)
    np.save(TERRAIN_DIR / "order.npy", order)

    src_note = dem_asset.source or "DEM"
    products = {}
    specs = [
        ("elevation", z.astype("float32"), "m"), ("slope", slope, "degrees"), ("aspect", aspect, "degrees"),
        ("hillshade", hs, "0-255"), ("roughness", tri, "m (TRI)"), ("filled_dem", filled.astype("float32"), "m"),
        ("fill_depth", fill_depth, "m"), ("flow_direction", hy.esri_codes(fdir), "ESRI D8 code"),
        ("flow_accumulation", (acc * cell_area / 1e6).astype("float32"), "km² contributing area"),
        ("stream_order", np.where(stream, sorder, np.nan).astype("float32"), "Strahler"),
        ("hand", hand_arr, "m above nearest drainage"),
    ]
    for name, arr, unit in specs:
        p = TERRAIN_DIR / f"{name}.tif"
        write_raster(p, arr, transform, crs, band_names=[name], tags={"unit": unit, "dem": dem_asset.path})
        a = register_raster(db, p, name=f"{name.replace('_', ' ').title()} ({unit})", kind="terrain", category=name,
                            parent_id=dem_asset.id, source=src_note,
                            processing={"product": name, "unit": unit, "resolution_m": res,
                                        "stream_threshold_km2": stream_threshold_km2})
        products[name] = a.id
    log("Vectorising stream network", 0.8)
    lines = hy.streams_to_lines(stream, fdir, sorder, transform)
    feats = [{"geometry": hy.to_wgs84(l["geometry"], crs), "strahler": l["strahler"],
              "length_m": round(l["length_m"], 1)} for l in lines]
    p = hy.write_geojson(TERRAIN_DIR / "streams.geojson", feats)
    _upsert_vector_layer(db, "streams", "Drainage network (DEM-derived, D8)", "hydrology", p, len(feats), src_note,
                         {"threshold_km2": stream_threshold_km2, "method": "D8 on Priority-Flood conditioned DEM"})

    log("Delineating watersheds", 0.88)
    rows, cols = z.shape
    inv = ~transform
    ws_feats = []
    # main AOI outlet = cell with largest accumulation
    k = int(np.nanargmax(acc))
    outlets = [{"name": "AOI main outlet", "rc": (k // cols, k % cols)}]
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    for rp in REFERENCE_POINTS:
        if rp["type"] != "settlement":
            continue
        x, y = t.transform(rp["lon"], rp["lat"])
        c, r = inv * (x, y)
        r, c = int(r), int(c)
        if 0 <= r < rows and 0 <= c < cols:
            outlets.append({"name": f"Upstream of {rp['name']}", "rc": hy.snap_pour_point(acc, r, c, radius=6)})
    for o in outlets:
        r, c = o["rc"]
        m = hy.upstream_mask(fdir, r * cols + c, order)
        polys = hy.polygonize_mask(m, transform)
        if not polys:
            continue
        g = unary_union(polys)
        ws_feats.append({"geometry": hy.to_wgs84(g, crs), "name": o["name"], "area_km2": round(g.area / 1e6, 2),
                         "outlet_elev_m": round(float(z[r, c]), 1)})
    p = hy.write_geojson(TERRAIN_DIR / "watersheds.geojson", ws_feats)
    _upsert_vector_layer(db, "watersheds", "Watersheds (DEM-derived)", "hydrology", p, len(ws_feats), src_note,
                         {"method": "D8 upstream tracing from snapped pour points"})

    valid = np.isfinite(z)
    stats = {
        "elevation_m": {"min": float(np.nanmin(z)), "max": float(np.nanmax(z)), "mean": float(np.nanmean(z))},
        "slope_deg": {"mean": float(np.nanmean(slope)), "p90": float(np.nanpercentile(slope, 90)),
                      "area_gt_30deg_km2": float(((slope > 30) & valid).sum() * cell_area / 1e6)},
        "max_contributing_area_km2": float(np.nanmax(acc) * cell_area / 1e6),
        "stream_length_km": round(sum(f["length_m"] for f in feats) / 1000, 2),
        "max_strahler_order": int(sorder.max()),
        "filled_cells_fraction": float((fill_depth > 0.01).mean()),
        "resolution_m": res, "watersheds": [{k: v for k, v in w.items() if k != "geometry"} for w in ws_feats],
    }
    ta = TerrainAnalysis(dem_source=src_note[:128], dem_asset_id=dem_asset.id, products=products, statistics=stats,
                         parameters={"stream_threshold_km2": stream_threshold_km2, "fill": "priority-flood-epsilon",
                                     "flow": "D8", "slope": "Horn 1981"})
    db.add(ta)
    db.commit()
    log("Terrain analysis complete", 1.0)
    return {"terrain_analysis_id": ta.id, "products": products, "statistics": stats}


def flow_path_from_point(db, lon: float, lat: float, name: str = "flow path", max_length_km: float | None = None) -> dict:
    """Steepest-descent (D8) flow path from a point, e.g. a lake outlet. Pure terrain routing:
    it indicates the likely flow corridor, NOT flood extent, depth or velocity."""
    from ..models import RasterAsset
    dem = db.query(RasterAsset).filter_by(kind="terrain", category="elevation").order_by(RasterAsset.id.desc()).first()
    if dem is None or not (TERRAIN_DIR / "fdir.npy").exists():
        raise RuntimeError("Run terrain analysis first (/api/terrain/analyse)")
    fdir = np.load(TERRAIN_DIR / "fdir.npy")
    with rasterio.open(dem.path) as src:
        z = src.read(1)
        transform, crs = src.transform, src.crs
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(lon, lat)
    c, r = ~transform * (x, y)
    r, c = int(r), int(c)
    if not (0 <= r < z.shape[0] and 0 <= c < z.shape[1]):
        raise ValueError("Point is outside the DEM extent")
    cells = hy.trace_flow_path(fdir, (r, c))
    pts = [transform * (cc + 0.5, rr + 0.5) for rr, cc in cells]
    profile, dist = [], 0.0
    for i, (rr, cc) in enumerate(cells):
        if i:
            dist += float(np.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
        if max_length_km and dist / 1000 > max_length_km:
            pts = pts[:i]
            break
        profile.append({"distance_m": round(dist, 1), "elevation_m": round(float(z[rr, cc]), 1)})
    line = LineString(pts) if len(pts) > 1 else Point(pts[0])
    return {"name": name, "geometry": mapping(hy.to_wgs84(line, crs)), "length_m": round(dist, 1),
            "elevation_drop_m": round(profile[0]["elevation_m"] - profile[-1]["elevation_m"], 1) if profile else 0,
            "profile": profile[:: max(1, len(profile) // 300)],
            "method": "D8 steepest descent on hydrologically conditioned Copernicus GLO-30",
            "caveat": "Indicates the terrain-controlled flow corridor only. Flood depth, velocity and extent "
                      "require hydraulic modelling (HEC-RAS 2D) with a defensible inflow hydrograph."}

