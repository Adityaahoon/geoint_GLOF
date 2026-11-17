"""Complete FastAPI router implementing all GlacioGuard AI endpoints."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from shapely.geometry import box, mapping
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import IS_POSTGRES, SessionLocal, get_db
from ..jobs import JobContext, submit
from ..models import (
    AnnualIndicator,
    ChangeDetectionResult,
    ExposureResult,
    FloodResult,
    FloodScenario,
    GlacialLake,
    GlacierBoundary,
    InfrastructureFeature,
    LakeObservation,
    ModelEvaluation,
    ModelTrainingRun,
    ProcessingJob,
    RainfallRecord,
    RasterAsset,
    Report,
    SatelliteAcquisition,
    SusceptibilityAssessment,
    TerrainAnalysis,
    VectorAsset,
    VectorLayer,
)
from ..services import (
    change_service,
    dl_service,
    exposure_service,
    flood_service,
    gee_service,
    glof_service,
    indices,
    lake_service,
    rainfall_service,
    raster_service,
    report_service,
    sensors,
    stac_service,
    terrain_service,
)
from ..study_area import (
    DISASTER_CONTEXT,
    REFERENCE_POINTS,
    STANDARD_COMPARISONS,
    STUDY_BBOX,
    SUB_REGIONS,
    TIMELINE_PERIODS,
    UTM_EPSG,
    region_geometry,
)

router = APIRouter(prefix="/api")
settings = get_settings()


def _serialize_raster(a: RasterAsset | None) -> dict | None:
    if a is None:
        return None
    return {
        "id": a.id,
        "name": a.name,
        "kind": a.kind,
        "category": a.category,
        "path_name": Path(a.path).name if a.path else None,
        "original_filename": a.original_filename,
        "is_original": a.is_original,
        "parent_id": a.parent_id,
        "crs": a.crs,
        "width": a.width,
        "height": a.height,
        "band_count": a.band_count,
        "dtype": a.dtype,
        "resolution_x": a.resolution_x,
        "resolution_y": a.resolution_y,
        "nodata": a.nodata,
        "bounds_wgs84": a.bounds_wgs84,
        "statistics": a.statistics,
        "year": a.year,
        "acquired_start": a.acquired_start.isoformat() if a.acquired_start else None,
        "acquired_end": a.acquired_end.isoformat() if a.acquired_end else None,
        "source": a.source,
        "processing": a.processing,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "download_url": f"/api/rasters/{a.id}/download",
    }


def _serialize_job(j: ProcessingJob) -> dict:
    return {
        "id": j.id,
        "job_type": j.job_type,
        "status": j.status,
        "progress": j.progress,
        "parameters": j.parameters,
        "result": j.result,
        "log": j.log,
        "error": j.error,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
    }


# ----------------------------------------------------------------------------- System & Overview

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    import torch
    xgb_ok, xgb_err = False, None
    try:
        import xgboost  # noqa: F401
        xgb_ok = True
    except Exception as exc:
        xgb_err = str(exc)

    dem_ok = db.query(RasterAsset).filter(RasterAsset.kind.in_(["dem", "terrain"])).count() > 0
    osm_ok = db.query(InfrastructureFeature).count() > 0
    comps = db.query(RasterAsset).filter_by(kind="composite").count()
    lakes = db.query(GlacialLake).count()
    return {
        "status": "ok",
        "version": "1.0.0",
        "database": {"dialect": "postgresql+postgis" if IS_POSTGRES else "sqlite+geojson", "ok": True},
        "gee": gee_service.status(),
        "stac": {"available": True, "providers": ["planetary_computer", "earth_search", "aws_copernicus_dem"]},
        "torch": {"available": True, "version": torch.__version__, "device": dl_service.torch_device()},
        "xgboost": {"available": xgb_ok, "error": xgb_err},
        "data": {"dem": dem_ok, "osm": osm_ok, "composites": comps, "lakes": lakes},
    }


@router.get("/study-area")
def get_study_area():
    return {
        "name": "Kedarnath–Chorabari Glacier–Gandhi Sarovar–Mandakini River Basin, Uttarakhand, India",
        "bbox": list(STUDY_BBOX),
        "geometry": region_geometry("full_aoi"),
        "utm_epsg": UTM_EPSG,
        "regions": {
            k: {"name": v["name"], "bbox": list(v["bbox"]), "geometry": region_geometry(k)}
            for k, v in SUB_REGIONS.items()
        },
        "reference_points": REFERENCE_POINTS,
        "timeline_periods": TIMELINE_PERIODS,
        "standard_comparisons": [list(p) for p in STANDARD_COMPARISONS],
        "disaster_context": DISASTER_CONTEXT,
    }


@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    comps = db.query(RasterAsset).filter_by(kind="composite").order_by(RasterAsset.year).all()
    by_year: dict[int, list[dict]] = {}
    for c in comps:
        if c.year is None:
            continue
        p = c.processing or {}
        by_year.setdefault(c.year, []).append({
            "mission": p.get("mission", "optical"),
            "status": "ok",
            "valid_fraction": p.get("valid_fraction", 1.0),
            "scene_count": p.get("scene_count", 1),
            "composite_id": c.id,
            "quality_flags": p.get("quality_flags", []),
        })
    years_cov = [{"year": y, "missions": by_year.get(y, [])} for y in range(2000, 2027)]

    # Latest year lake inventory summary
    latest_obs_year = db.query(LakeObservation.year).order_by(LakeObservation.year.desc()).first()
    ref_year = latest_obs_year[0] if latest_obs_year else None
    if ref_year:
        obs = db.query(LakeObservation).filter_by(year=ref_year).all()
        lake_summary = {
            "count": len(obs),
            "total_area_ha": round(sum(o.area_ha for o in obs), 3),
            "reference_year": ref_year,
            "method": obs[0].method if obs else None,
        }
    else:
        lake_summary = {"count": 0, "total_area_ha": 0.0, "reference_year": None, "method": None}

    # Annual indicator series for full_aoi
    ind_rows = db.query(AnnualIndicator).filter_by(region="full_aoi").order_by(AnnualIndicator.year).all()
    series: dict[str, list[dict]] = {}
    for r in ind_rows:
        series.setdefault(r.indicator, []).append({
            "year": r.year,
            "value": r.value,
            "unit": r.unit,
            "mission": r.mission,
            "valid_fraction": r.valid_pixel_fraction,
            "quality_flags": r.quality_flags or [],
        })

    # Susceptibility counts
    susc_counts = {"Low": 0, "Moderate": 0, "High": 0, "Very High": 0}
    sas = db.query(SusceptibilityAssessment).all()
    for s in sas:
        if s.category in susc_counts:
            susc_counts[s.category] += 1

    jobs = db.query(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(12).all()
    return {
        "coverage": {
            "years": years_cov,
            "dem_available": db.query(RasterAsset).filter_by(kind="dem").count() > 0,
            "terrain_available": db.query(TerrainAnalysis).count() > 0,
            "osm_available": db.query(InfrastructureFeature).count() > 0,
        },
        "lakes": lake_summary,
        "indicators": {"series": series},
        "susceptibility": {
            **susc_counts,
            "assessed_count": len(sas),
            "method": "mcda_screening_v1" if sas else None,
            "is_trained_model": False,
        },
        "recent_jobs": [_serialize_job(j) for j in jobs],
        "rainfall_available": db.query(RainfallRecord).count() > 0,
    }


@router.get("/jobs")
def list_jobs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(ProcessingJob).order_by(ProcessingJob.id.desc()).limit(limit).all()
    return [_serialize_job(j) for j in rows]


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    j = db.get(ProcessingJob, job_id)
    if j is None:
        raise HTTPException(404, f"Job {job_id} not found")
    return _serialize_job(j)


# ----------------------------------------------------------------------------- Rasters & Vectors

@router.get("/rasters")
def list_rasters(kind: str | None = None, category: str | None = None, year: int | None = None, db: Session = Depends(get_db)):
    q = db.query(RasterAsset)
    if kind:
        q = q.filter_by(kind=kind)
    if category:
        q = q.filter_by(category=category)
    if year is not None:
        q = q.filter_by(year=year)
    return [_serialize_raster(r) for r in q.order_by(RasterAsset.id.desc()).all() if Path(r.path).exists()]


@router.get("/rasters/{raster_id}")
def get_raster(raster_id: int, db: Session = Depends(get_db)):
    a = db.get(RasterAsset, raster_id)
    if a is None or not Path(a.path).exists():
        raise HTTPException(404, f"Raster {raster_id} not found")
    return _serialize_raster(a)


def _render_and_cache(a: RasterAsset, bands: str | None, cmap: str | None, vmin: float | None, vmax: float | None, categorical: str | None) -> tuple[Path, list[list[float]], dict]:
    cat_map = None
    legend_cats = None
    if categorical == "transition" or a.category == "transition":
        cat_map = {1: "#38bdf8", 2: "#22c55e", 3: "#ef4444"}
        legend_cats = [
            {"value": 1, "label": "Stable", "color": "#38bdf8"},
            {"value": 2, "label": "Gain / Expansion", "color": "#22c55e"},
            {"value": 3, "label": "Loss / Contraction", "color": "#ef4444"},
        ]
    elif categorical == "water" or a.category == "water_mask":
        cat_map = {1: "#0ea5e9"}
        legend_cats = [{"value": 1, "label": "Detected Water Body", "color": "#0ea5e9"}]

    band_list = [int(x) for x in bands.split(",")] if bands else (
        [3, 2, 1] if a.kind == "composite" and (a.band_count or 0) >= 3 and not cmap else None
    )
    use_cmap = cmap or (None if (band_list and len(band_list) == 3) or cat_map else (a.category or "viridis"))
    log_scale = a.category == "flow_accumulation"
    gamma = 1.35 if (band_list and len(band_list) == 3 and a.kind == "composite") else 1.0

    key = hashlib.md5(f"{a.id}_{a.path}_{bands}_{use_cmap}_{vmin}_{vmax}_{categorical}_{Path(a.path).stat().st_mtime}".encode()).hexdigest()[:16]
    png_path = settings.previews_dir / f"preview_{a.id}_{key}.png"
    meta_path = settings.previews_dir / f"preview_{a.id}_{key}.json"

    if png_path.exists() and meta_path.exists():
        m = json.loads(meta_path.read_text())
        return png_path, m["bounds"], m["legend"]

    png_bytes, bounds = raster_service.render_preview(
        a.path, bands=band_list, cmap=use_cmap, vmin=vmin, vmax=vmax,
        categorical=cat_map, log_scale=log_scale, gamma=gamma
    )
    bstats = ((a.statistics or {}).get("bands") or [{}])[0]
    legend = {
        "cmap": use_cmap,
        "vmin": vmin if vmin is not None else bstats.get("min"),
        "vmax": vmax if vmax is not None else bstats.get("max"),
        "unit": (a.processing or {}).get("unit"),
        "categories": legend_cats,
    }
    png_path.write_bytes(png_bytes)
    meta_path.write_text(json.dumps({"bounds": bounds, "legend": legend}))
    return png_path, bounds, legend


@router.get("/rasters/{raster_id}/overlay")
def get_raster_overlay(
    raster_id: int,
    bands: str | None = None,
    cmap: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    categorical: str | None = None,
    db: Session = Depends(get_db),
):
    a = db.get(RasterAsset, raster_id)
    if a is None or not Path(a.path).exists():
        raise HTTPException(404, f"Raster {raster_id} not found")
    _, bounds, legend = _render_and_cache(a, bands, cmap, vmin, vmax, categorical)
    qs = f"?bands={bands or ''}&cmap={cmap or ''}&vmin={vmin if vmin is not None else ''}&vmax={vmax if vmax is not None else ''}&categorical={categorical or ''}"
    return {
        "raster_id": a.id,
        "name": a.name,
        "image_url": f"/api/rasters/{a.id}/preview.png{qs}",
        "bounds": bounds,
        "legend": legend,
    }


@router.get("/rasters/{raster_id}/preview.png")
def get_raster_preview_png(
    raster_id: int,
    bands: str | None = None,
    cmap: str | None = None,
    vmin: str | None = None,
    vmax: str | None = None,
    categorical: str | None = None,
    db: Session = Depends(get_db),
):
    a = db.get(RasterAsset, raster_id)
    if a is None or not Path(a.path).exists():
        raise HTTPException(404, f"Raster {raster_id} not found")
    vf_min = float(vmin) if vmin not in (None, "") else None
    vf_max = float(vmax) if vmax not in (None, "") else None
    png_path, _, _ = _render_and_cache(
        a, bands or None, cmap or None, vf_min, vf_max, categorical or None
    )
    return FileResponse(png_path, media_type="image/png")


@router.get("/rasters/{raster_id}/download")
def download_raster(raster_id: int, db: Session = Depends(get_db)):
    a = db.get(RasterAsset, raster_id)
    if a is None or not Path(a.path).exists():
        raise HTTPException(404, f"Raster {raster_id} not found")
    return FileResponse(a.path, media_type="image/tiff", filename=Path(a.path).name)


@router.get("/vectors")
def list_vector_layers(db: Session = Depends(get_db)):
    layers = db.query(VectorLayer).order_by(VectorLayer.key).all()
    return [
        {
            "key": v.key,
            "name": v.name,
            "category": v.category,
            "feature_count": v.feature_count,
            "source": v.source,
            "attribution": v.attribution,
            "url": f"/api/vectors/{v.key}",
        }
        for v in layers
        if Path(v.path).exists()
    ]


@router.get("/vectors/{key}")
def get_vector_layer(key: str, db: Session = Depends(get_db)):
    v = db.query(VectorLayer).filter_by(key=key).first()
    if v is None or not Path(v.path).exists():
        raise HTTPException(404, f"Vector layer '{key}' not found")
    return json.loads(Path(v.path).read_text())


# ----------------------------------------------------------------------------- Satellite & Composites

@router.get("/satellite/missions")
def list_missions():
    return [
        {
            "mission": s.mission,
            "label": s.label,
            "instrument": s.instrument,
            "gee_collection": s.gee_collection,
            "stac_collection": s.stac_collection,
            "native_resolution_m": s.native_resolution_m,
            "bands": s.gee_bands,
            "operational": [s.operational[0].isoformat(), s.operational[1].isoformat() if s.operational[1] else None],
            "notes": s.notes,
            "citation": s.citation,
        }
        for s in sensors.SENSORS.values()
    ]


class CollectionQuery(BaseModel):
    mission: str = "sentinel2"
    start_date: str = "2023-09-15"
    end_date: str = "2023-11-15"
    region: str = "full_aoi"
    max_cloud: float = 60.0
    provider: str = "auto"


@router.post("/satellite/collections")
def search_satellite_collections(req: CollectionQuery, db: Session = Depends(get_db)):
    if req.mission not in sensors.SENSORS:
        raise HTTPException(400, f"Unknown mission '{req.mission}'")
    spec = sensors.SENSORS[req.mission]

    if req.provider == "gee" or (req.provider == "auto" and gee_service.status()["available"]):
        raw = gee_service.collection_summary(req.mission, req.start_date, req.end_date, req.region, req.max_cloud)
        scenes = [
            {
                "scene_id": r["scene_id"],
                "datetime": datetime.utcfromtimestamp(r["time_ms"] / 1000).isoformat() + "Z" if r.get("time_ms") else None,
                "cloud_cover": r.get("cloud_cover"),
                "footprint": region_geometry(req.region),
                "preview_url": None,
                "quality_flags": ["landsat7_slc_off_gaps"] if req.mission == "landsat7" else [],
            }
            for r in raw
        ]
        return {"provider": "gee", "mission": req.mission, "count": len(scenes), "scenes": scenes, "notes": spec.notes}

    recs = stac_service.search_scenes(req.mission, req.start_date, req.end_date, req.region, req.max_cloud)
    scenes = []
    for r in recs:
        scenes.append({
            "scene_id": r["scene_id"],
            "datetime": r["datetime"],
            "cloud_cover": r["cloud_cover"],
            "footprint": r["footprint"],
            "preview_url": r.get("preview_url"),
            "quality_flags": r.get("quality_flags", []),
            "provider": r["provider"],
        })
        # Record in satellite_acquisitions if new
        exists = db.query(SatelliteAcquisition).filter_by(scene_id=r["scene_id"], provider=r["provider"]).first()
        if exists is None:
            db.add(SatelliteAcquisition(
                scene_id=r["scene_id"],
                provider=r["provider"],
                mission=req.mission,
                collection=r["collection"],
                acquired_at=datetime.fromisoformat(r["datetime"].replace("Z", "+00:00")).replace(tzinfo=None),
                cloud_cover=r["cloud_cover"],
                footprint=r["footprint"],
                properties=r["properties"],
            ))
    db.commit()
    return {"provider": "stac", "mission": req.mission, "count": len(scenes), "scenes": scenes, "notes": spec.notes}


class CompositeRequest(BaseModel):
    year: int = 2023
    mission: str = "auto"
    region: str = "full_aoi"
    season_start: str = "09-15"
    season_end: str = "11-15"
    max_cloud: float = 60.0
    resolution: float | None = None
    max_scenes: int = 6
    provider: str = "auto"


def _build_and_register_composite(ctx: JobContext, year: int, mission: str, region: str, season: tuple[str, str], max_cloud: float, resolution: float | None, max_scenes: int) -> dict:
    use_mission = sensors.preferred_landsat_for_year(year) if mission == "auto" else mission
    ctx.log(f"Building {year} post-monsoon composite ({use_mission}, region={region})", 0.1)
    res = stac_service.build_composite(
        year=year, mission=use_mission, region=region, season=season,
        resolution=resolution, max_cloud=max_cloud, max_scenes=max_scenes, log=ctx.log
    )
    if res.get("status") != "ok":
        return res

    db = SessionLocal()
    try:
        prev = (
            db.query(RasterAsset)
            .filter_by(kind="composite", year=year, category=use_mission)
            .all()
        )
        for p in prev:
            if (p.processing or {}).get("region") == region:
                db.delete(p)
        db.commit()

        asset = raster_service.register_raster(
            db, Path(res["path"]),
            name=f"{SENSORS_LABEL(use_mission)} Composite {year} ({region})",
            kind="composite", category=use_mission, year=year,
            source=res["source"],
            acquired_start=datetime.fromisoformat(res["window"][0]),
            acquired_end=datetime.fromisoformat(res["window"][1]),
            processing={
                "mission": use_mission,
                "region": region,
                "window": res["window"],
                "scene_count": res["scene_count"],
                "scenes": res["scenes"],
                "valid_fraction": res["valid_fraction"],
                "quality_flags": res["quality_flags"],
                "provider": res["provider"],
            },
        )
        ctx.log(f"Computing environmental indicators (NDWI/MNDWI/NDVI/NDSI/NBR) for {year}", 0.8)
        change_service.compute_indicators_for_composite(db, asset)
        ctx.log(f"Detecting glacial lakes on {year} composite", 0.9)
        lake_service.detect_lakes_on_composite(db, asset.id, method="mndwi_otsu")
        res["composite_id"] = asset.id
        return res
    finally:
        db.close()


def SENSORS_LABEL(m: str) -> str:
    return sensors.SENSORS[m].label if m in sensors.SENSORS else m


@router.post("/satellite/composite")
def create_composite(req: CompositeRequest):
    def _job(ctx: JobContext):
        return _build_and_register_composite(
            ctx, req.year, req.mission, req.region,
            (req.season_start, req.season_end), req.max_cloud, req.resolution, req.max_scenes
        )
    jid = submit("satellite_composite", _job, req.model_dump())
    return {"job_id": jid}


class BatchCompositeRequest(BaseModel):
    years: list[int] = Field(default_factory=lambda: [2000, 2011, 2012, 2013, 2015, 2020, 2024, 2025])
    mission: str = "auto"
    region: str = "full_aoi"
    season_start: str = "09-15"
    season_end: str = "11-15"
    max_cloud: float = 65.0
    max_scenes: int = 5


@router.post("/satellite/composite/batch")
def create_composite_batch(req: BatchCompositeRequest):
    def _job(ctx: JobContext):
        built = []
        for idx, y in enumerate(req.years):
            ctx.log(f"[{idx+1}/{len(req.years)}] Processing year {y}", idx / max(len(req.years), 1))
            r = _build_and_register_composite(
                ctx, y, req.mission, req.region,
                (req.season_start, req.season_end), req.max_cloud, None, req.max_scenes
            )
            built.append({"year": y, "status": r.get("status"), "composite_id": r.get("composite_id")})
        return {"composites": built}
    jid = submit("satellite_composite_batch", _job, req.model_dump())
    return {"job_id": jid}


@router.get("/satellite/composites")
def list_composites(region: str | None = None, db: Session = Depends(get_db)):
    comps = db.query(RasterAsset).filter_by(kind="composite").order_by(RasterAsset.year.desc()).all()
    out = []
    for c in comps:
        if not Path(c.path).exists():
            continue
        p = c.processing or {}
        if region and p.get("region") != region:
            continue
        out.append({
            "composite_id": c.id,
            "year": c.year,
            "mission": p.get("mission", c.category),
            "region": p.get("region", "full_aoi"),
            "window": p.get("window", []),
            "scene_count": p.get("scene_count", 0),
            "scenes": p.get("scenes", []),
            "valid_fraction": p.get("valid_fraction", 1.0),
            "quality_flags": p.get("quality_flags", []),
            "resolution_m": c.resolution_x,
            "provider": p.get("provider", "stac"),
            "raster": _serialize_raster(c),
        })
    return out


class ExportRequest(BaseModel):
    composite_id: int | None = None
    year: int | None = None
    mission: str = "landsat8"
    region: str = "full_aoi"
    provider: str = "local"


@router.post("/satellite/export")
def export_satellite(req: ExportRequest, db: Session = Depends(get_db)):
    if req.composite_id is not None:
        a = db.get(RasterAsset, req.composite_id)
        if a is None or not Path(a.path).exists():
            raise HTTPException(404, f"Composite {req.composite_id} not found")
        return {"download_url": f"/api/rasters/{a.id}/download", "filename": Path(a.path).name}
    if req.provider == "gee":
        comp, _ = gee_service.generate_annual_composite(req.year or 2023, req.mission, req.region)
        return gee_service.export_geotiff(comp, f"glacioguard_{req.mission}_{req.year}", req.region)
    raise HTTPException(400, "Provide composite_id for local GeoTIFF download or provider='gee'")


# ----------------------------------------------------------------------------- GeoTIFF Workspace

@router.post("/geotiff/upload")
async def upload_geotiff(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not files:
        raise HTTPException(400, "No files uploaded")

    batch_dir = settings.uploads_dir / f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for uf in files:
        dest = batch_dir / Path(uf.filename or "file").name
        with dest.open("wb") as f:
            shutil.copyfileobj(uf.file, f)
        if dest.suffix.lower() == ".zip":
            with zipfile.ZipFile(dest, "r") as zf:
                zf.extractall(batch_dir)
        else:
            saved.append(dest)

    all_files = list(batch_dir.rglob("*"))
    tif_files = [p for p in all_files if p.suffix.lower() in (".tif", ".tiff")]
    vec_files = [p for p in all_files if p.suffix.lower() in (".shp", ".geojson", ".json", ".gpkg")]

    if tif_files:
        p = tif_files[0]
        try:
            asset = raster_service.register_raster(
                db, p, name=p.stem, kind="upload", category="user_raster",
                is_original=True, original_filename=p.name, source="User upload (original preserved)"
            )
        except Exception as exc:
            raise HTTPException(400, f"Invalid GeoTIFF file: {exc}")
        return {"type": "raster", "asset": _serialize_raster(asset)}

    if vec_files:
        p = vec_files[0]
        try:
            gdf = gpd.read_file(p)
        except Exception as exc:
            raise HTTPException(400, f"Invalid vector dataset: {exc}")
        crs_str = gdf.crs.to_string() if gdf.crs else None
        gdf_wgs = gdf.to_crs("EPSG:4326") if gdf.crs else gdf
        b = gdf_wgs.total_bounds.tolist() if len(gdf_wgs) else [0, 0, 0, 0]
        va = VectorAsset(
            name=p.stem,
            path=str(p),
            original_filename=p.name,
            crs=crs_str,
            feature_count=len(gdf),
            geometry_types=sorted(gdf.geom_type.dropna().unique().tolist()),
            columns=[c for c in gdf.columns if c != "geometry"],
            bounds_wgs84=mapping(box(*b)) if len(gdf_wgs) else None,
        )
        db.add(va)
        db.commit()
        db.refresh(va)
        return {
            "type": "vector",
            "asset": {
                "id": va.id,
                "name": va.name,
                "original_filename": va.original_filename,
                "crs": va.crs,
                "feature_count": va.feature_count,
                "geometry_types": va.geometry_types,
                "columns": va.columns,
                "bounds_wgs84": va.bounds_wgs84,
                "created_at": va.created_at.isoformat(),
            },
        }

    raise HTTPException(400, "Unsupported file format. Upload .tif, .tiff, .shp (with sidecars or .zip), .geojson, or .gpkg")


@router.get("/geotiff/uploads")
def list_uploads(db: Session = Depends(get_db)):
    rasters = db.query(RasterAsset).filter(RasterAsset.kind.in_(["upload", "processed_upload"])).order_by(RasterAsset.id.desc()).all()
    vectors = db.query(VectorAsset).order_by(VectorAsset.id.desc()).all()
    return {
        "rasters": [_serialize_raster(r) for r in rasters if Path(r.path).exists()],
        "vectors": [
            {
                "id": v.id,
                "name": v.name,
                "original_filename": v.original_filename,
                "crs": v.crs,
                "feature_count": v.feature_count,
                "geometry_types": v.geometry_types,
                "columns": v.columns,
                "bounds_wgs84": v.bounds_wgs84,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in vectors
            if Path(v.path).exists()
        ],
    }


@router.get("/geotiff/metadata/{asset_id}")
def get_geotiff_metadata(asset_id: int, db: Session = Depends(get_db)):
    a = db.get(RasterAsset, asset_id)
    if a is None or not Path(a.path).exists():
        raise HTTPException(404, f"Raster asset {asset_id} not found")
    return raster_service.raster_metadata(a.path, with_stats=True)


class GeoTIFFProcessRequest(BaseModel):
    asset_id: int
    operation: str  # reproject | clip | resample | index | statistics
    params: dict[str, Any] = Field(default_factory=dict)


@router.post("/geotiff/process")
def process_geotiff(req: GeoTIFFProcessRequest, db: Session = Depends(get_db)):
    src_asset = db.get(RasterAsset, req.asset_id)
    if src_asset is None or not Path(src_asset.path).exists():
        raise HTTPException(404, f"Raster asset {req.asset_id} not found")

    op = req.operation.lower()
    p = req.params or {}
    try:
        if op == "reproject":
            dst_crs = p.get("dst_crs", f"EPSG:{UTM_EPSG}")
            out_path = raster_service.reproject_raster(
                src_asset.path, dst_crs=dst_crs,
                resolution=p.get("resolution"), resampling=p.get("resampling", "bilinear")
            )
            label = f"{src_asset.name} [reprojected → {dst_crs}]"
        elif op == "clip":
            geom = p.get("geometry") or region_geometry(p.get("region", "full_aoi"))
            out_path = raster_service.clip_raster(src_asset.path, geom)
            label = f"{src_asset.name} [clipped → {p.get('region', 'custom')}]"
        elif op == "resample":
            res_m = float(p.get("resolution", 30.0))
            out_path = raster_service.resample_raster(src_asset.path, res_m, p.get("resampling", "bilinear"))
            label = f"{src_asset.name} [resampled → {res_m}m]"
        elif op == "index":
            idx_name = p.get("index", "ndwi").lower()
            band_map = p.get("band_map") or {"green": 2, "red": 3, "nir": 4, "swir1": 5, "swir2": 6}
            with rasterio.open(src_asset.path) as src:
                bands = {k: src.read(int(b), masked=True).astype("float32").filled(np.nan) for k, b in band_map.items() if int(b) <= src.count}
                arr = indices.compute_index(idx_name, bands)
                out_path = settings.processed_dir / f"{Path(src_asset.path).stem}_{idx_name}_{uuid.uuid4().hex[:6]}.tif"
                raster_service.write_raster(out_path, arr, src.transform, src.crs, band_names=[idx_name])
            label = f"{src_asset.name} [{idx_name.upper()}]"
        elif op == "statistics":
            return {"statistics": raster_service.raster_metadata(src_asset.path, with_stats=True)["statistics"]}
        else:
            raise HTTPException(400, f"Unsupported operation '{op}'")
    except Exception as exc:
        raise HTTPException(400, str(exc))

    derived = raster_service.register_raster(
        db, out_path, name=label, kind="processed_upload", category=op,
        parent_id=src_asset.id, is_original=False, source=src_asset.source,
        processing={"operation": op, "params": p, "parent_id": src_asset.id}
    )
    return {"asset": _serialize_raster(derived)}


@router.get("/vectors/uploads/{vector_id}")
def get_uploaded_vector_geojson(vector_id: int, db: Session = Depends(get_db)):
    v = db.get(VectorAsset, vector_id)
    if v is None or not Path(v.path).exists():
        raise HTTPException(404, f"Vector upload {vector_id} not found")
    gdf = gpd.read_file(v.path)
    if gdf.crs:
        gdf = gdf.to_crs("EPSG:4326")
    return json.loads(gdf.to_json())


# ----------------------------------------------------------------------------- Glacial Lakes

class LakeDetectRequest(BaseModel):
    composite_id: int
    method: str = "mndwi_otsu"
    min_area_ha: float = 0.5
    max_slope_deg: float = 22.0
    threshold: float | None = None
    min_elevation_m: float = 2800.0


@router.post("/lakes/detect")
def detect_lakes(req: LakeDetectRequest):
    def _job(ctx: JobContext):
        db = SessionLocal()
        try:
            return lake_service.detect_lakes_on_composite(
                db, req.composite_id, method=req.method, min_area_ha=req.min_area_ha,
                max_slope_deg=req.max_slope_deg, threshold=req.threshold,
                min_elevation_m=req.min_elevation_m, log=ctx.log
            )
        finally:
            db.close()
    return {"job_id": submit("lake_detection", _job, req.model_dump())}


@router.get("/lakes/inventory")
def get_lake_inventory(year: int | None = None, db: Session = Depends(get_db)):
    return lake_service.inventory_geojson(db, year=year)


@router.get("/lakes/statistics")
def get_lake_statistics(db: Session = Depends(get_db)):
    return lake_service.lake_statistics(db)


@router.get("/lakes/{lake_id}")
def get_lake_detail(lake_id: int, db: Session = Depends(get_db)):
    lk = db.get(GlacialLake, lake_id)
    if lk is None:
        raise HTTPException(404, f"Lake {lake_id} not found")
    obs = sorted(lk.observations, key=lambda o: o.year)
    return {
        "lake": {
            "id": lk.id,
            "lake_code": lk.lake_code,
            "name": lk.name,
            "centroid": lk.centroid,
            "elevation_m": lk.elevation_m,
            "lake_type": lk.lake_type,
            "source": lk.source,
            "first_detected": lk.first_detected.isoformat() if lk.first_detected else None,
            "last_detected": lk.last_detected.isoformat() if lk.last_detected else None,
        },
        "observations": [
            {
                "id": o.id,
                "year": o.year,
                "mission": o.mission,
                "method": o.method,
                "area_ha": o.area_ha,
                "perimeter_m": o.perimeter_m,
                "observed_start": o.observed_start.isoformat() if o.observed_start else None,
                "observed_end": o.observed_end.isoformat() if o.observed_end else None,
                "valid_pixel_fraction": o.valid_pixel_fraction,
                "geometry": o.geometry,
            }
            for o in obs
        ],
    }


# ----------------------------------------------------------------------------- Historical Change, Glacier & 2013 Disaster

@router.get("/change-detection/indicators")
def get_change_indicators(region: str = "full_aoi", db: Session = Depends(get_db)):
    rows = db.query(AnnualIndicator).filter_by(region=region).order_by(AnnualIndicator.year).all()
    out: dict[str, dict] = {
        k: {"unit": v["unit"], "description": v["description"], "series": []}
        for k, v in change_service.INDICATOR_METADATA.items()
    }
    for r in rows:
        if r.indicator not in out:
            out[r.indicator] = {"unit": r.unit, "description": r.indicator, "series": []}
        out[r.indicator]["series"].append({
            "year": r.year,
            "value": r.value,
            "mission": r.mission,
            "valid_fraction": r.valid_pixel_fraction,
            "scene_count": r.scene_count,
            "window": [
                r.window_start.strftime("%Y-%m-%d") if r.window_start else None,
                r.window_end.strftime("%Y-%m-%d") if r.window_end else None,
            ],
            "quality_flags": r.quality_flags or [],
        })
    return {"region": region, "indicators": out}


class ChangeAnalyseRequest(BaseModel):
    year_a: int = 2011
    year_b: int = 2013
    indicator: str = "water"
    region: str = "full_aoi"


@router.post("/change-detection/analyse")
def run_change_detection(req: ChangeAnalyseRequest, db: Session = Depends(get_db)):
    try:
        res = change_service.analyse_pair(db, req.year_a, req.year_b, req.indicator, req.region)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    res["rasters"] = {k: _serialize_raster(v) for k, v in res["rasters"].items()}
    return res


@router.get("/change-detection/results")
def list_change_results(db: Session = Depends(get_db)):
    rows = db.query(ChangeDetectionResult).order_by(ChangeDetectionResult.id.desc()).limit(30).all()
    return [
        {
            "id": r.id,
            "indicator": r.indicator,
            "year_a": r.year_a,
            "year_b": r.year_b,
            "mission_a": r.mission_a,
            "mission_b": r.mission_b,
            "region": r.region,
            "statistics": r.statistics,
            "caveats": r.caveats,
            "raster_asset_id": r.raster_asset_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/glacier/summary")
def get_glacier_summary(region: str = "chorabari", db: Session = Depends(get_db)):
    rows = (
        db.query(AnnualIndicator)
        .filter_by(region=region, indicator="snow_ice_area_ha")
        .order_by(AnnualIndicator.year)
        .all()
    )
    series = [
        {
            "year": r.year,
            "snow_ice_area_ha": r.value,
            "mission": r.mission,
            "valid_fraction": r.valid_pixel_fraction,
            "quality_flags": r.quality_flags or [],
        }
        for r in rows
    ]
    gbs = db.query(GlacierBoundary).order_by(GlacierBoundary.year).all()
    outlines = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": g.geometry,
                "properties": {
                    "id": g.id,
                    "glacier_name": g.glacier_name,
                    "year": g.year,
                    "area_km2": g.area_km2,
                    "source": g.source,
                    "attributes": g.attributes,
                },
            }
            for g in gbs
            if g.geometry
        ],
    }
    return {
        "region": region,
        "series": series,
        "outlines": outlines,
        "outline_source": "Post-monsoon optical NDSI (>0.40, NIR>0.11) in UTM 44N",
        "notes": [
            "Post-monsoon (mid-September to mid-November) window minimizes seasonal snow cover so NDSI reflects perennial snow/ice.",
            "Lower Chorabari Glacier tongue is heavily covered by supraglacial moraine debris; optical NDSI maps clean ice and perennial snowfields above the debris-covered snout.",
        ],
    }


@router.post("/glacier/analyse")
def run_glacier_analyse(req: ChangeAnalyseRequest, db: Session = Depends(get_db)):
    req.indicator = "snow_ice"
    return run_change_detection(req, db)


@router.get("/disaster/context")
def get_disaster_context(db: Session = Depends(get_db)):
    comps = db.query(RasterAsset).filter_by(kind="composite").order_by(RasterAsset.year).all()
    avail_years = sorted({c.year for c in comps if c.year is not None})
    return {
        "context": DISASTER_CONTEXT,
        "available_composite_years": avail_years,
        "mechanisms": [
            {
                "key": "glof",
                "label": "1. Glacial Lake Outburst (Chorabari Lake / Gandhi Sarovar)",
                "description": "Rapid infilling and moraine dam breach of Chorabari Tal (~3960 m a.s.l.) on the morning of 17 June 2013 released a sudden high-velocity water-debris wave down the Chorabari stream channel toward Kedarnath.",
            },
            {
                "key": "rainfall_flash_flood",
                "label": "2. Extreme Orographic Rainfall & Snowmelt Flash Floods",
                "description": "Interaction of a western disturbance with the monsoon trough produced >300 mm of rainfall over 15–17 June 2013 across snow-covered catchments, generating extreme runoff on both the Mandakini and Saraswati channels before the lake breach.",
            },
            {
                "key": "landslides_debris",
                "label": "3. Widespread Landslides, Bank Erosion & Debris Flows",
                "description": "Saturated moraine and colluvial slopes failed along the Mandakini gorge (Kedarnath, Rambara, Gaurikund, Sonprayag), stripping riparian vegetation and bulking floodwaters with boulders and sediment.",
            },
            {
                "key": "combined_exposure",
                "label": "4. Compound Downstream Exposure",
                "description": "Downstream devastation at Kedarnath, Rambara, Gaurikund and Sonprayag resulted from the compound interaction of these processes combined with dense settlement/pilgrimage infrastructure inside the active valley floor.",
            },
        ],
        "key_dates": [
            {"date": "2013-06-15", "event": "Onset of intense continuous rainfall across upper Mandakini catchment"},
            {"date": "2013-06-16", "event": "Severe flash flooding and debris flows along Saraswati and Mandakini channels; heavy damage in Rambara and Kedarnath"},
            {"date": "2013-06-17", "event": "Breach of Chorabari Lake (Gandhi Sarovar) moraine dam (~06:45–07:00 IST) releasing catastrophic debris flood wave"},
        ],
    }


class DisasterCompareRequest(BaseModel):
    pre_year: int = 2011
    post_year: int = 2013
    region: str = "mandakini_corridor"


@router.post("/disaster/compare")
def run_disaster_compare(req: DisasterCompareRequest, db: Session = Depends(get_db)):
    try:
        res = change_service.compare_2013_disaster(db, req.pre_year, req.post_year, req.region)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    res["rasters"] = {k: _serialize_raster(v) for k, v in res["rasters"].items()}
    res["primary"]["rasters"] = {k: _serialize_raster(v) for k, v in res["primary"]["rasters"].items()}
    return res


# ----------------------------------------------------------------------------- GLOF Susceptibility

@router.get("/glof/methodology")
def get_glof_methodology():
    return glof_service.methodology_spec()


@router.get("/glof/ml-status")
def get_glof_ml_status():
    return glof_service.ml_pipeline_status()


@router.post("/glof/assess")
def run_glof_assessment():
    def _job(ctx: JobContext):
        db = SessionLocal()
        try:
            res = glof_service.assess_all_lakes(db, log=ctx.log)
            return {"assessed_lakes": len(res), "assessments": res}
        finally:
            db.close()
    return {"job_id": submit("glof_susceptibility", _job, {})}


@router.get("/glof/assessments")
def list_glof_assessments(db: Session = Depends(get_db)):
    rows = db.query(SusceptibilityAssessment).order_by(SusceptibilityAssessment.score.desc()).all()
    out = []
    for r in rows:
        lk = db.get(GlacialLake, r.lake_id)
        out.append({
            "id": r.id,
            "lake_id": r.lake_id,
            "lake_code": lk.lake_code if lk else f"LAKE-{r.lake_id}",
            "name": lk.name if lk else None,
            "elevation_m": lk.elevation_m if lk else None,
            "centroid": lk.centroid if lk else None,
            "method": r.method,
            "is_trained_model": r.is_trained_model,
            "score": r.score,
            "category": r.category,
            "factors": r.factors,
            "missing_parameters": r.missing_parameters or [],
            "uncertainty": r.uncertainty,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return out


# ----------------------------------------------------------------------------- Terrain & Hydrology

class FetchDEMRequest(BaseModel):
    source: str = "copernicus"
    region: str = "full_aoi"
    resolution: float = 30.0


@router.post("/terrain/fetch-dem")
def fetch_dem_endpoint(req: FetchDEMRequest):
    def _job(ctx: JobContext):
        ctx.log("Downloading Copernicus DEM GLO-30 (30 m) and warping to UTM Zone 44N", 0.2)
        info = stac_service.fetch_copernicus_dem(req.region, req.resolution)
        db = SessionLocal()
        try:
            a = raster_service.register_raster(
                db, Path(info["path"]),
                name=f"Copernicus DEM GLO-30 ({req.region}, {int(req.resolution)}m UTM44N)",
                kind="dem", category="elevation", source=info["source"],
                processing={"notes": info["notes"], "tiles": info["tiles"], "valid_fraction": info["valid_fraction"]}
            )
            ctx.log(f"Registered DEM asset #{a.id}", 1.0)
            return {"dem_asset_id": a.id, **info}
        finally:
            db.close()
    return {"job_id": submit("fetch_dem", _job, req.model_dump())}


class TerrainAnalyseRequest(BaseModel):
    stream_threshold_km2: float = 1.0


@router.post("/terrain/analyse")
def analyse_terrain_endpoint(req: TerrainAnalyseRequest):
    def _job(ctx: JobContext):
        db = SessionLocal()
        try:
            dem = terrain_service.latest_dem(db)
            if dem is None:
                ctx.log("DEM not yet in database; fetching Copernicus GLO-30 first", 0.02)
                info = stac_service.fetch_copernicus_dem("full_aoi", 30.0)
                dem = raster_service.register_raster(
                    db, Path(info["path"]),
                    name="Copernicus DEM GLO-30 (full_aoi, 30m UTM44N)",
                    kind="dem", category="elevation", source=info["source"]
                )
            return terrain_service.run_terrain_analysis(db, dem, req.stream_threshold_km2, log=ctx.log)
        finally:
            db.close()
    return {"job_id": submit("terrain_analysis", _job, req.model_dump())}


@router.get("/terrain/summary")
def get_terrain_summary(db: Session = Depends(get_db)):
    ta = db.query(TerrainAnalysis).order_by(TerrainAnalysis.id.desc()).first()
    if ta is None:
        return {"available": False, "statistics": None, "products": {}, "vectors": [], "dem_source": None}
    products = {}
    for name, aid in (ta.products or {}).items():
        ra = db.get(RasterAsset, aid)
        if ra and Path(ra.path).exists():
            products[name] = _serialize_raster(ra)
    vls = db.query(VectorLayer).filter(VectorLayer.category == "hydrology").all()
    return {
        "available": True,
        "dem_source": ta.dem_source,
        "statistics": ta.statistics,
        "parameters": ta.parameters,
        "products": products,
        "vectors": [
            {"key": v.key, "name": v.name, "feature_count": v.feature_count, "url": f"/api/vectors/{v.key}"}
            for v in vls if Path(v.path).exists()
        ],
    }


class FlowPathRequest(BaseModel):
    lake_id: int | None = None
    lon: float | None = None
    lat: float | None = None
    max_length_km: float | None = 25.0


@router.post("/terrain/flowpath")
def trace_flowpath(req: FlowPathRequest, db: Session = Depends(get_db)):
    lon, lat, name = req.lon, req.lat, "Selected point"
    if req.lake_id is not None:
        lk = db.get(GlacialLake, req.lake_id)
        if lk is None or not lk.centroid:
            raise HTTPException(404, f"Lake {req.lake_id} not found")
        lon, lat = lk.centroid["coordinates"][0], lk.centroid["coordinates"][1]
        name = f"{lk.lake_code} ({lk.name})"
    if lon is None or lat is None:
        # Default to Chorabari Lake
        lon, lat, name = 79.0580, 30.7470, "Chorabari Lake (Gandhi Sarovar)"
    try:
        return terrain_service.flow_path_from_point(db, lon=lon, lat=lat, name=name, max_length_km=req.max_length_km)
    except Exception as exc:
        raise HTTPException(400, str(exc))


# ----------------------------------------------------------------------------- Flood Simulation (Hypothetical / HEC-RAS 2D)

def _serialize_scenario(s: FloodScenario, db: Session) -> dict:
    frs = db.query(FloodResult).filter_by(scenario_id=s.id).order_by(FloodResult.id.desc()).all()
    return {
        "id": s.id,
        "name": s.name,
        "source_lake_id": s.source_lake_id,
        "scenario_type": s.scenario_type,
        "description": s.description,
        "hydrograph": s.hydrograph,
        "hydrograph_source": s.hydrograph_source,
        "terrain_asset_id": s.terrain_asset_id,
        "domain": s.domain,
        "assumptions": s.assumptions or [],
        "boundary_conditions": s.boundary_conditions or {},
        "status": s.status,
        "export_url": f"/api/flood/scenarios/{s.id}/export-download" if s.export_path and Path(s.export_path).exists() else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "results": [
            {
                "id": r.id,
                "scenario_id": r.scenario_id,
                "variable": r.variable,
                "model_software": r.model_software,
                "statistics": r.statistics,
                "extent_geometry": r.extent_geometry,
                "raster": _serialize_raster(db.get(RasterAsset, r.raster_asset_id)) if r.raster_asset_id else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in frs
        ],
    }


@router.get("/flood/scenarios")
def list_flood_scenarios(db: Session = Depends(get_db)):
    rows = db.query(FloodScenario).order_by(FloodScenario.id.desc()).all()
    return [_serialize_scenario(s, db) for s in rows]


class CreateScenarioRequest(BaseModel):
    name: str
    source_lake_id: int | None = None
    description: str | None = None
    hydrograph: dict | None = None
    hydrograph_source: str | None = None
    assumptions: list[str] | None = None
    downstream_length_km: float = 22.0
    manning_n: float = 0.065


@router.post("/flood/scenarios")
def create_flood_scenario(req: CreateScenarioRequest, db: Session = Depends(get_db)):
    try:
        scen = flood_service.create_scenario(
            db, req.name, req.source_lake_id, req.description,
            req.hydrograph, req.hydrograph_source, req.assumptions,
            req.downstream_length_km, req.manning_n
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return _serialize_scenario(scen, db)


@router.post("/flood/scenarios/{scenario_id}/export")
def export_flood_scenario(scenario_id: int, db: Session = Depends(get_db)):
    try:
        p = flood_service.export_hecras_package(db, scenario_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"download_url": f"/api/flood/scenarios/{scenario_id}/export-download", "filename": p.name}


@router.get("/flood/scenarios/{scenario_id}/export-download")
def download_flood_scenario_zip(scenario_id: int, db: Session = Depends(get_db)):
    scen = db.get(FloodScenario, scenario_id)
    if scen is None or not scen.export_path or not Path(scen.export_path).exists():
        p = flood_service.export_hecras_package(db, scenario_id)
    else:
        p = Path(scen.export_path)
    return FileResponse(p, media_type="application/zip", filename=p.name)


@router.post("/flood/scenarios/{scenario_id}/results")
async def upload_flood_result(
    scenario_id: int,
    file: UploadFile = File(...),
    variable: str = Form("depth"),
    model_software: str = Form("HEC-RAS 2D"),
    db: Session = Depends(get_db),
):
    dest_dir = settings.flood_dir / f"scenario_{scenario_id}" / "results"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{variable}_{uuid.uuid4().hex[:6]}_{Path(file.filename or 'output.tif').name}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        fr = flood_service.import_flood_result(db, scenario_id, dest, variable, model_software)
    except Exception as exc:
        raise HTTPException(400, f"Failed to import hydraulic result raster: {exc}")
    return {
        "id": fr.id,
        "scenario_id": fr.scenario_id,
        "variable": fr.variable,
        "model_software": fr.model_software,
        "statistics": fr.statistics,
        "extent_geometry": fr.extent_geometry,
        "raster": _serialize_raster(db.get(RasterAsset, fr.raster_asset_id)),
    }


@router.get("/flood/results")
def list_all_flood_results(scenario_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(FloodResult)
    if scenario_id is not None:
        q = q.filter_by(scenario_id=scenario_id)
    rows = q.order_by(FloodResult.id.desc()).all()
    return [
        {
            "id": r.id,
            "scenario_id": r.scenario_id,
            "variable": r.variable,
            "model_software": r.model_software,
            "statistics": r.statistics,
            "extent_geometry": r.extent_geometry,
            "raster": _serialize_raster(db.get(RasterAsset, r.raster_asset_id)) if r.raster_asset_id else None,
        }
        for r in rows
    ]


# ----------------------------------------------------------------------------- Infrastructure Exposure

@router.post("/exposure/fetch-osm")
def fetch_osm_endpoint():
    def _job(ctx: JobContext):
        db = SessionLocal()
        try:
            return exposure_service.fetch_osm_infrastructure(db, log=ctx.log)
        finally:
            db.close()
    return {"job_id": submit("fetch_osm", _job, {})}


@router.get("/exposure/infrastructure")
def get_infrastructure_geojson(category: str | None = None, db: Session = Depends(get_db)):
    return exposure_service.infrastructure_geojson(db, category=category)


@router.get("/exposure/infrastructure/summary")
def get_infrastructure_summary(db: Session = Depends(get_db)):
    return exposure_service.infrastructure_summary(db)


class ExposureAnalyseRequest(BaseModel):
    scenario_id: int | None = None
    lake_id: int | None = None
    buffer_m: float = 250.0
    hand_max_m: float = 25.0


@router.post("/exposure/analyse")
def run_exposure_analysis(req: ExposureAnalyseRequest, db: Session = Depends(get_db)):
    try:
        return exposure_service.analyse_exposure(
            db, scenario_id=req.scenario_id, lake_id=req.lake_id,
            buffer_m=req.buffer_m, hand_max_m=req.hand_max_m
        )
    except Exception as exc:
        raise HTTPException(400, str(exc))


# ----------------------------------------------------------------------------- Rainfall

@router.get("/rainfall")
def get_rainfall(db: Session = Depends(get_db)):
    return rainfall_service.rainfall_summary(db)


class RainfallFetchRequest(BaseModel):
    source: str = "nasa_power"
    start_year: int = 2000
    end_year: int = 2025


@router.post("/rainfall/fetch")
def fetch_rainfall_endpoint(req: RainfallFetchRequest):
    def _job(ctx: JobContext):
        db = SessionLocal()
        try:
            return rainfall_service.fetch_rainfall(db, req.source, req.start_year, req.end_year, log=ctx.log)
        finally:
            db.close()
    return {"job_id": submit("fetch_rainfall", _job, req.model_dump())}


# ----------------------------------------------------------------------------- Deep Learning Model Lab

@router.get("/models/datasets")
def get_model_datasets():
    return {
        "segmentation": dl_service.dataset_status(),
        "susceptibility": glof_service.ml_pipeline_status(),
    }


class PrepareTilesRequest(BaseModel):
    composite_id: int
    tile_size: int = 256
    stride: int = 256


@router.post("/models/prepare-tiles")
def prepare_tiles_endpoint(req: PrepareTilesRequest):
    def _job(ctx: JobContext):
        db = SessionLocal()
        try:
            return dl_service.prepare_tiles_from_composite(db, req.composite_id, req.tile_size, req.stride, log=ctx.log)
        finally:
            db.close()
    return {"job_id": submit("prepare_tiles", _job, req.model_dump())}


class TrainModelRequest(BaseModel):
    model_type: str = "unet"
    epochs: int = 25
    batch_size: int = 4
    learning_rate: float = 1e-3
    tile_size: int = 256


@router.post("/models/train")
def train_model_endpoint(req: TrainModelRequest, db: Session = Depends(get_db)):
    st = dl_service.dataset_status()
    if st["status"] != "ready":
        raise HTTPException(
            409,
            f"Model status is 'awaiting_training_data' ({st['paired_verified_tiles']} verified mask tiles found; "
            f"at least 6 verified image-mask pairs in {st['directory']}/verified_masks/ are required before training).",
        )
    run = ModelTrainingRun(
        model_type=req.model_type,
        task="lake_segmentation",
        status="queued",
        hyperparameters=req.model_dump(),
        history=[],
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    def _job(ctx: JobContext):
        s_db = SessionLocal()
        try:
            return dl_service.train_segmentation_model(
                s_db, run.id, req.model_type, req.epochs, req.batch_size, req.learning_rate, log=ctx.log
            )
        finally:
            s_db.close()

    jid = submit(f"train_{req.model_type}", _job, req.model_dump())
    run.job_id = jid
    db.commit()
    return {"job_id": jid, "run_id": run.id}


@router.get("/models/runs")
def list_model_runs(db: Session = Depends(get_db)):
    runs = db.query(ModelTrainingRun).order_by(ModelTrainingRun.id.desc()).all()
    out = []
    for r in runs:
        evs = db.query(ModelEvaluation).filter_by(run_id=r.id).all()
        out.append({
            "id": r.id,
            "model_type": r.model_type,
            "task": r.task,
            "status": r.status,
            "dataset_summary": r.dataset_summary,
            "hyperparameters": r.hyperparameters,
            "history": r.history or [],
            "checkpoint_path": r.checkpoint_path,
            "best_epoch": r.best_epoch,
            "job_id": r.job_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "evaluations": [
                {
                    "id": e.id,
                    "split": e.split,
                    "metrics": e.metrics,
                    "confusion_matrix": e.confusion_matrix,
                    "sample_count": e.sample_count,
                }
                for e in evs
            ],
        })
    return out


class EvaluateModelRequest(BaseModel):
    run_id: int
    split: str = "test"


@router.post("/models/evaluate")
def evaluate_model_endpoint(req: EvaluateModelRequest, db: Session = Depends(get_db)):
    run = db.get(ModelTrainingRun, req.run_id)
    if run is None or not run.checkpoint_path or not Path(run.checkpoint_path).exists():
        raise HTTPException(404, f"Completed training run {req.run_id} with checkpoint not found")
    evs = db.query(ModelEvaluation).filter_by(run_id=run.id, split=req.split).first()
    if evs:
        return {"run_id": run.id, "split": evs.split, "metrics": evs.metrics, "confusion_matrix": evs.confusion_matrix}
    raise HTTPException(400, "No evaluation split available")


# ----------------------------------------------------------------------------- Reports

class GenerateReportRequest(BaseModel):
    title: str | None = None
    sections: list[str] | None = None


@router.post("/reports/generate")
def generate_report_endpoint(req: GenerateReportRequest, db: Session = Depends(get_db)):
    rep = report_service.generate_pdf_report(db, title=req.title, sections=req.sections)
    return {
        "report_id": rep.id,
        "title": rep.title,
        "created_at": rep.created_at.isoformat(),
        "download_url": f"/api/reports/{rep.id}/download",
    }


@router.get("/reports")
def list_reports(db: Session = Depends(get_db)):
    rows = db.query(Report).order_by(Report.id.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "sections": r.sections,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "download_url": f"/api/reports/{r.id}/download",
        }
        for r in rows
        if Path(r.path).exists()
    ]


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if r is None or not Path(r.path).exists():
        raise HTTPException(404, f"Report {report_id} not found")
    return FileResponse(r.path, media_type="application/pdf", filename=Path(r.path).name)

