"""Historical environmental change detection (2000–2026) and 2013 disaster impact analysis.

Computes annual indicator series from seasonal-window composites and generates paired
difference + transition rasters for any two years (including the 6 standard comparisons:
2000v2012, 2012v2013, 2013v2015, 2015v2020, 2020v2024, 2024v2026-YTD).

Every comparison records sensor differences, spatial resolution differences, and data-quality
flags so users can separate observed environmental changes from sensor/seasonal artefacts.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.mask import mask as rio_mask
from rasterio.warp import reproject, transform_geom
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

from ..config import get_settings
from ..models import AnnualIndicator, ChangeDetectionResult, GlacierBoundary, RasterAsset
from ..study_area import DISASTER_CONTEXT, REFERENCE_POINTS, region_geometry
from . import hydrology as hy
from .indices import mndwi, nbr, ndsi, ndvi, ndwi, snow_indices
from .raster_service import register_raster, write_raster
from .sensors import SENSORS

settings = get_settings()
CHANGE_DIR = settings.processed_dir / "change"

INDICATOR_METADATA = {
    "water_area_ha": {"unit": "ha", "description": "Surface water area (MNDWI > 0.05, NIR < 0.22)"},
    "snow_ice_area_ha": {"unit": "ha", "description": "Snow & glacier ice cover area (NDSI > 0.40, NIR > 0.11)"},
    "ndvi_mean": {"unit": "index", "description": "Mean Normalized Difference Vegetation Index"},
    "vegetated_area_ha": {"unit": "ha", "description": "Vegetated area (NDVI > 0.25)"},
    "exposed_ground_area_ha": {"unit": "ha", "description": "Bare rock / debris / sediment area (|NDVI|<0.15, NDSI<0.2, MNDWI<0)"},
    "mndwi_mean": {"unit": "index", "description": "Mean Modified Normalized Difference Water Index"},
}


def compute_indicators_for_composite(db, comp: RasterAsset, regions: tuple[str, ...] = ("full_aoi", "chorabari", "kedarnath_valley", "mandakini_corridor")) -> list[dict]:
    """Compute and store all annual environmental indicators for a composite across study sub-regions."""
    if not Path(comp.path).exists():
        return []
    proc = comp.processing or {}
    mission = proc.get("mission", "landsat8")
    year = comp.year or datetime.utcnow().year
    qflags = list(proc.get("quality_flags") or [])
    scene_count = proc.get("scene_count", 1)
    scenes = proc.get("scenes") or []
    scene_dates = [s.get("datetime", "")[:10] for s in scenes if isinstance(s, dict)]

    results = []
    with rasterio.open(comp.path) as src:
        names = [d or f"b{i}" for i, d in enumerate(src.descriptions, 1)]
        for reg in regions:
            geom_wgs = region_geometry(reg)
            geom_proj = transform_geom("EPSG:4326", src.crs, geom_wgs)
            try:
                data, _ = rio_mask(src, [geom_proj], crop=True, nodata=np.nan, filled=True)
            except ValueError:
                continue
            bmap = {names[i]: data[i].astype("float32") for i in range(len(names))}
            if "green" not in bmap or "swir1" not in bmap:
                continue
            valid = np.isfinite(bmap["green"]) & np.isfinite(bmap["nir"]) & np.isfinite(bmap["swir1"])
            vf = float(valid.mean()) if valid.size else 0.0
            if vf == 0.0:
                continue
            cell_ha = (abs(src.res[0]) * abs(src.res[1])) / 1e4
            scale_factor = 1.0 / max(vf, 0.25) if vf < 0.95 else 1.0  # raw observed area is stored; valid_pixel_fraction is reported alongside

            m_arr = mndwi(bmap["green"], bmap["swir1"])
            v_arr = ndvi(bmap["nir"], bmap["red"])
            sn = snow_indices(bmap)
            ndsi_arr = sn["ndsi"]

            water_mask = valid & (m_arr > 0.05) & (bmap["nir"] < 0.22) & (bmap["blue"] > 0.01)
            snow_mask = valid & (sn["snow_ice_mask"] > 0.5)
            veg_mask = valid & (v_arr > 0.25) & (~snow_mask) & (~water_mask)
            bare_mask = valid & (v_arr >= -0.05) & (v_arr <= 0.15) & (ndsi_arr < 0.20) & (m_arr < 0.0)

            vals = {
                "water_area_ha": round(float(water_mask.sum() * cell_ha), 2),
                "snow_ice_area_ha": round(float(snow_mask.sum() * cell_ha), 2),
                "ndvi_mean": round(float(np.nanmean(v_arr[valid])), 4),
                "vegetated_area_ha": round(float(veg_mask.sum() * cell_ha), 2),
                "exposed_ground_area_ha": round(float(bare_mask.sum() * cell_ha), 2),
                "mndwi_mean": round(float(np.nanmean(m_arr[valid])), 4),
            }

            for ind_name, val in vals.items():
                row = (
                    db.query(AnnualIndicator)
                    .filter_by(year=year, mission=mission, region=reg, indicator=ind_name)
                    .first()
                )
                if row is None:
                    row = AnnualIndicator(year=year, mission=mission, region=reg, indicator=ind_name)
                    db.add(row)
                row.value = val
                row.unit = INDICATOR_METADATA[ind_name]["unit"]
                row.valid_pixel_fraction = round(vf, 4)
                row.scene_count = scene_count
                row.window_start = comp.acquired_start
                row.window_end = comp.acquired_end
                row.scene_dates = scene_dates
                row.quality_flags = qflags
                row.raster_asset_id = comp.id
                row.parameters = {"scale_factor_note": scale_factor, "resolution_m": abs(src.res[0])}
                results.append({"year": year, "mission": mission, "region": reg, "indicator": ind_name, "value": val})

            # Also persist vector snow/glacier outline for chorabari region
            if reg == "chorabari" and snow_mask.any():
                _update_glacier_outline(db, comp, reg, snow_mask)

    db.commit()
    return results


def _update_glacier_outline(db, comp: RasterAsset, region: str, _unused_mask) -> None:
    """Extract NDSI snow/ice boundary inside the Chorabari zone in UTM and store in GlacierBoundary."""
    with rasterio.open(comp.path) as src:
        geom_proj = transform_geom("EPSG:4326", src.crs, region_geometry(region))
        data, m_transform = rio_mask(src, [geom_proj], crop=True, nodata=np.nan, filled=True)
        names = [d or f"b{i}" for i, d in enumerate(src.descriptions, 1)]
        bmap = {names[i]: data[i].astype("float32") for i in range(len(names))}
        sn = snow_indices(bmap)
        mask = np.isfinite(sn["snow_ice_mask"]) & (sn["snow_ice_mask"] > 0.5)
        polys = hy.polygonize_mask(mask, m_transform, min_area_m2=50_000)  # >= 5 ha
        if not polys:
            return
        from shapely.ops import unary_union
        from shapely.geometry import MultiPolygon, Polygon
        u = unary_union(polys)
        if isinstance(u, Polygon):
            u = MultiPolygon([u])
        area_km2 = round(float(u.area / 1e6), 3)
        wgs = hy.to_wgs84(u, src.crs)
        proc = comp.processing or {}
        mission = proc.get("mission", "optical")
        gb = db.query(GlacierBoundary).filter_by(glacier_name="Chorabari snow & ice extent", year=comp.year).first()
        if gb is None:
            gb = GlacierBoundary(glacier_name="Chorabari snow & ice extent", year=comp.year)
            db.add(gb)
        gb.source = f"Optical NDSI>0.40 & NIR>0.11 ({mission}, post-monsoon composite)"
        gb.area_km2 = area_km2
        gb.geometry = mapping(wgs)
        gb.attributes = {
            "composite_id": comp.id,
            "mission": mission,
            "caveat": "Optical NDSI maps combined clean glacier ice + seasonal/perennial snowpack; debris-covered glacier tongues (such as lower Chorabari snout) have rock-like spectral signatures and require SAR coherence or manual/RGI outlines to separate from surrounding moraine.",
        }


def _best_composite_for_year(db, year: int, region: str = "full_aoi") -> RasterAsset | None:
    q = db.query(RasterAsset).filter_by(kind="composite", year=year)
    comps = q.order_by(RasterAsset.id.desc()).all()
    if not comps:
        return None
    for c in comps:
        if (c.processing or {}).get("region") == region and Path(c.path).exists():
            return c
    for c in comps:
        if Path(c.path).exists():
            return c
    return None


def _compute_surface_grid(comp: RasterAsset, indicator: str, dst_transform, dst_w: int, dst_h: int, dst_crs) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (continuous_index, binary_target_mask, threshold) warped onto dst grid."""
    with rasterio.open(comp.path) as src:
        names = [d or f"b{i}" for i, d in enumerate(src.descriptions, 1)]
        bmap = {}
        for i, n in enumerate(names, 1):
            if n not in ("blue", "green", "red", "nir", "swir1", "swir2"):
                continue
            arr = np.full((dst_h, dst_w), np.nan, dtype="float32")
            reproject(
                rasterio.band(src, i), arr,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=dst_transform, dst_crs=dst_crs,
                resampling=Resampling.bilinear, src_nodata=src.nodata, dst_nodata=np.nan
            )
            bmap[n] = arr

    valid = np.isfinite(bmap["green"]) & np.isfinite(bmap["nir"]) & np.isfinite(bmap["swir1"])
    if indicator in ("water", "mndwi"):
        idx = mndwi(bmap["green"], bmap["swir1"])
        thr = 0.05
        mask = valid & (idx > thr) & (bmap["nir"] < 0.22)
    elif indicator in ("vegetation", "ndvi"):
        idx = ndvi(bmap["nir"], bmap["red"])
        thr = 0.25
        mask = valid & (idx > thr)
    elif indicator in ("snow_ice", "ndsi"):
        idx = ndsi(bmap["green"], bmap["swir1"])
        thr = 0.40
        mask = valid & (idx > thr) & (bmap["nir"] > 0.11)
    elif indicator in ("exposed_ground", "nbr"):
        v = ndvi(bmap["nir"], bmap["red"])
        s = ndsi(bmap["green"], bmap["swir1"])
        m = mndwi(bmap["green"], bmap["swir1"])
        idx = nbr(bmap["nir"], bmap["swir2"])
        thr = 0.10
        mask = valid & (v >= -0.05) & (v <= 0.15) & (s < 0.20) & (m < 0.0)
    else:
        idx = ndwi(bmap["green"], bmap["nir"])
        thr = 0.05
        mask = valid & (idx > thr)
    return idx, mask, thr


def analyse_pair(db, year_a: int, year_b: int, indicator: str = "water", region: str = "full_aoi") -> dict:
    CHANGE_DIR.mkdir(parents=True, exist_ok=True)
    comp_a = _best_composite_for_year(db, year_a, region)
    comp_b = _best_composite_for_year(db, year_b, region)
    if comp_a is None or comp_b is None:
        missing = [y for y, c in ((year_a, comp_a), (year_b, comp_b)) if c is None]
        raise ValueError(
            f"Composite raster not yet built for year(s) {missing}. "
            f"Build the annual composites first via Satellite Explorer or /api/satellite/composite."
        )

    from .raster_service import aoi_grid
    res = max(comp_a.resolution_x or 30.0, comp_b.resolution_x or 30.0, 30.0)
    transform, w, h, crs = aoi_grid(region, res)

    idx_a, mask_a, thr = _compute_surface_grid(comp_a, indicator, transform, w, h, crs)
    idx_b, mask_b, _ = _compute_surface_grid(comp_b, indicator, transform, w, h, crs)

    joint_valid = np.isfinite(idx_a) & np.isfinite(idx_b)
    diff = np.where(joint_valid, idx_b - idx_a, np.nan).astype("float32")
    # Transition classes: 0 = stable non-target, 1 = stable target, 2 = gain, 3 = loss
    trans = np.full((h, w), np.nan, dtype="float32")
    trans[joint_valid & (~mask_a) & (~mask_b)] = 0.0
    trans[joint_valid & mask_a & mask_b] = 1.0
    trans[joint_valid & (~mask_a) & mask_b] = 2.0
    trans[joint_valid & mask_a & (~mask_b)] = 3.0

    cell_ha = (res * res) / 1e4
    stable_ha = float((trans == 1.0).sum() * cell_ha)
    gain_ha = float((trans == 2.0).sum() * cell_ha)
    loss_ha = float((trans == 3.0).sum() * cell_ha)
    area_a_ha = stable_ha + loss_ha
    area_b_ha = stable_ha + gain_ha

    mission_a = (comp_a.processing or {}).get("mission", "unknown")
    mission_b = (comp_b.processing or {}).get("mission", "unknown")
    caveats = []
    if mission_a != mission_b:
        caveats.append(
            f"Cross-sensor comparison ({SENSORS.get(mission_a, SENSORS['landsat8']).label} in {year_a} vs "
            f"{SENSORS.get(mission_b, SENSORS['landsat8']).label} in {year_b}): bandpass and native resolution differences "
            f"have been harmonised to a common {int(res)} m UTM grid, but small spectral index shifts (±0.02–0.04) may reflect sensor response."
        )
    for y, c in ((year_a, comp_a), (year_b, comp_b)):
        fl = (c.processing or {}).get("quality_flags") or []
        if "landsat7_slc_off_gaps" in fl:
            caveats.append(f"{y} composite uses Landsat 7 ETM+ SLC-off data; un-filled gap pixels are masked out of the joint change comparison.")
        if "year_to_date" in fl:
            caveats.append(f"{y} is a year-to-date observation window, not a completed annual cycle.")
    joint_vf = float(joint_valid.mean())
    if joint_vf < 0.85:
        caveats.append(f"Joint valid (cloud- & gap-free in both years) coverage is {joint_vf:.1%} of the region; area changes apply strictly to this jointly observed footprint.")

    diff_path = CHANGE_DIR / f"diff_{region}_{indicator}_{year_a}_{year_b}.tif"
    trans_path = CHANGE_DIR / f"trans_{region}_{indicator}_{year_a}_{year_b}.tif"
    write_raster(diff_path, diff, transform, crs, band_names=[f"{indicator}_diff_{year_b}_minus_{year_a}"])
    write_raster(trans_path, trans, transform, crs, band_names=[f"{indicator}_transition"])

    diff_asset = register_raster(
        db, diff_path,
        name=f"{indicator.title()} difference ({year_b} − {year_a})",
        kind="change", category="difference", parent_id=comp_b.id, year=year_b,
        source=f"{comp_a.name} vs {comp_b.name}",
        processing={"indicator": indicator, "year_a": year_a, "year_b": year_b, "region": region}
    )
    trans_asset = register_raster(
        db, trans_path,
        name=f"{indicator.title()} transition ({year_a} → {year_b})",
        kind="change", category="transition", parent_id=comp_b.id, year=year_b,
        source=f"{comp_a.name} vs {comp_b.name}",
        processing={"indicator": indicator, "year_a": year_a, "year_b": year_b, "region": region,
                    "classes": {"0": "Stable non-target", "1": "Stable target", "2": "Gain / expansion", "3": "Loss / contraction"}}
    )

    stats = {
        "area_a_ha": round(area_a_ha, 2),
        "area_b_ha": round(area_b_ha, 2),
        "stable_ha": round(stable_ha, 2),
        "area_gain_ha": round(gain_ha, 2),
        "area_loss_ha": round(loss_ha, 2),
        "net_change_ha": round(gain_ha - loss_ha, 2),
        "mean_difference": round(float(np.nanmean(diff)), 4) if joint_valid.any() else None,
        "std_difference": round(float(np.nanstd(diff)), 4) if joint_valid.any() else None,
        "joint_valid_fraction": round(joint_vf, 4),
        "threshold": thr,
        "resolution_m": res,
    }

    row = ChangeDetectionResult(
        indicator=indicator, year_a=year_a, year_b=year_b,
        mission_a=mission_a, mission_b=mission_b, region=region,
        statistics=stats, caveats=caveats, raster_asset_id=diff_asset.id
    )
    db.add(row)
    db.commit()
    return {
        "id": row.id,
        "year_a": year_a,
        "year_b": year_b,
        "mission_a": mission_a,
        "mission_b": mission_b,
        "indicator": indicator,
        "region": region,
        "statistics": stats,
        "caveats": caveats,
        "rasters": {
            "difference": diff_asset,
            "transition": trans_asset,
            "before": comp_a,
            "after": comp_b,
        },
        "legend": {
            "classes": [
                {"value": 1, "label": "Stable", "color": "#38bdf8"},
                {"value": 2, "label": "Gain / Expansion", "color": "#22c55e"},
                {"value": 3, "label": "Loss / Contraction", "color": "#ef4444"},
            ]
        },
    }


def compare_2013_disaster(db, pre_year: int = 2011, post_year: int = 2013, region: str = "mandakini_corridor") -> dict:
    """Multi-indicator pre- vs post-June 2013 Kedarnath disaster analysis."""
    veg = analyse_pair(db, pre_year, post_year, indicator="vegetation", region=region)
    bare = analyse_pair(db, pre_year, post_year, indicator="exposed_ground", region=region)
    water = analyse_pair(db, pre_year, post_year, indicator="water", region=region)

    # Sample NDVI & NBR change in a 350 m window around each reference settlement/site
    comp_a = veg["rasters"]["before"]
    comp_b = veg["rasters"]["after"]
    affected = []
    with rasterio.open( veg["rasters"]["difference"].path ) as src_vd, rasterio.open( bare["rasters"]["difference"].path ) as src_bd:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", src_vd.crs, always_xy=True)
        for rp in REFERENCE_POINTS:
            x, y = t.transform(rp["lon"], rp["lat"])
            c, r = ~src_vd.transform * (x, y)
            r, c = int(round(r)), int(round(c))
            rad = 8  # ~240 m radius at 30 m
            r0, r1 = max(0, r - rad), min(src_vd.height, r + rad + 1)
            c0, c1 = max(0, c - rad), min(src_vd.width, c + rad + 1)
            if r1 <= r0 or c1 <= c0:
                continue
            vd = src_vd.read(1, window=rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0))
            bd = src_bd.read(1, window=rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0))
            m_ndvi = float(np.nanmean(vd)) if np.isfinite(vd).any() else None
            m_nbr = float(np.nanmean(bd)) if np.isfinite(bd).any() else None
            affected.append({
                "name": rp["name"],
                "type": rp["type"],
                "lat": rp["lat"],
                "lon": rp["lon"],
                "mean_ndvi_change": round(m_ndvi, 4) if m_ndvi is not None else None,
                "mean_nbr_change": round(m_nbr, 4) if m_nbr is not None else None,
                "change_summary": (
                    f"Mean ΔNDVI = {m_ndvi:+.3f}, ΔNBR = {m_nbr:+.3f} within ~240 m radius "
                    f"(negative values indicate vegetation stripping / fresh sediment or debris deposition)."
                    if m_ndvi is not None and m_nbr is not None else "Outside composite footprint"
                ),
            })

    caveats = list(dict.fromkeys(
        veg["caveats"] + [
            DISASTER_CONTEXT,
            "Optical satellite change maps document where vegetation loss, channel widening and sediment/debris deposition occurred between acquisitions, but cannot by themselves isolate the exact physical trigger (GLOF wave vs rainfall-runoff flash flood vs local hillslope debris flow) at each pixel.",
        ]
    ))

    return {
        "pre_year": pre_year,
        "post_year": post_year,
        "region": region,
        "context": DISASTER_CONTEXT,
        "primary": veg,
        "indicators": {
            "vegetation": veg["statistics"],
            "exposed_ground": bare["statistics"],
            "water": water["statistics"],
        },
        "rasters": {
            "before": comp_a,
            "after": comp_b,
            "ndvi_difference": veg["rasters"]["difference"],
            "ndvi_transition": veg["rasters"]["transition"],
            "exposed_transition": bare["rasters"]["transition"],
            "water_transition": water["rasters"]["transition"],
        },
        "affected_locations": affected,
        "caveats": caveats,
    }
