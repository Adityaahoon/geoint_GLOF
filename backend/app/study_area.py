"""Kedarnath study-area definition.

The analysis extent is a bounding box covering the Chorabari Glacier, Chorabari Lake
(Gandhi Sarovar), Kedarnath, Rambara, Gaurikund, Sonprayag and the upper Mandakini corridor.

Reference-point coordinates below are APPROXIMATE gazetteer positions used only for map
orientation. When OpenStreetMap data is fetched (scripts/fetch_osm.py) the OSM place nodes
are stored in the infrastructure table and preferred by the frontend.
"""
from __future__ import annotations

from shapely.geometry import box, mapping

# lon_min, lat_min, lon_max, lat_max (EPSG:4326)
STUDY_BBOX = (78.92, 30.58, 79.14, 30.82)
UTM_EPSG = 32644

SUB_REGIONS = {
    "full_aoi": {
        "name": "Upper Mandakini basin (full AOI)",
        "bbox": STUDY_BBOX,
    },
    "chorabari": {
        "name": "Chorabari Glacier & Gandhi Sarovar zone",
        "bbox": (79.035, 30.735, 79.095, 30.800),
    },
    "kedarnath_valley": {
        "name": "Kedarnath township & valley floor",
        "bbox": (79.040, 30.715, 79.090, 30.750),
    },
    "mandakini_corridor": {
        "name": "Mandakini corridor (Kedarnath – Sonprayag)",
        "bbox": (78.980, 30.620, 79.085, 30.745),
    },
}

REFERENCE_POINTS = [
    {"name": "Chorabari Lake (Gandhi Sarovar)", "lat": 30.7470, "lon": 79.0580, "type": "lake"},
    {"name": "Chorabari Glacier (snout area)", "lat": 30.7545, "lon": 79.0605, "type": "glacier"},
    {"name": "Kedarnath", "lat": 30.7346, "lon": 79.0669, "type": "settlement"},
    {"name": "Rambara (pre-2013 location)", "lat": 30.7080, "lon": 79.0490, "type": "settlement"},
    {"name": "Gaurikund", "lat": 30.6530, "lon": 79.0260, "type": "settlement"},
    {"name": "Sonprayag", "lat": 30.6330, "lon": 78.9990, "type": "settlement"},
]

TIMELINE_PERIODS = [
    {"key": "baseline", "label": "Pre-disaster baseline", "start": 2000, "end": 2012},
    {"key": "disaster", "label": "June 2013 Kedarnath disaster", "start": 2013, "end": 2013},
    {"key": "recovery", "label": "Post-disaster recovery", "start": 2014, "end": 2019},
    {"key": "recent", "label": "Recent monitoring (2026 = year-to-date)", "start": 2020, "end": 2026},
]

# Comparisons mandated by the research design
STANDARD_COMPARISONS = [(2000, 2012), (2012, 2013), (2013, 2015), (2015, 2020), (2020, 2024), (2024, 2026)]

DISASTER_CONTEXT = (
    "The June 2013 Kedarnath disaster (16–17 June 2013) resulted from a combination of "
    "extreme, early-onset monsoon rainfall, rapid snowmelt, landslides and debris flows, and "
    "the breach/overflow of Chorabari Lake (Gandhi Sarovar). It must not be attributed to a "
    "single GLOF mechanism. This platform separates GLOF-related hazards, rainfall-triggered "
    "flash floods, landslides/debris flows and combined downstream exposure."
)


def region_geometry(region: str = "full_aoi") -> dict:
    r = SUB_REGIONS.get(region)
    if r is None:
        raise KeyError(f"Unknown region '{region}'. Options: {list(SUB_REGIONS)}")
    return mapping(box(*r["bbox"]))


def region_bbox(region: str = "full_aoi") -> tuple[float, float, float, float]:
    return SUB_REGIONS[region]["bbox"]

