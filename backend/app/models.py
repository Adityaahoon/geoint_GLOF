"""ORM models. Every scientific record carries provenance (source dataset, acquisition
dates, processing parameters) so results are reproducible and auditable."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, GeoJSONGeometry


def _now() -> datetime:
    return datetime.utcnow()


class StudyArea(Base):
    __tablename__ = "study_areas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[dict] = mapped_column(GeoJSONGeometry("POLYGON"))
    utm_epsg: Mapped[int] = mapped_column(Integer, default=32644)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ProcessingJob(Base):
    """Reproducible processing log: one row per pipeline run."""
    __tablename__ = "processing_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued|running|completed|failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    log: Mapped[str | None] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class SatelliteAcquisition(Base):
    __tablename__ = "satellite_acquisitions"
    __table_args__ = (UniqueConstraint("scene_id", "provider"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[str] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(64))  # gee | planetary_computer | earth_search
    mission: Mapped[str] = mapped_column(String(32), index=True)  # landsat5/7/8/9, sentinel2, sentinel1
    collection: Mapped[str] = mapped_column(String(128))
    acquired_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    cloud_cover: Mapped[float | None] = mapped_column(Float)
    footprint: Mapped[dict | None] = mapped_column(GeoJSONGeometry("GEOMETRY"))
    properties: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class RasterAsset(Base):
    """Metadata + storage reference for every raster (uploaded, downloaded or derived)."""
    __tablename__ = "raster_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(64), index=True)  # upload|dem|composite|index|terrain|change|flood|mask
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    is_original: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    crs: Mapped[str | None] = mapped_column(String(255))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    band_count: Mapped[int | None] = mapped_column(Integer)
    dtype: Mapped[str | None] = mapped_column(String(32))
    resolution_x: Mapped[float | None] = mapped_column(Float)
    resolution_y: Mapped[float | None] = mapped_column(Float)
    nodata: Mapped[float | None] = mapped_column(Float)
    bounds_wgs84: Mapped[dict | None] = mapped_column(GeoJSONGeometry("POLYGON"))
    statistics: Mapped[dict | None] = mapped_column(JSON)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    acquired_start: Mapped[datetime | None] = mapped_column(DateTime)
    acquired_end: Mapped[datetime | None] = mapped_column(DateTime)
    source: Mapped[str | None] = mapped_column(Text)
    processing: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class VectorAsset(Base):
    __tablename__ = "vector_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    crs: Mapped[str | None] = mapped_column(String(255))
    feature_count: Mapped[int | None] = mapped_column(Integer)
    geometry_types: Mapped[list | None] = mapped_column(JSON)
    columns: Mapped[list | None] = mapped_column(JSON)
    bounds_wgs84: Mapped[dict | None] = mapped_column(GeoJSONGeometry("POLYGON"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class GlacialLake(Base):
    """Lake inventory entry. Identity is persistent across observations."""
    __tablename__ = "glacial_lakes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lake_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    centroid: Mapped[dict | None] = mapped_column(GeoJSONGeometry("POINT"))
    elevation_m: Mapped[float | None] = mapped_column(Float)
    lake_type: Mapped[str | None] = mapped_column(String(64))  # moraine-dammed, supraglacial... (if known)
    source: Mapped[str] = mapped_column(String(255))  # detection method / inventory reference
    first_detected: Mapped[datetime | None] = mapped_column(DateTime)
    last_detected: Mapped[datetime | None] = mapped_column(DateTime)
    attributes: Mapped[dict | None] = mapped_column(JSON)
    observations: Mapped[list["LakeObservation"]] = relationship(back_populates="lake", cascade="all, delete-orphan")


class LakeObservation(Base):
    """A lake boundary as observed in one composite / scene (lake boundaries + area)."""
    __tablename__ = "lake_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lake_id: Mapped[int] = mapped_column(ForeignKey("glacial_lakes.id"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    observed_start: Mapped[datetime | None] = mapped_column(DateTime)
    observed_end: Mapped[datetime | None] = mapped_column(DateTime)
    mission: Mapped[str] = mapped_column(String(32))
    method: Mapped[str] = mapped_column(String(64))  # mndwi_otsu | unet | deeplabv3plus | manual
    area_ha: Mapped[float] = mapped_column(Float)
    perimeter_m: Mapped[float | None] = mapped_column(Float)
    geometry: Mapped[dict] = mapped_column(GeoJSONGeometry("MULTIPOLYGON"))
    valid_pixel_fraction: Mapped[float | None] = mapped_column(Float)
    raster_asset_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    parameters: Mapped[dict | None] = mapped_column(JSON)
    lake: Mapped[GlacialLake] = relationship(back_populates="observations")


class AnnualIndicator(Base):
    """Annual (seasonal-window) environmental indicator statistics for a region."""
    __tablename__ = "annual_indicators"
    __table_args__ = (UniqueConstraint("year", "mission", "region", "indicator"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    mission: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(64))
    indicator: Mapped[str] = mapped_column(String(64))  # water_area_ha, snow_ice_area_ha, ndvi_mean, ...
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32))
    valid_pixel_fraction: Mapped[float | None] = mapped_column(Float)
    scene_count: Mapped[int | None] = mapped_column(Integer)
    window_start: Mapped[datetime | None] = mapped_column(DateTime)
    window_end: Mapped[datetime | None] = mapped_column(DateTime)
    scene_dates: Mapped[list | None] = mapped_column(JSON)
    quality_flags: Mapped[list | None] = mapped_column(JSON)
    raster_asset_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    parameters: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class GlacierBoundary(Base):
    __tablename__ = "glacier_boundaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    glacier_name: Mapped[str] = mapped_column(String(255))
    year: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(255))  # RGI 7.0 / GLIMS / derived NDSI mask
    area_km2: Mapped[float | None] = mapped_column(Float)
    geometry: Mapped[dict] = mapped_column(GeoJSONGeometry("MULTIPOLYGON"))
    attributes: Mapped[dict | None] = mapped_column(JSON)


class ChangeDetectionResult(Base):
    __tablename__ = "change_detection_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    indicator: Mapped[str] = mapped_column(String(64))
    year_a: Mapped[int] = mapped_column(Integer)
    year_b: Mapped[int] = mapped_column(Integer)
    mission_a: Mapped[str | None] = mapped_column(String(32))
    mission_b: Mapped[str | None] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(64))
    statistics: Mapped[dict | None] = mapped_column(JSON)
    caveats: Mapped[list | None] = mapped_column(JSON)
    raster_asset_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class TerrainAnalysis(Base):
    __tablename__ = "terrain_analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dem_source: Mapped[str] = mapped_column(String(128))
    dem_asset_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    products: Mapped[dict | None] = mapped_column(JSON)  # product -> raster_asset_id
    statistics: Mapped[dict | None] = mapped_column(JSON)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class VectorLayer(Base):
    """Derived vector layers (streams, watersheds, flow paths, glacier outlines…) as GeoJSON files."""
    __tablename__ = "vector_layers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    feature_count: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SusceptibilityAssessment(Base):
    __tablename__ = "susceptibility_assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lake_id: Mapped[int] = mapped_column(ForeignKey("glacial_lakes.id"), index=True)
    method: Mapped[str] = mapped_column(String(64))  # mcda_screening_v1 | random_forest | xgboost | mlp
    is_trained_model: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float | None] = mapped_column(Float)  # screening index 0..1 (NOT a probability)
    category: Mapped[str | None] = mapped_column(String(32))
    factors: Mapped[dict | None] = mapped_column(JSON)
    missing_parameters: Mapped[list | None] = mapped_column(JSON)
    uncertainty: Mapped[dict | None] = mapped_column(JSON)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class FloodScenario(Base):
    __tablename__ = "flood_scenarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    source_lake_id: Mapped[int | None] = mapped_column(ForeignKey("glacial_lakes.id"))
    scenario_type: Mapped[str] = mapped_column(String(64), default="hypothetical")
    description: Mapped[str | None] = mapped_column(Text)
    hydrograph: Mapped[dict | None] = mapped_column(JSON)  # user-supplied, with citation
    hydrograph_source: Mapped[str | None] = mapped_column(Text)
    terrain_asset_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    domain: Mapped[dict | None] = mapped_column(GeoJSONGeometry("POLYGON"))
    assumptions: Mapped[list | None] = mapped_column(JSON)
    boundary_conditions: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="defined")  # defined|exported|results_imported
    export_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class FloodResult(Base):
    __tablename__ = "flood_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("flood_scenarios.id"), index=True)
    variable: Mapped[str] = mapped_column(String(32))  # depth|velocity|wse|arrival_time|duration|extent
    raster_asset_id: Mapped[int | None] = mapped_column(ForeignKey("raster_assets.id"))
    model_software: Mapped[str | None] = mapped_column(String(128))
    statistics: Mapped[dict | None] = mapped_column(JSON)
    extent_geometry: Mapped[dict | None] = mapped_column(GeoJSONGeometry("MULTIPOLYGON"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class InfrastructureFeature(Base):
    __tablename__ = "infrastructure"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    osm_id: Mapped[str | None] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)  # building|road|bridge|hospital|school|settlement|...
    name: Mapped[str | None] = mapped_column(String(255))
    geometry: Mapped[dict] = mapped_column(GeoJSONGeometry("GEOMETRY"))
    tags: Mapped[dict | None] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(128), default="OpenStreetMap")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ExposureResult(Base):
    __tablename__ = "exposure_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int | None] = mapped_column(ForeignKey("flood_scenarios.id"))
    analysis_type: Mapped[str] = mapped_column(String(64))  # flood_overlay | flowpath_proximity
    statistics: Mapped[dict | None] = mapped_column(JSON)
    features: Mapped[dict | None] = mapped_column(JSON)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ModelTrainingRun(Base):
    __tablename__ = "model_training_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_type: Mapped[str] = mapped_column(String(64))  # unet | deeplabv3plus | random_forest | xgboost | mlp
    task: Mapped[str] = mapped_column(String(64))  # lake_segmentation | glof_susceptibility
    status: Mapped[str] = mapped_column(String(32), default="queued")
    dataset_summary: Mapped[dict | None] = mapped_column(JSON)
    hyperparameters: Mapped[dict | None] = mapped_column(JSON)
    history: Mapped[list | None] = mapped_column(JSON)  # per-epoch train/val loss & metrics
    checkpoint_path: Mapped[str | None] = mapped_column(Text)
    best_epoch: Mapped[int | None] = mapped_column(Integer)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("processing_jobs.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("model_training_runs.id"), index=True)
    split: Mapped[str] = mapped_column(String(32))  # val | test
    metrics: Mapped[dict | None] = mapped_column(JSON)
    confusion_matrix: Mapped[list | None] = mapped_column(JSON)
    sample_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class RainfallRecord(Base):
    __tablename__ = "rainfall_records"
    __table_args__ = (UniqueConstraint("source", "period", "date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64))  # CHIRPS | GPM_IMERG | NASA_POWER_MERRA2
    period: Mapped[str] = mapped_column(String(16))  # daily | monthly
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float)
    location: Mapped[dict | None] = mapped_column(GeoJSONGeometry("POINT"))
    parameters: Mapped[dict | None] = mapped_column(JSON)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(Text)
    sections: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

