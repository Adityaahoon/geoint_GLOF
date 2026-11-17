"""Downstream infrastructure & settlement exposure analysis service.

Integrates real OpenStreetMap features (settlements, buildings, roads, bridges, hospitals,
schools, helipads, temples/shrines, power facilities) across the Upper Mandakini study area
via the Overpass API and stores them in the `infrastructure` table.

Supports two exposure analysis modes:
  1. `flood_overlay`: Overlays infrastructure with an imported hydraulic flood extent polygon
     (`FloodResult.extent_geometry`) from a hypothetical scenario.
  2. `flowpath_corridor`: When a hydraulic simulation raster is not yet imported, screens
     infrastructure located within a user-specified horizontal buffer (`buffer_m`) AND low
     relative elevation above the nearest drainage (`hand_max_m` on the HAND terrain raster)
     along the D8 steepest-descent flow path from a glacial lake.

All outputs are strictly labelled as POTENTIAL EXPOSURE (never confirmed historical damage).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
import rasterio
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.ops import unary_union

from ..config import get_settings
from ..models import ExposureResult, FloodResult, GlacialLake, InfrastructureFeature, RasterAsset, VectorLayer
from ..study_area import STUDY_BBOX, UTM_EPSG
from . import hydrology as hy
from .terrain_service import flow_path_from_point

settings = get_settings()

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _classify_osm_tags(tags: dict) -> str:
    if not tags:
        return "other"
    if tags.get("bridge") and tags.get("bridge") not in ("no", "false"):
        return "bridge"
    if tags.get("amenity") in ("hospital", "clinic", "doctors", "pharmacy") or tags.get("healthcare"):
        return "hospital"
    if tags.get("amenity") in ("school", "college", "university"):
        return "school"
    if tags.get("aeroway") in ("helipad", "heliport"):
        return "helipad"
    if tags.get("power"):
        return "power"
    if tags.get("place") in ("town", "village", "hamlet", "isolated_dwelling", "locality", "suburb"):
        return "settlement"
    if tags.get("amenity") in ("place_of_worship", "police", "fire_station", "townhall", "shelter", "community_centre"):
        return "public"
    if tags.get("building"):
        return "building"
    if tags.get("highway"):
        return "road"
    return "other"


def fetch_osm_infrastructure(db, bbox: tuple[float, float, float, float] = STUDY_BBOX, log=lambda m, p=None: None) -> dict:
    w, s, e, n = bbox
    query = f"""
    [out:json][timeout:60];
    (
      node["place"]({s},{w},{n},{e});
      node["amenity"~"hospital|clinic|doctors|school|college|place_of_worship|police|shelter"]({s},{w},{n},{e});
      node["aeroway"="helipad"]({s},{w},{n},{e});
      way["building"]({s},{w},{n},{e});
      way["highway"]({s},{w},{n},{e});
      way["bridge"]({s},{w},{n},{e});
      way["aeroway"="helipad"]({s},{w},{n},{e});
      way["power"]({s},{w},{n},{e});
    );
    out body geom;
    """
    log("Querying OpenStreetMap Overpass API for Upper Mandakini infrastructure", 0.15)
    payload = None
    last_err = None
    headers = {"User-Agent": "GlacioGuardAI-Research/1.0 (Geospatial GLOF Research Platform)"}
    for url in OVERPASS_ENDPOINTS:
        try:
            with httpx.Client(timeout=65.0, headers=headers, follow_redirects=True) as client:
                resp = client.post(url, data={"data": query})
                if resp.status_code == 200:
                    payload = resp.json()
                    break
                last_err = f"{url} returned HTTP {resp.status_code}"
        except Exception as exc:
            last_err = f"{url}: {exc}"

    if payload is None:
        raise RuntimeError(f"Failed to retrieve OpenStreetMap data from Overpass endpoints: {last_err}")

    elements = payload.get("elements", [])
    log(f"Parsing {len(elements)} OpenStreetMap elements", 0.55)
    db.query(InfrastructureFeature).delete()

    counts: dict[str, int] = {}
    geojson_feats = []
    for el in elements:
        tags = el.get("tags") or {}
        cat = _classify_osm_tags(tags)
        osm_id = f"{el.get('type', 'el')}/{el.get('id')}"
        name = tags.get("name:en") or tags.get("name") or tags.get("ref")

        geom_dict = None
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            geom_dict = {"type": "Point", "coordinates": [float(el["lon"]), float(el["lat"])]}
        elif el.get("type") == "way" and el.get("geometry"):
            coords = [[float(pt["lon"]), float(pt["lat"])] for pt in el["geometry"]]
            if len(coords) >= 4 and coords[0] == coords[-1] and cat in ("building", "helipad", "public", "hospital", "school"):
                geom_dict = {"type": "Polygon", "coordinates": [coords]}
            elif len(coords) >= 2:
                geom_dict = {"type": "LineString", "coordinates": coords}
        if geom_dict is None:
            continue

        row = InfrastructureFeature(
            osm_id=osm_id,
            category=cat,
            name=name,
            geometry=geom_dict,
            tags={k: str(v)[:120] for k, v in list(tags.items())[:15]},
            source="OpenStreetMap contributors (ODbL)",
            retrieved_at=datetime.utcnow(),
        )
        db.add(row)
        counts[cat] = counts.get(cat, 0) + 1
        geojson_feats.append({"geometry": geom_dict, "osm_id": osm_id, "category": cat, "name": name})

    db.commit()
    p = settings.processed_dir / "infrastructure_osm.geojson"
    hy.write_geojson(p, geojson_feats)
    vl = db.query(VectorLayer).filter_by(key="infrastructure").first()
    if vl is None:
        vl = VectorLayer(key="infrastructure")
        db.add(vl)
    vl.name = "OpenStreetMap Infrastructure & Settlements"
    vl.category = "infrastructure"
    vl.path = str(p)
    vl.feature_count = len(geojson_feats)
    vl.source = "OpenStreetMap contributors (Overpass API)"
    vl.attribution = "© OpenStreetMap contributors (ODbL)"
    db.commit()
    log(f"Stored {len(geojson_feats)} OSM features: {counts}", 1.0)
    return {"total_features": len(geojson_feats), "counts": counts}


def infrastructure_summary(db) -> dict:
    feats = db.query(InfrastructureFeature).all()
    counts: dict[str, int] = {}
    road_m = 0.0
    crs_utm = f"EPSG:{UTM_EPSG}"
    latest = None
    for f in feats:
        counts[f.category] = counts.get(f.category, 0) + 1
        if latest is None or (f.retrieved_at and f.retrieved_at > latest):
            latest = f.retrieved_at
        if f.category in ("road", "bridge") and f.geometry:
            g_utm = hy.from_wgs84(shape(f.geometry), crs_utm)
            road_m += float(g_utm.length)
    return {
        "total": len(feats),
        "counts": counts,
        "road_length_km": round(road_m / 1000.0, 2),
        "source": "OpenStreetMap contributors (ODbL)",
        "retrieved_at": latest.isoformat() if latest else None,
    }


def infrastructure_geojson(db, category: str | None = None) -> dict:
    q = db.query(InfrastructureFeature)
    if category:
        q = q.filter_by(category=category)
    rows = q.limit(5000).all()
    return {
        "type": "FeatureCollection",
        "attribution": "© OpenStreetMap contributors (ODbL)",
        "features": [
            {
                "type": "Feature",
                "geometry": r.geometry,
                "properties": {"id": r.id, "osm_id": r.osm_id, "category": r.category, "name": r.name, "tags": r.tags},
            }
            for r in rows
            if r.geometry
        ],
    }


def analyse_exposure(
    db,
    scenario_id: int | None = None,
    lake_id: int | None = None,
    buffer_m: float = 250.0,
    hand_max_m: float = 25.0,
) -> dict:
    crs_utm = f"EPSG:{UTM_EPSG}"
    hazard_zone_utm = None
    analysis_type = "flowpath_corridor"
    caveat = (
        "POTENTIAL EXPOSURE SCREENING ONLY — NOT CONFIRMED HISTORICAL DAMAGE OR HYDRAULIC PREDICTION. "
        "This screening identifies OpenStreetMap elements inside a terrain corridor (horizontal distance ≤ "
        f"{buffer_m:.0f} m from the D8 valley flow path and HAND ≤ {hand_max_m:.0f} m above nearest drainage)."
    )

    if scenario_id is not None:
        fr = (
            db.query(FloodResult)
            .filter_by(scenario_id=scenario_id)
            .filter(FloodResult.extent_geometry.isnot(None))
            .order_by(FloodResult.id.desc())
            .first()
        )
        if fr and fr.extent_geometry:
            hazard_zone_utm = hy.from_wgs84(shape(fr.extent_geometry), crs_utm)
            analysis_type = "flood_overlay"
            caveat = (
                "POTENTIAL EXPOSURE UNDER HYPOTHETICAL SCENARIO — NOT CONFIRMED HISTORICAL DAMAGE. "
                f"Computed by intersecting OpenStreetMap infrastructure with the imported {fr.model_software} flood extent for Scenario #{scenario_id}."
            )

    if hazard_zone_utm is None:
        # Build D8 flowpath corridor intersected with HAND <= hand_max_m
        if lake_id is not None:
            lk = db.get(GlacialLake, lake_id)
        else:
            lk = db.query(GlacialLake).filter(GlacialLake.name.ilike("%Chorabari%")).first()
            if lk is None:
                lk = db.query(GlacialLake).order_by(GlacialLake.id).first()
        if lk and lk.centroid:
            pt = shape(lk.centroid)
            fp = flow_path_from_point(db, lon=pt.x, lat=pt.y, name=lk.name or lk.lake_code)
            line_utm = hy.from_wgs84(shape(fp["geometry"]), crs_utm)
        else:
            # Fallback to Chorabari Lake reference coordinates
            fp = flow_path_from_point(db, lon=79.0580, lat=30.7470, name="Chorabari Lake outlet")
            line_utm = hy.from_wgs84(shape(fp["geometry"]), crs_utm)
        corridor_utm = line_utm.buffer(buffer_m)

        hand_a = db.query(RasterAsset).filter_by(kind="terrain", category="hand").order_by(RasterAsset.id.desc()).first()
        if hand_a and Path(hand_a.path).exists():
            with rasterio.open(hand_a.path) as src:
                h_arr = src.read(1, masked=True).astype("float32").filled(np.nan)
                low_mask = np.isfinite(h_arr) & (h_arr <= hand_max_m)
                polys = hy.polygonize_mask(low_mask, src.transform, min_area_m2=900.0)
                if polys:
                    hand_poly = unary_union(polys)
                    hazard_zone_utm = corridor_utm.intersection(hand_poly)
        if hazard_zone_utm is None or hazard_zone_utm.is_empty:
            hazard_zone_utm = corridor_utm

    feats = db.query(InfrastructureFeature).all()
    if not feats:
        raise ValueError("No OpenStreetMap infrastructure loaded yet. Click 'Fetch OpenStreetMap Infrastructure' first.")

    by_cat: dict[str, int] = {}
    road_len_m = 0.0
    settlements = []
    exposed_fc = []

    for f in feats:
        if not f.geometry:
            continue
        g_utm = hy.from_wgs84(shape(f.geometry), crs_utm)
        if not g_utm.intersects(hazard_zone_utm):
            continue
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
        if f.category in ("road", "bridge"):
            inter = g_utm.intersection(hazard_zone_utm)
            road_len_m += float(inter.length)
        if f.category == "settlement" and f.name:
            settlements.append(f.name)
        exposed_fc.append({
            "type": "Feature",
            "geometry": f.geometry,
            "properties": {
                "id": f.id,
                "osm_id": f.osm_id,
                "category": f.category,
                "name": f.name,
                "exposure_label": "potential_exposure",
            },
        })

    stats = {
        "buildings": by_cat.get("building", 0),
        "road_length_km": round(road_len_m / 1000.0, 2),
        "bridges": by_cat.get("bridge", 0),
        "hospitals": by_cat.get("hospital", 0),
        "schools": by_cat.get("school", 0),
        "public_infrastructure": by_cat.get("public", 0) + by_cat.get("helipad", 0) + by_cat.get("power", 0),
        "settlements": sorted(set(settlements)),
        "by_category": by_cat,
        "total_exposed_features": len(exposed_fc),
        "buffer_m": buffer_m,
        "hand_max_m": hand_max_m,
    }

    hazard_wgs = mapping(hy.to_wgs84(hazard_zone_utm, crs_utm))
    row = ExposureResult(
        scenario_id=scenario_id,
        analysis_type=analysis_type,
        statistics=stats,
        features={"type": "FeatureCollection", "features": exposed_fc[:1500], "hazard_zone": hazard_wgs},
        parameters={"scenario_id": scenario_id, "lake_id": lake_id, "buffer_m": buffer_m, "hand_max_m": hand_max_m},
    )
    db.add(row)
    db.commit()
    return {
        "id": row.id,
        "analysis_type": analysis_type,
        "statistics": stats,
        "features": {"type": "FeatureCollection", "features": exposed_fc[:1500]},
        "hazard_zone": hazard_wgs,
        "caveat": caveat,
    }

