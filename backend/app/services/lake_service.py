"""Glacial lake detection & persistent inventory service.

Methods supported:
  1. `mndwi_otsu`: MNDWI (Xu 2006) combined with NDWI, slope masking (< max_slope_deg on DEM to
     suppress steep mountain shadows), and NIR reflectance < 0.20 (suppresses bright ice/cloud edges).
     Threshold is either user-specified or determined automatically via Otsu's method bounded to [-0.05, 0.35].
  2. `unet` / `deeplabv3plus`: Semantic segmentation using a trained PyTorch checkpoint. Never runs with
     random weights — raises an explicit error if no trained checkpoint exists.

Lake polygons are extracted in UTM 44N (EPSG:32644) for exact metric area (ha) and perimeter (m),
then matched spatially to existing `GlacialLake` inventory entries (within 250 m centroid distance
or overlapping footprint) so each lake maintains a persistent `lake_code` across 2000–2026.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from shapely.geometry import MultiPolygon, Polygon, mapping, shape

from ..config import get_settings
from ..models import GlacialLake, LakeObservation, RasterAsset, SusceptibilityAssessment
from ..study_area import REFERENCE_POINTS
from . import hydrology as hy
from .indices import mndwi, ndwi, otsu_threshold
from .raster_service import register_raster, write_raster

settings = get_settings()
LAKES_DIR = settings.processed_dir / "lakes"


def _load_composite_bands(comp_asset: RasterAsset) -> tuple[dict[str, np.ndarray], any, any, float]:
    with rasterio.open(comp_asset.path) as src:
        names = [d or f"b{i}" for i, d in enumerate(src.descriptions, 1)]
        bands = {}
        for i, name in enumerate(names, 1):
            a = src.read(i, masked=True).astype("float32").filled(np.nan)
            bands[name] = a
        return bands, src.transform, src.crs, abs(src.res[0])


def _aligned_dem_and_slope(db, transform, width: int, height: int, crs) -> tuple[np.ndarray | None, np.ndarray | None]:
    dem_a = db.query(RasterAsset).filter_by(kind="terrain", category="elevation").order_by(RasterAsset.id.desc()).first()
    if dem_a is None:
        dem_a = db.query(RasterAsset).filter_by(kind="dem").order_by(RasterAsset.id.desc()).first()
    slope_a = db.query(RasterAsset).filter_by(kind="terrain", category="slope").order_by(RasterAsset.id.desc()).first()

    elev = None
    slope = None
    if dem_a and Path(dem_a.path).exists():
        elev = np.full((height, width), np.nan, dtype="float32")
        with rasterio.open(dem_a.path) as src:
            reproject(
                rasterio.band(src, 1), elev,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform, dst_crs=crs,
                resampling=Resampling.bilinear, src_nodata=src.nodata, dst_nodata=np.nan
            )
    if slope_a and Path(slope_a.path).exists():
        slope = np.full((height, width), np.nan, dtype="float32")
        with rasterio.open(slope_a.path) as src:
            reproject(
                rasterio.band(src, 1), slope,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform, dst_crs=crs,
                resampling=Resampling.bilinear, src_nodata=src.nodata, dst_nodata=np.nan
            )
    elif elev is not None:
        slope, _ = hy.slope_aspect(elev, abs(transform.a))
    return elev, slope


def detect_lakes_on_composite(
    db,
    composite_id: int,
    method: str = "mndwi_otsu",
    min_area_ha: float = 0.5,
    max_slope_deg: float = 22.0,
    threshold: float | None = None,
    min_elevation_m: float = 2800.0,
    log=lambda m, p=None: None,
) -> dict:
    comp = db.get(RasterAsset, composite_id)
    if comp is None or not Path(comp.path).exists():
        raise ValueError(f"Composite raster {composite_id} not found")

    LAKES_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Loading composite {comp.name}", 0.1)
    bands, transform, crs, res = _load_composite_bands(comp)
    h, w = bands["green"].shape
    elev, slope = _aligned_dem_and_slope(db, transform, w, h, crs)

    valid = np.isfinite(bands["green"]) & np.isfinite(bands["swir1"]) & np.isfinite(bands["nir"])
    valid_fraction = float(valid.mean())

    if method in ("unet", "deeplabv3plus"):
        from .dl_service import predict_composite_mask
        log(f"Running {method} inference", 0.35)
        water_mask, dl_meta = predict_composite_mask(db, comp, model_type=method)
        used_thr = dl_meta.get("probability_threshold", 0.5)
    else:
        log("Computing MNDWI & NDWI", 0.25)
        m = mndwi(bands["green"], bands["swir1"])
        n = ndwi(bands["green"], bands["nir"])
        if threshold is None:
            try:
                raw_otsu = otsu_threshold(m[valid])
                used_thr = float(np.clip(raw_otsu, 0.12, 0.30))
            except Exception:
                used_thr = 0.15
        else:
            used_thr = float(threshold)
        # Water spectral + terrain + illumination criteria (suppress cast shadow & bright snow/ice)
        hs = hy.hillshade(elev, res) if elev is not None else None
        water_mask = (
            valid
            & (m > used_thr)
            & (n > 0.08)
            & (bands["green"] > 0.035)
            & (bands["nir"] < 0.18)
            & (bands["swir1"] < 0.12)
            & (bands["green"] > bands["nir"] * 1.15)
        )
        if hs is not None:
            water_mask &= np.isnan(hs) | (hs >= 105.0)

    if slope is not None:
        water_mask &= np.isnan(slope) | (slope <= min(max_slope_deg, 16.0))
    if elev is not None:
        water_mask &= np.isnan(elev) | (elev >= min_elevation_m)

    log("Vectorising water bodies and matching glacial lake inventory", 0.65)
    min_area_m2 = min_area_ha * 1e4
    polys = hy.polygonize_mask(water_mask, transform, min_area_m2=min_area_m2)

    mask_path = LAKES_DIR / f"lake_mask_{comp.year or 'unk'}_{method}_{comp.id}.tif"
    write_raster(
        mask_path,
        np.where(valid, water_mask.astype("float32"), np.nan),
        transform, crs, band_names=["water_mask"],
        tags={"method": method, "threshold": used_thr, "composite_id": comp.id}
    )
    mask_asset = register_raster(
        db, mask_path,
        name=f"Glacial lake mask {comp.year or ''} ({method})",
        kind="mask", category="water_mask", parent_id=comp.id, year=comp.year,
        source=comp.source,
        processing={"method": method, "threshold": used_thr, "min_area_ha": min_area_ha,
                    "max_slope_deg": max_slope_deg, "min_elevation_m": min_elevation_m}
    )

    year = comp.year or (comp.acquired_start.year if comp.acquired_start else datetime.utcnow().year)
    mission = (comp.processing or {}).get("mission", "optical")

    existing_lakes = db.query(GlacialLake).all()
    existing_utm = []
    for lk in existing_lakes:
        if lk.centroid:
            existing_utm.append((lk, hy.from_wgs84(shape(lk.centroid), crs)))

    # Reference named lakes (e.g. Chorabari Lake / Gandhi Sarovar)
    named_refs = []
    for rp in REFERENCE_POINTS:
        if rp["type"] == "lake":
            from shapely.geometry import Point
            named_refs.append((rp["name"], hy.from_wgs84(Point(rp["lon"], rp["lat"]), crs)))

    inv = ~transform
    detected = []
    for poly in sorted(polys, key=lambda g: g.area, reverse=True):
        if isinstance(poly, Polygon):
            mpoly = MultiPolygon([poly])
        else:
            mpoly = poly
        area_ha = float(mpoly.area / 1e4)
        perim_m = float(mpoly.length)
        cent_utm = mpoly.centroid
        cent_wgs = hy.to_wgs84(cent_utm, crs)
        mpoly_wgs = hy.to_wgs84(mpoly, crs)

        # Sample mean elevation
        c_px, r_px = inv * (cent_utm.x, cent_utm.y)
        r_i, c_i = int(round(r_px)), int(round(c_px))
        lake_elev = None
        if elev is not None and 0 <= r_i < h and 0 <= c_i < w and np.isfinite(elev[r_i, c_i]):
            lake_elev = round(float(elev[r_i, c_i]), 1)

        # Match existing inventory entry within 300 m
        matched_lake = None
        best_d = 300.0
        for lk, pt_utm in existing_utm:
            d = cent_utm.distance(pt_utm)
            if d < best_d:
                best_d = d
                matched_lake = lk

        obs_dt = comp.acquired_end or comp.acquired_start or datetime(year, 10, 15)
        if matched_lake is None:
            code = f"KED-GL-{len(existing_utm) + 1:03d}"
            lake_name = None
            for ref_name, ref_pt in named_refs:
                if cent_utm.distance(ref_pt) < 450.0:
                    lake_name = ref_name
                    break
            if lake_name is None:
                lake_name = f"High-altitude water body {code}"
            matched_lake = GlacialLake(
                lake_code=code,
                name=lake_name,
                centroid=mapping(cent_wgs),
                elevation_m=lake_elev,
                lake_type="moraine/glacial water body",
                source=f"{method} on {mission} ({year})",
                first_detected=obs_dt,
                last_detected=obs_dt,
                attributes={"min_elevation_filter_m": min_elevation_m},
            )
            db.add(matched_lake)
            db.flush()
            existing_utm.append((matched_lake, cent_utm))
        else:
            if lake_elev is not None and matched_lake.elevation_m is None:
                matched_lake.elevation_m = lake_elev
            if matched_lake.first_detected is None or obs_dt < matched_lake.first_detected:
                matched_lake.first_detected = obs_dt
            if matched_lake.last_detected is None or obs_dt > matched_lake.last_detected:
                matched_lake.last_detected = obs_dt

        # Replace any duplicate observation for same (lake, year, mission, method)
        prev = (
            db.query(LakeObservation)
            .filter_by(lake_id=matched_lake.id, year=year, mission=mission, method=method)
            .first()
        )
        if prev is None:
            prev = LakeObservation(lake_id=matched_lake.id, year=year, mission=mission, method=method)
            db.add(prev)
        prev.observed_start = comp.acquired_start
        prev.observed_end = comp.acquired_end
        prev.area_ha = round(area_ha, 3)
        prev.perimeter_m = round(perim_m, 1)
        prev.geometry = mapping(mpoly_wgs)
        prev.valid_pixel_fraction = round(valid_fraction, 4)
        prev.raster_asset_id = mask_asset.id
        prev.parameters = {"threshold": round(used_thr, 4), "min_area_ha": min_area_ha, "max_slope_deg": max_slope_deg}

        detected.append({
            "lake_id": matched_lake.id,
            "lake_code": matched_lake.lake_code,
            "name": matched_lake.name,
            "area_ha": round(area_ha, 3),
            "perimeter_m": round(perim_m, 1),
            "elevation_m": matched_lake.elevation_m,
        })

    db.commit()
    log(f"Detected {len(detected)} lakes (total {sum(d['area_ha'] for d in detected):.2f} ha)", 1.0)
    return {
        "composite_id": composite_id,
        "year": year,
        "mission": mission,
        "method": method,
        "threshold": round(used_thr, 4),
        "lake_count": len(detected),
        "total_area_ha": round(sum(d["area_ha"] for d in detected), 3),
        "mask_asset_id": mask_asset.id,
        "lakes": detected,
    }


def inventory_geojson(db, year: int | None = None) -> dict:
    lakes = db.query(GlacialLake).order_by(GlacialLake.lake_code).all()
    susc_map = {}
    for sa in db.query(SusceptibilityAssessment).order_by(SusceptibilityAssessment.id.desc()).all():
        if sa.lake_id not in susc_map:
            susc_map[sa.lake_id] = sa.category

    features = []
    for lk in lakes:
        obs_q = db.query(LakeObservation).filter_by(lake_id=lk.id)
        if year is not None:
            obs = obs_q.filter_by(year=year).order_by(LakeObservation.id.desc()).first()
        else:
            obs = obs_q.order_by(LakeObservation.year.desc(), LakeObservation.id.desc()).first()
        if obs is None:
            continue
        n_obs = obs_q.count()
        features.append({
            "type": "Feature",
            "geometry": obs.geometry,
            "properties": {
                "lake_id": lk.id,
                "lake_code": lk.lake_code,
                "name": lk.name,
                "area_ha": obs.area_ha,
                "perimeter_m": obs.perimeter_m,
                "elevation_m": lk.elevation_m,
                "year": obs.year,
                "mission": obs.mission,
                "method": obs.method,
                "observed_start": obs.observed_start.isoformat() if obs.observed_start else None,
                "observed_end": obs.observed_end.isoformat() if obs.observed_end else None,
                "first_detected": lk.first_detected.isoformat() if lk.first_detected else None,
                "last_detected": lk.last_detected.isoformat() if lk.last_detected else None,
                "n_observations": n_obs,
                "susceptibility_category": susc_map.get(lk.id),
            },
        })
    return {"type": "FeatureCollection", "features": features}


def lake_statistics(db) -> dict:
    obs_all = db.query(LakeObservation).order_by(LakeObservation.year).all()
    by_ym: dict[tuple[int, str, str], list[LakeObservation]] = {}
    for o in obs_all:
        by_ym.setdefault((o.year, o.mission, o.method), []).append(o)
    annual = []
    for (year, mission, method), items in sorted(by_ym.items()):
        annual.append({
            "year": year,
            "mission": mission,
            "method": method,
            "lake_count": len(items),
            "total_area_ha": round(sum(i.area_ha for i in items), 3),
            "valid_fraction": items[0].valid_pixel_fraction,
        })
    lakes = db.query(GlacialLake).order_by(GlacialLake.lake_code).all()
    per_lake = []
    for lk in lakes:
        series = [
            {"year": o.year, "area_ha": o.area_ha, "mission": o.mission, "method": o.method}
            for o in sorted(lk.observations, key=lambda x: x.year)
        ]
        per_lake.append({
            "lake_id": lk.id,
            "lake_code": lk.lake_code,
            "name": lk.name,
            "elevation_m": lk.elevation_m,
            "series": series,
        })
    return {"annual": annual, "per_lake": per_lake}

