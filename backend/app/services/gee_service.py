"""Google Earth Engine service.

Authentication (server side only – credentials never reach the browser):
  1. Service account (recommended for deployment):
       GG_GEE_SERVICE_ACCOUNT=<name>@<project>.iam.gserviceaccount.com
       GG_GEE_PRIVATE_KEY_FILE=/secure/path/key.json
       GG_GEE_PROJECT=<cloud-project-id>
     The service account must be registered for Earth Engine on that project.
  2. User credentials (development): run `earthengine authenticate` once, then set
     GG_GEE_PROJECT. Stored credentials in ~/.config/earthengine are used.

All functions return server-side ee objects; nothing is computed until getInfo()/export.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ..config import get_settings
from ..study_area import region_geometry
from .sensors import L7_SLC_FAILURE, LANDSAT_MISSIONS, QA_BITS, SENSORS

logger = logging.getLogger("glacioguard.gee")

_state: dict[str, Any] = {"initialized": False, "error": None, "mode": None}


def _ee():
    import ee  # imported lazily so the API runs without earthengine-api configured
    return ee


def initialize(force: bool = False) -> dict:
    """Initialise Earth Engine; returns a status dict (never raises)."""
    if _state["initialized"] and not force:
        return status()
    s = get_settings()
    try:
        ee = _ee()
        if s.gee_service_account and s.gee_private_key_file:
            creds = ee.ServiceAccountCredentials(s.gee_service_account, s.gee_private_key_file)
            ee.Initialize(creds, project=s.gee_project)
            _state["mode"] = "service_account"
        else:
            if not s.gee_project:
                raise RuntimeError(
                    "Earth Engine not configured. Set GG_GEE_PROJECT (and optionally "
                    "GG_GEE_SERVICE_ACCOUNT + GG_GEE_PRIVATE_KEY_FILE) in .env, or run "
                    "`earthengine authenticate` for user credentials.")
            ee.Initialize(project=s.gee_project)
            _state["mode"] = "user_credentials"
        ee.Number(1).getInfo()  # round-trip check
        _state.update(initialized=True, error=None)
    except Exception as exc:  # noqa: BLE001
        _state.update(initialized=False, error=str(exc))
        logger.warning("Earth Engine unavailable: %s", exc)
    return status()


def status() -> dict:
    return {"available": _state["initialized"], "mode": _state["mode"], "error": _state["error"],
            "project": get_settings().gee_project}


def require() -> Any:
    if not _state["initialized"]:
        initialize()
    if not _state["initialized"]:
        raise RuntimeError(f"Google Earth Engine is not available: {_state['error']}")
    return _ee()


def aoi(region: str = "full_aoi"):
    ee = require()
    return ee.Geometry(region_geometry(region))


# ----------------------------------------------------------------------------- masking

def _mask_landsat(image, mission: str):
    """Apply QA_PIXEL cloud/shadow/fill mask and C2 L2 scale factors; rename to common bands."""
    ee = _ee()
    spec = SENSORS[mission]
    qa = image.select("QA_PIXEL")
    bad = (qa.bitwiseAnd(1 << QA_BITS["fill"]).neq(0)
           .Or(qa.bitwiseAnd(1 << QA_BITS["dilated_cloud"]).neq(0))
           .Or(qa.bitwiseAnd(1 << QA_BITS["cloud"]).neq(0))
           .Or(qa.bitwiseAnd(1 << QA_BITS["cloud_shadow"]).neq(0)))
    if mission in ("landsat8", "landsat9"):
        bad = bad.Or(qa.bitwiseAnd(1 << QA_BITS["cirrus"]).neq(0))
    sat = image.select("QA_RADSAT").eq(0)  # drop saturated pixels
    src = [spec.gee_bands[b] for b in ("blue", "green", "red", "nir", "swir1", "swir2")]
    optical = (image.select(src, ["blue", "green", "red", "nir", "swir1", "swir2"])
               .multiply(spec.scale).add(spec.offset))
    # SLC-off gaps are fill pixels -> masked by the fill bit (never treated as valid).
    return (optical.updateMask(bad.Not()).updateMask(sat)
            .set("mission", mission).copyProperties(image, ["system:time_start", "CLOUD_COVER", "LANDSAT_PRODUCT_ID"]))


def _mask_s2(image):
    ee = _ee()
    spec = SENSORS["sentinel2"]
    scl = image.select("SCL")
    good = scl.neq(0)
    for cls in (1, 3, 8, 9, 10):
        good = good.And(scl.neq(cls))
    src = [spec.gee_bands[b] for b in ("blue", "green", "red", "nir", "swir1", "swir2")]
    optical = image.select(src, ["blue", "green", "red", "nir", "swir1", "swir2"]).multiply(spec.scale)
    return optical.updateMask(good).set("mission", "sentinel2").copyProperties(
        image, ["system:time_start", "CLOUDY_PIXEL_PERCENTAGE", "PRODUCT_ID"])


# ----------------------------------------------------------------------------- 1. collections

def get_landsat_collection(mission: str, start: str, end: str, region: str = "full_aoi",
                           max_cloud: float = 60.0, months: tuple[int, int] | None = None):
    """1. Landsat 5/7/8/9 Collection 2 Level-2 SR, cloud-masked, scaled, harmonised band names."""
    ee = require()
    if mission not in LANDSAT_MISSIONS:
        raise ValueError(f"{mission} is not a Landsat mission")
    spec = SENSORS[mission]
    col = (ee.ImageCollection(spec.gee_collection).filterBounds(aoi(region))
           .filterDate(start, end).filter(ee.Filter.lt("CLOUD_COVER", max_cloud)))
    if months:
        col = col.filter(ee.Filter.calendarRange(months[0], months[1], "month"))
    return col.map(lambda img: _mask_landsat(img, mission))


def get_sentinel2_collection(start: str, end: str, region: str = "full_aoi", max_cloud: float = 60.0,
                             months: tuple[int, int] | None = None):
    """2. Sentinel-2 L2A (harmonised; baseline-04.00 offset removed by GEE) with SCL masking."""
    ee = require()
    col = (ee.ImageCollection(SENSORS["sentinel2"].gee_collection).filterBounds(aoi(region))
           .filterDate(start, end).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud)))
    if months:
        col = col.filter(ee.Filter.calendarRange(months[0], months[1], "month"))
    return col.map(_mask_s2)


def get_sentinel1_collection(start: str, end: str, region: str = "full_aoi", orbit: str | None = None):
    """3. Sentinel-1 GRD IW, VV+VH, 10 m. Values are dB (GEE applies thermal noise removal,
    radiometric calibration and terrain correction with SRTM/ASTER DEM)."""
    ee = require()
    col = (ee.ImageCollection(SENSORS["sentinel1"].gee_collection).filterBounds(aoi(region))
           .filterDate(start, end).filter(ee.Filter.eq("instrumentMode", "IW"))
           .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
           .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")))
    if orbit:
        col = col.filter(ee.Filter.eq("orbitProperties_pass", orbit))
    return col.select(["VV", "VH", "angle"])


def get_dem(source: str = "copernicus"):
    """4. DEM: Copernicus GLO-30 (default) or SRTM 30 m (USGS/SRTMGL1_003)."""
    ee = require()
    if source == "srtm":
        return ee.Image("USGS/SRTMGL1_003").select("elevation").rename("elevation")
    return ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic().rename("elevation")


# ----------------------------------------------------------------------------- 5–9 indices

def calculate_ndwi(image):
    """5. NDWI (McFeeters 1996) = (green − nir)/(green + nir)."""
    return image.normalizedDifference(["green", "nir"]).rename("ndwi")


def calculate_mndwi(image):
    """6. MNDWI (Xu 2006) = (green − swir1)/(green + swir1)."""
    return image.normalizedDifference(["green", "swir1"]).rename("mndwi")


def calculate_ndvi(image):
    """7. NDVI = (nir − red)/(nir + red)."""
    return image.normalizedDifference(["nir", "red"]).rename("ndvi")


def calculate_nbr(image):
    """8. NBR = (nir − swir2)/(nir + swir2) (used here for exposed-ground/debris change)."""
    return image.normalizedDifference(["nir", "swir2"]).rename("nbr")


def calculate_snow_indices(image, ndsi_threshold: float = 0.4):
    """9. NDSI and snow/ice mask (NDSI > thr, NIR > 0.11 to exclude water)."""
    ndsi = image.normalizedDifference(["green", "swir1"]).rename("ndsi")
    mask = ndsi.gt(ndsi_threshold).And(image.select("nir").gt(0.11)).And(
        image.select("green").gt(0.10)).rename("snow_ice")
    return ndsi.addBands(mask)


# ----------------------------------------------------------------------------- 10. composites

def generate_annual_composite(year: int, mission: str, region: str = "full_aoi",
                              season: tuple[str, str] = ("09-15", "11-15"), max_cloud: float = 60.0):
    """10. Seasonal-window median composite for one year.

    Uses the same calendar window every year (default 15 Sep – 15 Nov, post-monsoon:
    minimum cloud and before persistent winter snow) to reduce seasonal bias. For 2026
    the window is truncated at today's date (year-to-date).
    Returns (composite_image, metadata_dict).
    """
    ee = require()
    start = f"{year}-{season[0]}"
    end_d = date.fromisoformat(f"{year}-{season[1]}")
    end_d = min(end_d, date.today())
    end = end_d.isoformat()
    if mission == "sentinel2":
        col = get_sentinel2_collection(start, end, region, max_cloud)
        scale = 20
    else:
        col = get_landsat_collection(mission, start, end, region, max_cloud)
        scale = 30
    comp = col.median().clip(aoi(region))
    valid = col.select("green").count().rename("valid_obs")
    comp = comp.addBands(valid)
    flags = []
    if mission == "landsat7" and date(year, 1, 1) > L7_SLC_FAILURE:
        flags.append("landsat7_slc_off_gaps")
    if year == date.today().year:
        flags.append("year_to_date")
    meta = {"year": year, "mission": mission, "window": [start, end], "scale_m": scale,
            "scene_count": col.size(), "dates": col.aggregate_array("system:time_start"),
            "quality_flags": flags}
    return comp, meta


def calculate_water_area(image, region: str = "full_aoi", index: str = "mndwi",
                         threshold: float = 0.0, scale: int = 30) -> dict:
    """11. Water area (ha) from an index threshold, computed in an equal-area sense via
    ee.Image.pixelArea() (m² per pixel on the ellipsoid)."""
    ee = require()
    idx = calculate_mndwi(image) if index == "mndwi" else calculate_ndwi(image)
    water = idx.gt(threshold)
    area = water.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=aoi(region), scale=scale, maxPixels=1e10)
    total = ee.Image.pixelArea().updateMask(idx.mask()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=aoi(region), scale=scale, maxPixels=1e10)
    res = ee.Dictionary({"water_m2": area.values().get(0), "valid_m2": total.values().get(0)}).getInfo()
    res["water_ha"] = (res.get("water_m2") or 0) / 1e4
    res["threshold"] = threshold
    res["index"] = index
    return res


def export_geotiff(image, description: str, region: str = "full_aoi", scale: int = 30,
                   crs: str = "EPSG:32644", folder: str | None = None) -> dict:
    """12. Export to Google Drive as Cloud-Optimised GeoTIFF; returns task id/status."""
    ee = require()
    task = ee.batch.Export.image.toDrive(
        image=image.toFloat(), description=description[:100], folder=folder or get_settings().gee_drive_folder,
        region=aoi(region), scale=scale, crs=crs, maxPixels=1e10, fileFormat="GeoTIFF",
        formatOptions={"cloudOptimized": True})
    task.start()
    return {"task_id": task.id, "state": task.status().get("state"), "description": description}


def export_status(task_id: str) -> dict:
    ee = require()
    for t in ee.batch.Task.list():
        if t.id == task_id:
            return t.status()
    return {"id": task_id, "state": "UNKNOWN"}


def generate_change_detection_map(img_a, img_b, index: str = "mndwi", threshold: float = 0.0):
    """13. Index difference (b − a) plus categorical transition map:
    0 = stable non-target, 1 = stable target, 2 = gain (new), 3 = loss."""
    fn = {"mndwi": calculate_mndwi, "ndwi": calculate_ndwi, "ndvi": calculate_ndvi,
          "nbr": calculate_nbr}[index]
    a = fn(img_a)
    b = fn(img_b)
    diff = b.subtract(a).rename("difference")
    ma, mb = a.gt(threshold), b.gt(threshold)
    trans = (ma.And(mb).multiply(1).add(ma.Not().And(mb).multiply(2)).add(ma.And(mb.Not()).multiply(3))
             .rename("transition"))
    return diff.addBands(trans)


def thumbnail_url(image, bands: list[str], vmin: float, vmax: float, region: str = "full_aoi",
                  dimensions: int = 1024, palette: list[str] | None = None) -> str:
    vis: dict[str, Any] = {"bands": bands, "min": vmin, "max": vmax, "dimensions": dimensions,
                           "region": aoi(region), "format": "png"}
    if palette:
        vis["palette"] = palette
    return image.getThumbURL(vis)


def collection_summary(mission: str, start: str, end: str, region: str = "full_aoi",
                       max_cloud: float = 60.0) -> list[dict]:
    ee = require()
    if mission == "sentinel2":
        raw = (ee.ImageCollection(SENSORS["sentinel2"].gee_collection).filterBounds(aoi(region))
               .filterDate(start, end).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud)))
        cloud_prop = "CLOUDY_PIXEL_PERCENTAGE"
    elif mission == "sentinel1":
        raw = get_sentinel1_collection(start, end, region)
        cloud_prop = None
    else:
        raw = (ee.ImageCollection(SENSORS[mission].gee_collection).filterBounds(aoi(region))
               .filterDate(start, end).filter(ee.Filter.lt("CLOUD_COVER", max_cloud)))
        cloud_prop = "CLOUD_COVER"
    ids = raw.aggregate_array("system:index").getInfo()
    times = raw.aggregate_array("system:time_start").getInfo()
    clouds = raw.aggregate_array(cloud_prop).getInfo() if cloud_prop else [None] * len(ids)
    return [{"scene_id": i, "time_ms": t, "cloud_cover": c} for i, t, c in zip(ids, times, clouds)]


def chirps_monthly(start: str, end: str, region: str = "kedarnath_valley") -> list[dict]:
    """Area-mean monthly CHIRPS precipitation (UCSB-CHG/CHIRPS/DAILY summed per month)."""
    ee = require()
    col = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(start, end).select("precipitation")
    geom = aoi(region)
    s, e = ee.Date(start), ee.Date(end)
    n = e.difference(s, "month").round()

    def per_month(i):
        d0 = s.advance(i, "month")
        img = col.filterDate(d0, d0.advance(1, "month")).sum()
        v = img.reduceRegion(ee.Reducer.mean(), geom, 5566).get("precipitation")
        return ee.Feature(None, {"date": d0.format("YYYY-MM-dd"), "precipitation_mm": v})

    fc = ee.FeatureCollection(ee.List.sequence(0, n.subtract(1)).map(per_month))
    return [f["properties"] for f in fc.getInfo()["features"]]


def gpm_daily(start: str, end: str, region: str = "kedarnath_valley") -> list[dict]:
    """Area-mean daily GPM IMERG V07 final-run precipitation (mm/day)."""
    ee = require()
    col = ee.ImageCollection("NASA/GPM_L3/IMERG_V07").filterDate(start, end).select("precipitation")
    geom = aoi(region)
    s, e = ee.Date(start), ee.Date(end)
    n = e.difference(s, "day").round()

    def per_day(i):
        d0 = s.advance(i, "day")
        img = col.filterDate(d0, d0.advance(1, "day")).mean().multiply(24)  # mm/hr -> mm/day
        v = img.reduceRegion(ee.Reducer.mean(), geom, 11132).get("precipitation")
        return ee.Feature(None, {"date": d0.format("YYYY-MM-dd"), "precipitation_mm": v})

    fc = ee.FeatureCollection(ee.List.sequence(0, n.subtract(1)).map(per_day))
    return [f["properties"] for f in fc.getInfo()["features"]]

