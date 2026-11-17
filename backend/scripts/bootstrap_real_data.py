"""End-to-end real geospatial data acquisition & processing script for GlacioGuard AI.

Executes against real open satellite/terrain/infrastructure datasets:
  1. Copernicus DEM GLO-30 (30 m) download & warp to UTM Zone 44N (EPSG:32644).
  2. Priority-Flood hydrological conditioning, D8 flow direction/accumulation, Strahler streams,
     watersheds, slope, aspect, hillshade, TRI, and HAND.
  3. OpenStreetMap infrastructure & settlement extraction via Overpass API.
  4. Historical & June 2013 daily precipitation retrieval via NASA POWER MERRA-2 (or GEE CHIRPS/GPM).
  5. Post-monsoon satellite composites across key historical epochs (2000, 2011, 2012, 2013, 2015,
     2020, 2024, 2026-YTD) from USGS Landsat Collection 2 Level-2 & Copernicus Sentinel-2 L2A COGs.
  6. Multi-temporal glacial lake detection (MNDWI + NDWI + slope & elevation masking) in UTM 44N.
  7. Standard historical change-detection pairs & 2013 Kedarnath disaster impact analysis.
  8. GAPHAZ / Huggel / Allen multi-criteria GLOF susceptibility screening with uncertainty intervals.
  9. Default hypothetical HEC-RAS 2D scenario definition & downstream corridor exposure screening.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.main import _seed_study_areas
from app.models import FloodScenario, RasterAsset
from app.services import (
    change_service,
    dl_service,
    exposure_service,
    flood_service,
    glof_service,
    lake_service,
    rainfall_service,
    raster_service,
    report_service,
    sensors,
    stac_service,
    terrain_service,
)


def log(msg: str, prog: float | None = None) -> None:
    p = f" ({prog*100:.0f}%)" if prog is not None else ""
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}]{p} {msg}", flush=True)


def run_bootstrap(years: list[int], max_scenes: int = 3) -> None:
    init_db()
    _seed_study_areas()
    db = SessionLocal()
    try:
        # 1. Copernicus GLO-30 DEM
        dem_asset = db.query(RasterAsset).filter_by(kind="dem").first()
        if dem_asset is None or not Path(dem_asset.path).exists():
            log("=== Step 1: Copernicus DEM GLO-30 (30 m, UTM 44N) ===")
            dem_info = stac_service.fetch_copernicus_dem("full_aoi", 30.0)
            dem_asset = raster_service.register_raster(
                db, Path(dem_info["path"]),
                name="Copernicus DEM GLO-30 (full_aoi, 30m UTM44N)",
                kind="dem", category="elevation", source=dem_info["source"],
                processing={"notes": dem_info["notes"], "tiles": dem_info["tiles"], "valid_fraction": dem_info["valid_fraction"]}
            )

        # 2. Terrain & Hydrology
        from app.models import InfrastructureFeature, RainfallRecord, TerrainAnalysis
        if db.query(TerrainAnalysis).count() == 0:
            log("=== Step 2: DEM Derivatives & D8 Hydrological Analysis ===")
            terrain_service.run_terrain_analysis(db, dem_asset, stream_threshold_km2=1.0, log=log)

        # 3. OpenStreetMap Infrastructure
        if db.query(InfrastructureFeature).count() == 0:
            log("=== Step 3: OpenStreetMap Infrastructure & Settlements ===")
            try:
                exposure_service.fetch_osm_infrastructure(db, log=log)
            except Exception as exc:
                log(f"WARN: Overpass API fetch error: {exc}")

        # 4. Precipitation (2000–2025 monthly + 2013 daily monsoon window)
        if db.query(RainfallRecord).count() == 0:
            log("=== Step 4: Historical & June 2013 Precipitation ===")
            try:
                rainfall_service.fetch_rainfall(db, source="nasa_power", start_year=2000, end_year=2025, log=log)
            except Exception as exc:
                log(f"WARN: Rainfall fetch error: {exc}")

        # 5. Satellite Composites + Annual Indicators + Lake Detection
        log(f"=== Step 5: Building Satellite Composites for {years} ===")
        built_years = []
        for y in years:
            # Choose mission: Landsat 5 for <=2011, Landsat 7 for 2012, Landsat 8 for 2013-2019, Sentinel-2 / Landsat 8 for >=2020
            mission = "sentinel2" if y in (2020, 2024) else sensors.preferred_landsat_for_year(y)
            # For 2026 (year-to-date), use Jan 01 - today if post-monsoon hasn't started or use available months
            season = ("09-15", "11-20")
            if y == 2026:
                season = ("04-01", "11-15")
            log(f"--- Year {y} ({mission}, window {season[0]}..{season[1]}) ---")
            res = stac_service.build_composite(
                year=y, mission=mission, region="full_aoi",
                season=season, resolution=30.0, max_cloud=65.0, max_scenes=max_scenes, log=log
            )
            if res.get("status") != "ok":
                log(f"  No composite built for {y}: {res.get('message')}")
                continue

            comp_asset = raster_service.register_raster(
                db, Path(res["path"]),
                name=f"{sensors.SENSORS[mission].label} Composite {y} (full_aoi)",
                kind="composite", category=mission, year=y,
                source=res["source"],
                acquired_start=datetime.fromisoformat(res["window"][0]),
                acquired_end=datetime.fromisoformat(res["window"][1]),
                processing={
                    "mission": mission,
                    "region": "full_aoi",
                    "window": res["window"],
                    "scene_count": res["scene_count"],
                    "scenes": res["scenes"],
                    "valid_fraction": res["valid_fraction"],
                    "quality_flags": res["quality_flags"],
                    "provider": res["provider"],
                },
            )
            change_service.compute_indicators_for_composite(db, comp_asset)
            lake_service.detect_lakes_on_composite(db, comp_asset.id, method="mndwi_otsu", log=log)
            built_years.append(y)

        # Prepare sample 256x256 tiles on the most recent composite for Model Lab
        latest_comp = db.query(RasterAsset).filter_by(kind="composite").order_by(RasterAsset.year.desc()).first()
        if latest_comp:
            log("=== Step 6: Preparing 256x256 Image Tiles + Unverified Pre-Labels for Model Lab ===")
            dl_service.prepare_tiles_from_composite(db, latest_comp.id, tile_size=256, stride=256, log=log)

        # 7. Historical Change Detection Pairs & 2013 Disaster Analysis
        log("=== Step 7: Standard Historical Change Pairs & 2013 Disaster Comparison ===")
        pairs = [(2000, 2012), (2012, 2013), (2013, 2015), (2015, 2020), (2020, 2024), (2024, 2026)]
        for ya, yb in pairs:
            if ya in built_years and yb in built_years:
                for ind in ("water", "vegetation", "snow_ice", "exposed_ground"):
                    change_service.analyse_pair(db, ya, yb, indicator=ind, region="full_aoi")
        if 2011 in built_years and 2013 in built_years:
            change_service.compare_2013_disaster(db, pre_year=2011, post_year=2013, region="mandakini_corridor")
        elif 2012 in built_years and 2013 in built_years:
            change_service.compare_2013_disaster(db, pre_year=2012, post_year=2013, region="mandakini_corridor")

        # 8. GLOF Susceptibility Screening
        log("=== Step 8: GLOF Multi-Criteria Susceptibility Screening ===")
        glof_service.assess_all_lakes(db, log=log)

        # 9. Hypothetical HEC-RAS 2D Scenario & Downstream Corridor Exposure
        log("=== Step 9: Hypothetical Scenario & Downstream Exposure Screening ===")
        if db.query(FloodScenario).count() == 0:
            scen = flood_service.create_scenario(
                db,
                name="Hypothetical Chorabari / Upper Mandakini Outburst Routing Package",
                source_lake_id=None,
                description="Baseline HEC-RAS 2D terrain & boundary package for the Kedarnath–Sonprayag corridor (awaiting user-supplied breach hydrograph and HEC-RAS 2D solver outputs).",
                hydrograph=None,
                hydrograph_source=None,
                assumptions=None,
            )
            flood_service.export_hecras_package(db, scen.id)
        try:
            exposure_service.analyse_exposure(db, scenario_id=None, lake_id=None, buffer_m=250.0, hand_max_m=25.0)
        except Exception as exc:
            log(f"WARN: Exposure screening skipped: {exc}")

        # 10. Generate initial PDF research report
        log("=== Step 10: Generating Downloadable PDF Research Report ===")
        rep = report_service.generate_pdf_report(db)
        log(f"=== Bootstrap complete! Report saved to {rep.path} ===")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap real satellite, DEM, hydrological & OSM data for GlacioGuard AI")
    parser.add_argument("--years", nargs="+", type=int, default=[2000, 2011, 2012, 2013, 2015, 2020, 2024, 2026])
    parser.add_argument("--max-scenes", type=int, default=2)
    args = parser.parse_args()
    run_bootstrap(args.years, max_scenes=args.max_scenes)
