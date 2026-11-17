"""Open-data satellite provider (no credentials required).

Mirrors the Earth Engine workflow locally using public STAC catalogues of the SAME
source products, read as Cloud-Optimised GeoTIFFs with windowed HTTP range requests:

- Landsat 5/7/8/9 Collection 2 Level-2 (Tier 1)  -> Microsoft Planetary Computer STAC
  (identical USGS product to GEE LANDSAT/LXXX/C02/T1_L2)
- Sentinel-2 L2A                                  -> Element 84 Earth Search STAC (AWS open data)
- Copernicus DEM GLO-30                           -> AWS open data (copernicus-dem-30m)

Every scene's ID and acquisition time is recorded; per-pixel QA masks are applied before
compositing; Landsat 7 SLC-off gaps (fill) are NoData.
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from ..config import get_settings
from ..study_area import region_bbox
from .raster_service import aoi_grid, write_raster
from .sensors import L7_SLC_FAILURE, LANDSAT_MISSIONS, QA_BITS, S2_SCL_MASK, SENSORS

logger = logging.getLogger("glacioguard.stac")
settings = get_settings()

GDAL_ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
                GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE",
                GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                AWS_NO_SIGN_REQUEST="YES")
OPTICAL_BANDS = ("blue", "green", "red", "nir", "swir1", "swir2")


def _client(mission: str):
    from pystac_client import Client
    if mission in LANDSAT_MISSIONS or mission == "sentinel1":
        import planetary_computer
        return Client.open(settings.pc_stac_url, modifier=planetary_computer.sign_inplace), "planetary_computer"
    return Client.open(settings.earth_search_url), "earth_search"


def search_scenes(mission: str, start: str, end: str, region: str = "full_aoi",
                  max_cloud: float = 60.0, limit: int = 200) -> list[dict]:
    """Search scenes; returns JSON-serialisable metadata (+ the pystac item under '_item')."""
    spec = SENSORS[mission]
    client, provider = _client(mission)
    bbox = list(region_bbox(region))
    kw: dict[str, Any] = dict(collections=[spec.stac_collection], bbox=bbox, datetime=f"{start}/{end}",
                              max_items=limit)
    if mission in LANDSAT_MISSIONS:
        kw["query"] = {"platform": {"in": [spec.stac_platform]}, "eo:cloud_cover": {"lt": max_cloud},
                       "landsat:collection_category": {"eq": "T1"}}
    elif mission == "sentinel2":
        kw["query"] = {"eo:cloud_cover": {"lt": max_cloud}}
    out = []
    for it in client.search(**kw).items():
        p = it.properties
        dt = it.datetime or datetime.fromisoformat(p["start_datetime"].replace("Z", "+00:00"))
        rec = {"scene_id": it.id, "provider": provider, "mission": mission, "collection": spec.stac_collection,
               "datetime": dt.isoformat(), "cloud_cover": p.get("eo:cloud_cover"),
               "footprint": it.geometry, "platform": p.get("platform"),
               "properties": {k: v for k, v in p.items() if isinstance(v, (str, int, float, bool)) and len(str(v)) < 200},
               "_item": it}
        if mission == "landsat7" and dt.date() > L7_SLC_FAILURE:
            rec["quality_flags"] = ["landsat7_slc_off_gaps"]
        if mission in LANDSAT_MISSIONS:
            rec["preview_url"] = it.assets["rendered_preview"].href if "rendered_preview" in it.assets else None
        elif "thumbnail" in it.assets:
            rec["preview_url"] = it.assets["thumbnail"].href
        out.append(rec)
    out.sort(key=lambda r: r["datetime"])
    return out


def _read_asset(href: str, transform, width: int, height: int, crs, resampling: Resampling) -> tuple[np.ndarray, Any]:
    with rasterio.Env(**GDAL_ENV):
        with rasterio.open(href) as src:
            # Sources without a NoData value (e.g. Copernicus DEM) would otherwise be padded with 0
            # outside their footprint – use an explicit sentinel so mosaicking is correct.
            nodata = src.nodata if src.nodata is not None else -32768.0
            with WarpedVRT(src, crs=crs, transform=transform, width=width, height=height,
                           resampling=resampling, src_nodata=src.nodata, nodata=nodata) as vrt:
                return vrt.read(1), nodata


def _scale_offset(asset, spec) -> tuple[float, float]:
    rb = (asset.extra_fields.get("raster:bands") or [{}])[0]
    return float(rb.get("scale", spec.scale)), float(rb.get("offset", spec.offset))


def read_scene(rec: dict, region: str, resolution: float) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """Read one scene onto the fixed analysis grid. Returns (bands reflectance, valid mask)."""
    mission = rec["mission"]
    spec = SENSORS[mission]
    item = rec["_item"]
    transform, width, height, crs = aoi_grid(region, resolution)
    bands: dict[str, np.ndarray] = {}
    if mission in LANDSAT_MISSIONS:
        qa, _ = _read_asset(item.assets["qa_pixel"].href, transform, width, height, crs, Resampling.nearest)
        qa = qa.astype("uint16")
        bad = np.zeros(qa.shape, bool)
        for b in ("fill", "dilated_cloud", "cloud", "cloud_shadow"):
            bad |= (qa & (1 << QA_BITS[b])) != 0
        if mission in ("landsat8", "landsat9"):
            bad |= (qa & (1 << QA_BITS["cirrus"])) != 0
        bad |= qa == 0  # outside footprint / SLC gap
        if "qa_radsat" in item.assets:
            rs, _ = _read_asset(item.assets["qa_radsat"].href, transform, width, height, crs, Resampling.nearest)
            bad |= rs != 0
        valid = ~bad
    else:
        scl, _ = _read_asset(item.assets["scl"].href, transform, width, height, crs, Resampling.nearest)
        valid = ~np.isin(scl, list(S2_SCL_MASK.keys()))
    for b in OPTICAL_BANDS:
        asset = item.assets[spec.stac_assets[b]]
        raw, nodata = _read_asset(asset.href, transform, width, height, crs, Resampling.bilinear)
        scale, offset = _scale_offset(asset, spec)
        refl = raw.astype("float32") * scale + offset
        if nodata is not None:
            valid &= raw != nodata
        bands[b] = refl
    # physically implausible reflectance -> invalid
    for b in OPTICAL_BANDS:
        valid &= (bands[b] > -0.05) & (bands[b] < 1.6)
    for b in OPTICAL_BANDS:
        bands[b] = np.where(valid, np.clip(bands[b], 0, 1.6), np.nan).astype("float32")
    return bands, valid


def season_window(year: int, season: tuple[str, str]) -> tuple[str, str, list[str]]:
    start = date.fromisoformat(f"{year}-{season[0]}")
    end = date.fromisoformat(f"{year}-{season[1]}")
    flags = []
    if end > date.today():
        end = date.today()
        flags.append("year_to_date")
    if start > date.today():
        raise ValueError(f"Seasonal window for {year} has not started yet")
    return start.isoformat(), end.isoformat(), flags


def build_composite(year: int, mission: str, region: str = "full_aoi", season: tuple[str, str] = ("09-15", "11-15"),
                    resolution: float | None = None, max_cloud: float = 60.0, max_scenes: int = 8,
                    log=lambda m, p=None: None) -> dict:
    """Seasonal median composite on the fixed UTM grid. Writes a 7-band GeoTIFF
    (blue..swir2 reflectance + valid observation count) and returns metadata."""
    spec = SENSORS[mission]
    resolution = resolution or (20.0 if mission == "sentinel2" else 30.0)
    start, end, flags = season_window(year, season)
    scenes = search_scenes(mission, start, end, region, max_cloud)
    if not scenes:
        return {"year": year, "mission": mission, "status": "no_data", "window": [start, end],
                "message": f"No {spec.label} scenes with cloud < {max_cloud}% in {start}..{end}"}
    # Score candidate scenes by AOI footprint overlap and low cloud cover
    from shapely.geometry import box as shp_box, shape as shp_shape
    aoi_poly = shp_box(*region_bbox(region))
    scored = []
    for r in scenes:
        try:
            ov = shp_shape(r["footprint"]).intersection(aoi_poly).area / max(aoi_poly.area, 1e-9) if r.get("footprint") else 1.0
        except Exception:
            ov = 1.0
        if ov < 0.20:
            continue
        cc = r["cloud_cover"] if r["cloud_cover"] is not None else 50.0
        scored.append((cc - ov * 35.0, r))
    if not scored:
        scored = [(r["cloud_cover"] or 50.0, r) for r in scenes]
    scored.sort(key=lambda x: x[0])
    scenes = [r for _, r in scored[:max_scenes]]
    transform, width, height, crs = aoi_grid(region, resolution)
    stack = {b: [] for b in OPTICAL_BANDS}
    used = []
    for i, rec in enumerate(scenes):
        try:
            log(f"Reading {rec['scene_id']} ({rec['datetime'][:10]}, cloud {rec['cloud_cover']})",
                None)
            bands, valid = read_scene(rec, region, resolution)
        except Exception as exc:  # noqa: BLE001 – record and continue
            log(f"  skipped {rec['scene_id']}: {exc}")
            continue
        vf = float(valid.mean())
        if vf < 0.02:
            log(f"  skipped {rec['scene_id']}: only {vf:.1%} valid pixels in AOI")
            continue
        for b in OPTICAL_BANDS:
            stack[b].append(bands[b])
        used.append({"scene_id": rec["scene_id"], "datetime": rec["datetime"], "cloud_cover": rec["cloud_cover"],
                     "valid_fraction_in_aoi": round(vf, 4), "provider": rec["provider"],
                     "footprint": rec["footprint"], "properties": rec["properties"]})
    if not used:
        return {"year": year, "mission": mission, "status": "no_valid_data", "window": [start, end],
                "message": "Scenes found but none had valid (cloud-free) pixels over the AOI"}
    comp = {}
    with np.errstate(all="ignore"):
        for b in OPTICAL_BANDS:
            arr = np.stack(stack[b])
            comp[b] = np.nanmedian(arr, axis=0).astype("float32")
        count = np.sum(np.isfinite(np.stack(stack["green"])), axis=0).astype("float32")
    del stack
    valid_fraction = float((count > 0).mean())
    if mission == "landsat7" and date(year, 1, 1) > L7_SLC_FAILURE:
        flags.append("landsat7_slc_off_gaps")
    if valid_fraction < 0.8:
        flags.append("low_valid_coverage")
    if len(used) < 2:
        flags.append("single_scene_composite")
    out = settings.processed_dir / "composites" / f"composite_{region}_{mission}_{year}.tif"
    write_raster(out, [comp[b] for b in OPTICAL_BANDS] + [count], transform, crs,
                 band_names=list(OPTICAL_BANDS) + ["valid_obs"],
                 tags={"mission": mission, "year": year, "window": f"{start}/{end}", "method": "per-pixel median",
                       "scenes": ";".join(u["scene_id"] for u in used), "source": spec.citation})
    return {"year": year, "mission": mission, "region": region, "status": "ok", "path": str(out),
            "window": [start, end], "resolution_m": resolution, "scene_count": len(used), "scenes": used,
            "valid_fraction": valid_fraction, "quality_flags": flags, "max_cloud": max_cloud,
            "provider": used[0]["provider"], "source": spec.citation}


# ----------------------------------------------------------------------------- DEM

COP_DEM_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
               "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif")
COP_DEM_CITATION = ("European Space Agency (2024). Copernicus Global Digital Elevation Model GLO-30. "
                    "https://doi.org/10.5270/ESA-c5d3d65. Produced using Copernicus WorldDEM-30 © DLR e.V. "
                    "2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by "
                    "the European Union and ESA; all rights reserved.")


def fetch_copernicus_dem(region: str = "full_aoi", resolution: float = 30.0) -> dict:
    """Download Copernicus GLO-30 tiles covering the region and warp to the UTM analysis grid."""
    bbox = region_bbox(region)
    transform, width, height, crs = aoi_grid(region, resolution)
    out_arr = np.full((height, width), np.nan, dtype="float32")
    tiles = []
    for lat in range(math.floor(bbox[1]), math.floor(bbox[3]) + 1):
        for lon in range(math.floor(bbox[0]), math.floor(bbox[2]) + 1):
            url = COP_DEM_URL.format(ns="N" if lat >= 0 else "S", lat=abs(lat), ew="E" if lon >= 0 else "W", lon=abs(lon))
            arr, nodata = _read_asset("/vsicurl/" + url, transform, width, height, crs, Resampling.bilinear)
            arr = arr.astype("float32")
            if nodata is not None:
                arr[arr == nodata] = np.nan
            arr[arr < -100] = np.nan
            fill = np.isnan(out_arr) & np.isfinite(arr)
            out_arr[fill] = arr[fill]
            tiles.append(url)
    out = settings.raw_dir / "dem" / f"copernicus_glo30_{region}_utm44n_{int(resolution)}m.tif"
    write_raster(out, out_arr, transform, crs, band_names=["elevation"],
                 tags={"source": "Copernicus DEM GLO-30", "tiles": ";".join(tiles), "vertical_datum": "EGM2008"})
    return {"path": str(out), "tiles": tiles, "source": COP_DEM_CITATION,
            "valid_fraction": float(np.isfinite(out_arr).mean()),
            "notes": ["GLO-30 is a Digital Surface Model (X-band InSAR, TanDEM-X 2011–2015 acquisitions); "
                      "glacier surfaces reflect that epoch.", "Heights are orthometric (EGM2008)."]}
