-- =============================================================================
-- GlacioGuard AI — PostgreSQL + PostGIS Spatial Schema
-- Automatically executed on container startup in docker-compose.yml.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Study areas
CREATE TABLE IF NOT EXISTS study_areas (
    id SERIAL PRIMARY KEY,
    key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    geometry geometry(POLYGON, 4326) NOT NULL,
    utm_epsg INTEGER DEFAULT 32644,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_study_areas_geom ON study_areas USING GIST (geometry);

-- Reproducible processing jobs log
CREATE TABLE IF NOT EXISTS processing_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'queued',
    progress DOUBLE PRECISION DEFAULT 0.0,
    parameters JSONB,
    result JSONB,
    log TEXT DEFAULT '',
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- Satellite acquisitions metadata
CREATE TABLE IF NOT EXISTS satellite_acquisitions (
    id SERIAL PRIMARY KEY,
    scene_id VARCHAR(255) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    mission VARCHAR(32) NOT NULL,
    collection VARCHAR(128) NOT NULL,
    acquired_at TIMESTAMP NOT NULL,
    cloud_cover DOUBLE PRECISION,
    footprint geometry(GEOMETRY, 4326),
    properties JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scene_id, provider)
);
CREATE INDEX IF NOT EXISTS idx_sat_acq_footprint ON satellite_acquisitions USING GIST (footprint);

-- Raster metadata (files stored in object/filesystem storage)
CREATE TABLE IF NOT EXISTS raster_assets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    kind VARCHAR(64) NOT NULL,
    category VARCHAR(64),
    path TEXT NOT NULL,
    original_filename VARCHAR(255),
    is_original BOOLEAN DEFAULT FALSE,
    parent_id INTEGER REFERENCES raster_assets(id),
    crs VARCHAR(255),
    width INTEGER,
    height INTEGER,
    band_count INTEGER,
    dtype VARCHAR(32),
    resolution_x DOUBLE PRECISION,
    resolution_y DOUBLE PRECISION,
    nodata DOUBLE PRECISION,
    bounds_wgs84 geometry(POLYGON, 4326),
    statistics JSONB,
    year INTEGER,
    acquired_start TIMESTAMP,
    acquired_end TIMESTAMP,
    source TEXT,
    processing JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_raster_assets_bounds ON raster_assets USING GIST (bounds_wgs84);

-- Vector uploads
CREATE TABLE IF NOT EXISTS vector_assets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    original_filename VARCHAR(255),
    crs VARCHAR(255),
    feature_count INTEGER,
    geometry_types JSONB,
    columns JSONB,
    bounds_wgs84 geometry(POLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Persistent glacial lake inventory
CREATE TABLE IF NOT EXISTS glacial_lakes (
    id SERIAL PRIMARY KEY,
    lake_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255),
    centroid geometry(POINT, 4326),
    elevation_m DOUBLE PRECISION,
    lake_type VARCHAR(64),
    source VARCHAR(255) NOT NULL,
    first_detected TIMESTAMP,
    last_detected TIMESTAMP,
    attributes JSONB
);
CREATE INDEX IF NOT EXISTS idx_glacial_lakes_centroid ON glacial_lakes USING GIST (centroid);

-- Multi-temporal lake boundary observations
CREATE TABLE IF NOT EXISTS lake_observations (
    id SERIAL PRIMARY KEY,
    lake_id INTEGER NOT NULL REFERENCES glacial_lakes(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    observed_start TIMESTAMP,
    observed_end TIMESTAMP,
    mission VARCHAR(32) NOT NULL,
    method VARCHAR(64) NOT NULL,
    area_ha DOUBLE PRECISION NOT NULL,
    perimeter_m DOUBLE PRECISION,
    geometry geometry(MULTIPOLYGON, 4326) NOT NULL,
    valid_pixel_fraction DOUBLE PRECISION,
    raster_asset_id INTEGER REFERENCES raster_assets(id),
    parameters JSONB
);
CREATE INDEX IF NOT EXISTS idx_lake_obs_geom ON lake_observations USING GIST (geometry);

-- Annual environmental indicators
CREATE TABLE IF NOT EXISTS annual_indicators (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    mission VARCHAR(32) NOT NULL,
    region VARCHAR(64) NOT NULL,
    indicator VARCHAR(64) NOT NULL,
    value DOUBLE PRECISION,
    unit VARCHAR(32),
    valid_pixel_fraction DOUBLE PRECISION,
    scene_count INTEGER,
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    scene_dates JSONB,
    quality_flags JSONB,
    raster_asset_id INTEGER REFERENCES raster_assets(id),
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year, mission, region, indicator)
);

-- Glacier boundaries
CREATE TABLE IF NOT EXISTS glacier_boundaries (
    id SERIAL PRIMARY KEY,
    glacier_name VARCHAR(255) NOT NULL,
    year INTEGER,
    source VARCHAR(255) NOT NULL,
    area_km2 DOUBLE PRECISION,
    geometry geometry(MULTIPOLYGON, 4326) NOT NULL,
    attributes JSONB
);
CREATE INDEX IF NOT EXISTS idx_glacier_geom ON glacier_boundaries USING GIST (geometry);

-- Change detection results
CREATE TABLE IF NOT EXISTS change_detection_results (
    id SERIAL PRIMARY KEY,
    indicator VARCHAR(64) NOT NULL,
    year_a INTEGER NOT NULL,
    year_b INTEGER NOT NULL,
    mission_a VARCHAR(32),
    mission_b VARCHAR(32),
    region VARCHAR(64) NOT NULL,
    statistics JSONB,
    caveats JSONB,
    raster_asset_id INTEGER REFERENCES raster_assets(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Terrain analysis runs
CREATE TABLE IF NOT EXISTS terrain_analyses (
    id SERIAL PRIMARY KEY,
    dem_source VARCHAR(128) NOT NULL,
    dem_asset_id INTEGER REFERENCES raster_assets(id),
    products JSONB,
    statistics JSONB,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Derived vector layers
CREATE TABLE IF NOT EXISTS vector_layers (
    id SERIAL PRIMARY KEY,
    key VARCHAR(128) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    path TEXT NOT NULL,
    feature_count INTEGER,
    source TEXT,
    attribution TEXT,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GLOF susceptibility assessments
CREATE TABLE IF NOT EXISTS susceptibility_assessments (
    id SERIAL PRIMARY KEY,
    lake_id INTEGER NOT NULL REFERENCES glacial_lakes(id) ON DELETE CASCADE,
    method VARCHAR(64) NOT NULL,
    is_trained_model BOOLEAN DEFAULT FALSE,
    score DOUBLE PRECISION,
    category VARCHAR(32),
    factors JSONB,
    missing_parameters JSONB,
    uncertainty JSONB,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hypothetical flood scenarios
CREATE TABLE IF NOT EXISTS flood_scenarios (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_lake_id INTEGER REFERENCES glacial_lakes(id),
    scenario_type VARCHAR(64) DEFAULT 'hypothetical',
    description TEXT,
    hydrograph JSONB,
    hydrograph_source TEXT,
    terrain_asset_id INTEGER REFERENCES raster_assets(id),
    domain geometry(POLYGON, 4326),
    assumptions JSONB,
    boundary_conditions JSONB,
    status VARCHAR(32) DEFAULT 'defined',
    export_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hydraulic flood simulation outputs
CREATE TABLE IF NOT EXISTS flood_results (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES flood_scenarios(id) ON DELETE CASCADE,
    variable VARCHAR(32) NOT NULL,
    raster_asset_id INTEGER REFERENCES raster_assets(id),
    model_software VARCHAR(128),
    statistics JSONB,
    extent_geometry geometry(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_flood_results_extent ON flood_results USING GIST (extent_geometry);

-- OpenStreetMap infrastructure
CREATE TABLE IF NOT EXISTS infrastructure (
    id SERIAL PRIMARY KEY,
    osm_id VARCHAR(64),
    category VARCHAR(64) NOT NULL,
    name VARCHAR(255),
    geometry geometry(GEOMETRY, 4326) NOT NULL,
    tags JSONB,
    source VARCHAR(128) DEFAULT 'OpenStreetMap',
    retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_infrastructure_geom ON infrastructure USING GIST (geometry);

-- Exposure analysis runs
CREATE TABLE IF NOT EXISTS exposure_results (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER REFERENCES flood_scenarios(id),
    analysis_type VARCHAR(64) NOT NULL,
    statistics JSONB,
    features JSONB,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deep learning training runs & evaluation
CREATE TABLE IF NOT EXISTS model_training_runs (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(64) NOT NULL,
    task VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'queued',
    dataset_summary JSONB,
    hyperparameters JSONB,
    history JSONB,
    checkpoint_path TEXT,
    best_epoch INTEGER,
    job_id INTEGER REFERENCES processing_jobs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_evaluations (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES model_training_runs(id) ON DELETE CASCADE,
    split VARCHAR(32) NOT NULL,
    metrics JSONB,
    confusion_matrix JSONB,
    sample_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rainfall records
CREATE TABLE IF NOT EXISTS rainfall_records (
    id SERIAL PRIMARY KEY,
    source VARCHAR(64) NOT NULL,
    period VARCHAR(16) NOT NULL,
    date TIMESTAMP NOT NULL,
    precipitation_mm DOUBLE PRECISION,
    location geometry(POINT, 4326),
    parameters JSONB,
    UNIQUE(source, period, date)
);

-- Generated PDF reports
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    sections JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

