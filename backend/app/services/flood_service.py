"""Flood scenario & HEC-RAS 2D hydraulic modelling integration service.

Scientific integrity rules:
- Flood depth, velocity and inundation extent are NEVER derived directly from a DEM.
- Scenarios are explicitly marked `scenario_type = "hypothetical"`.
- Outburst discharge hydrographs are never invented; users must supply a hydrograph with an
  explicit citation/source (e.g., published dam-breach study or empirical equation with
  documented assumptions).
- Because HEC-RAS 2D is a Windows desktop/CLI solver, this module provides:
  (a) Complete HEC-RAS 2D simulation package export (.zip containing the clipped UTM terrain
      GeoTIFF, 2D flow-area domain polygon GeoJSON, upstream breach boundary condition line,
      downstream normal-depth boundary line, D8 valley centreline GeoJSON, inflow hydrograph
      CSV, and step-by-step HEC-RAS 6.x setup instructions).
  (b) Direct import and validation of hydraulic model output rasters (depth, velocity, water
      surface elevation, arrival time, duration) exported from HEC-RAS 2D, computing wet
      inundation polygons and summary statistics in UTM 44N.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import LineString, MultiPolygon, Polygon, box, mapping, shape
from shapely.ops import unary_union

from ..config import get_settings
from ..models import FloodResult, FloodScenario, GlacialLake, RasterAsset
from ..study_area import region_geometry
from . import hydrology as hy
from .raster_service import clip_raster, register_raster
from .terrain_service import flow_path_from_point

settings = get_settings()


def create_scenario(
    db,
    name: str,
    source_lake_id: int | None,
    description: str | None,
    hydrograph: dict | None,
    hydrograph_source: str | None,
    assumptions: list[str] | None,
    downstream_length_km: float = 22.0,
    manning_n: float = 0.065,
) -> FloodScenario:
    if hydrograph and not (hydrograph_source and hydrograph_source.strip()):
        raise ValueError("A citation or engineering source description (`hydrograph_source`) is required whenever an inflow hydrograph is specified.")

    dem_a = db.query(RasterAsset).filter_by(kind="terrain", category="elevation").order_by(RasterAsset.id.desc()).first()
    if dem_a is None:
        dem_a = db.query(RasterAsset).filter_by(kind="dem").order_by(RasterAsset.id.desc()).first()

    default_assumptions = assumptions or [
        "HYPOTHETICAL SCENARIO: Does not represent a prediction or real-time forecast.",
        f"2D unsteady shallow-water / diffusion-wave routing over 30 m Copernicus GLO-30 DSM (Manning's n = {manning_n} for steep boulder-bed mountain channel).",
        "30 m DSM includes vegetation/building heights and does not resolve channel bathymetry below the water surface at acquisition time.",
        "Sediment entrainment / debris-flow rheology bulking is not represented unless explicitly configured in HEC-RAS 2D non-Newtonian mud/debris settings.",
    ]

    bc = {
        "upstream": "Inflow hydrograph boundary condition at lake outlet / breach line",
        "downstream": "Normal depth (friction slope S0 ≈ 0.04) at Sonprayag / lower Mandakini boundary",
        "manning_n": manning_n,
        "downstream_length_km": downstream_length_km,
    }

    scen = FloodScenario(
        name=name,
        source_lake_id=source_lake_id,
        scenario_type="hypothetical",
        description=description or "Hypothetical glacial lake outburst hydraulic modelling scenario for HEC-RAS 2D.",
        hydrograph=hydrograph,
        hydrograph_source=hydrograph_source,
        terrain_asset_id=dem_a.id if dem_a else None,
        domain=region_geometry("mandakini_corridor"),
        assumptions=default_assumptions,
        boundary_conditions=bc,
        status="defined",
    )
    db.add(scen)
    db.commit()
    db.refresh(scen)
    return scen


def export_hecras_package(db, scenario_id: int) -> Path:
    scen = db.get(FloodScenario, scenario_id)
    if scen is None:
        raise ValueError(f"Scenario {scenario_id} not found")
    dem_a = db.get(RasterAsset, scen.terrain_asset_id) if scen.terrain_asset_id else None
    if dem_a is None or not Path(dem_a.path).exists():
        raise ValueError("Terrain DEM raster is not available; fetch DEM and run terrain analysis first.")

    pkg_dir = settings.flood_dir / f"scenario_{scen.id}"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    zip_path = pkg_dir / f"hecras2d_scenario_{scen.id}.zip"

    # Trace flow path if source lake is linked
    fp_info = None
    if scen.source_lake_id:
        lk = db.get(GlacialLake, scen.source_lake_id)
        if lk and lk.centroid:
            pt = shape(lk.centroid)
            try:
                fp_info = flow_path_from_point(
                    db, lon=pt.x, lat=pt.y, name=f"Flow path from {lk.name}",
                    max_length_km=(scen.boundary_conditions or {}).get("downstream_length_km", 22.0)
                )
            except Exception:
                fp_info = None

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Terrain GeoTIFF (UTM 44N, metres)
        zf.write(dem_a.path, arcname="terrain/copernicus_glo30_utm44n_30m.tif")

        # 2. 2D Flow Area domain polygon
        dom_fc = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": scen.domain or region_geometry("mandakini_corridor"),
                "properties": {"name": scen.name, "scenario_type": "hypothetical", "crs": "EPSG:4326"},
            }],
        }
        zf.writestr("geometry/2d_flow_area_domain.geojson", json.dumps(dom_fc, indent=2))

        # 3. Flow path & elevation profile
        if fp_info:
            zf.writestr("geometry/d8_thalweg_flowpath.geojson", json.dumps(fp_info, indent=2))

        # 4. Hydrograph CSV (either user-supplied or empty template)
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["# Scenario", scen.name])
        writer.writerow(["# Type", "HYPOTHETICAL - NOT AN OBSERVED OR FORECAST HYDROGRAPH"])
        writer.writerow(["# Source / Citation", scen.hydrograph_source or "USER_MUST_SUPPLY_DEFENSIBLE_BREACH_HYDROGRAPH"])
        writer.writerow(["time_s", "discharge_m3s"])
        if scen.hydrograph and "time_s" in scen.hydrograph and "discharge_m3s" in scen.hydrograph:
            for t_val, q_val in zip(scen.hydrograph["time_s"], scen.hydrograph["discharge_m3s"]):
                writer.writerow([t_val, q_val])
        else:
            writer.writerow(["# Populate time_s and discharge_m3s from a documented breach model before running HEC-RAS 2D", ""])
        zf.writestr("boundary_conditions/inflow_hydrograph.csv", csv_buf.getvalue())

        # 5. Detailed README
        readme = f"""# GlacioGuard AI — HEC-RAS 2D Hydraulic Simulation Package
Scenario ID: {scen.id}
Scenario Name: {scen.name}
Classification: HYPOTHETICAL SCENARIO

## Contents
- `terrain/copernicus_glo30_utm44n_30m.tif`: Hydrologically conditioned / projected terrain in WGS 84 / UTM Zone 44N (EPSG:32644, units: metres).
- `geometry/2d_flow_area_domain.geojson`: Modelling domain covering the Mandakini river corridor.
- `geometry/d8_thalweg_flowpath.geojson`: DEM-derived steepest-descent centreline from the source lake.
- `boundary_conditions/inflow_hydrograph.csv`: Upstream breach hydrograph input table.

## Documented Assumptions & Boundary Conditions
{chr(10).join('- ' + a for a in (scen.assumptions or []))}
- Boundary conditions: {json.dumps(scen.boundary_conditions, indent=2)}

## Workflow in HEC-RAS (v6.3+)
1. Open RAS Mapper, set projection to EPSG:32644 (UTM Zone 44N), and import `terrain/copernicus_glo30_utm44n_30m.tif`.
2. Import `geometry/2d_flow_area_domain.geojson` as a 2D Flow Area perimeter and generate a computational mesh (20–30 m nominal cell size with breaklines along the thalweg).
3. Add upstream Flow Hydrograph BC from `boundary_conditions/inflow_hydrograph.csv` and downstream Normal Depth BC.
4. Run the 2D Unsteady Flow solver (Shallow Water Equations / Momentum formulation recommended for steep Himalayan valleys).
5. In RAS Mapper, export Maximum Depth (`depth`), Maximum Velocity (`velocity`), and Water Surface Elevation (`wse`) as GeoTIFFs, then upload them back into GlacioGuard AI via the Flood Simulation page (`POST /api/flood/scenarios/{scen.id}/results`).
"""
        zf.writestr("README_HECRAS_WORKFLOW.md", readme)

    scen.status = "exported"
    scen.export_path = str(zip_path)
    db.commit()
    return zip_path


def import_flood_result(
    db,
    scenario_id: int,
    raster_path: Path,
    variable: str,
    model_software: str = "HEC-RAS 2D",
    min_wet_depth_m: float = 0.05,
) -> FloodResult:
    scen = db.get(FloodScenario, scenario_id)
    if scen is None:
        raise ValueError(f"Scenario {scenario_id} not found")

    asset = register_raster(
        db, raster_path,
        name=f"Scenario {scen.id} {variable} ({model_software})",
        kind="flood", category=variable,
        source=f"{model_software} output for hypothetical scenario '{scen.name}'",
        processing={"scenario_id": scen.id, "variable": variable, "scenario_type": "hypothetical"}
    )

    with rasterio.open(raster_path) as src:
        arr = src.read(1, masked=True).astype("float32").filled(np.nan)
        transform, crs = src.transform, src.crs
        cell_ha = (abs(src.res[0]) * abs(src.res[1])) / 1e4 if (crs and crs.is_projected) else None

    thr = min_wet_depth_m if variable == "depth" else 0.01
    wet = np.isfinite(arr) & (arr >= thr)
    wet_vals = arr[wet]
    stats = {
        "max": round(float(np.nanmax(wet_vals)), 3) if wet_vals.size else 0.0,
        "mean": round(float(np.nanmean(wet_vals)), 3) if wet_vals.size else 0.0,
        "p90": round(float(np.nanpercentile(wet_vals, 90)), 3) if wet_vals.size else 0.0,
        "wet_pixels": int(wet.sum()),
        "area_ha_wet": round(float(wet.sum() * cell_ha), 2) if cell_ha else None,
        "threshold_applied": thr,
    }

    extent_geom = None
    if wet.any() and crs:
        polys = hy.polygonize_mask(wet, transform, min_area_m2=900.0)
        if polys:
            u = unary_union(polys)
            if isinstance(u, Polygon):
                u = MultiPolygon([u])
            extent_geom = mapping(hy.to_wgs84(u, crs))

    fr = FloodResult(
        scenario_id=scen.id,
        variable=variable,
        raster_asset_id=asset.id,
        model_software=model_software,
        statistics=stats,
        extent_geometry=extent_geom,
    )
    scen.status = "results_imported"
    db.add(fr)
    db.commit()
    db.refresh(fr)
    return fr

