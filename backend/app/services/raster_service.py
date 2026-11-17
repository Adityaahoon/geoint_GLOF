"""Raster utilities built on Rasterio/GDAL.

Design rules
- Original uploads are never modified; every operation writes a new file under
  data/processed and registers a new RasterAsset with a `parent_id` and processing params.
- Statistics are computed block-wise (or from overviews for very large rasters) so whole
  high-resolution rasters are never loaded into memory unnecessarily.
- All area/distance work uses the projected UTM 44N grid (EPSG:32644).
"""
from __future__ import annotations

import io
import math
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.mask import mask as rio_mask
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, transform_bounds, transform_geom
from rasterio.windows import Window
from shapely.geometry import box, mapping, shape

from ..config import get_settings
from ..study_area import UTM_EPSG, region_bbox

settings = get_settings()

GTIFF_PROFILE = {"driver": "GTiff", "tiled": True, "blockxsize": 256, "blockysize": 256,
                 "compress": "deflate", "predictor": 2, "BIGTIFF": "IF_SAFER"}
MAX_IN_MEMORY_PIXELS = 25_000_000


def aoi_grid(region: str = "full_aoi", resolution: float = 30.0, epsg: int = UTM_EPSG):
    """Fixed analysis grid (transform, width, height, crs) for a region in UTM.

    Snapped to multiples of the resolution so every product aligns pixel-for-pixel."""
    bbox = region_bbox(region)
    left, bottom, right, top = transform_bounds("EPSG:4326", f"EPSG:{epsg}", *bbox, densify_pts=21)
    left = math.floor(left / resolution) * resolution
    top = math.ceil(top / resolution) * resolution
    right = math.ceil(right / resolution) * resolution
    bottom = math.floor(bottom / resolution) * resolution
    width = int(round((right - left) / resolution))
    height = int(round((top - bottom) / resolution))
    return from_origin(left, top, resolution, resolution), width, height, CRS.from_epsg(epsg)


def write_raster(path: Path, arrays: np.ndarray | list[np.ndarray], transform, crs, nodata=np.nan,
                 band_names: list[str] | None = None, dtype: str = "float32", tags: dict | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(arrays, np.ndarray) and arrays.ndim == 2:
        arrays = [arrays]
    arr = np.stack([np.asarray(a) for a in arrays]).astype(dtype)
    profile = dict(GTIFF_PROFILE, count=arr.shape[0], height=arr.shape[1], width=arr.shape[2],
                   dtype=dtype, crs=crs, transform=transform, nodata=nodata)
    if arr.shape[1] < 256 or arr.shape[2] < 256:
        profile.update(tiled=False)
        profile.pop("blockxsize"), profile.pop("blockysize")
    if dtype.startswith("uint") or dtype.startswith("int"):
        profile["predictor"] = 2
    else:
        profile["predictor"] = 3
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr)
        if band_names:
            for i, n in enumerate(band_names, 1):
                dst.set_band_description(i, n)
        if tags:
            dst.update_tags(**{k: str(v) for k, v in tags.items()})
    return path


def bounds_polygon_wgs84(src) -> dict | None:
    if src.crs is None:
        return None
    b = transform_bounds(src.crs, "EPSG:4326", *src.bounds, densify_pts=21)
    return mapping(box(*b))


def _block_stats(src, band: int) -> dict:
    """Streaming min/max/mean/std/valid-count over internal blocks or a decimated read."""
    n_pix = src.width * src.height
    nodata = src.nodata
    if n_pix > MAX_IN_MEMORY_PIXELS * 4:
        # Very large: use a decimated read (overviews if present) – flagged as approximate.
        factor = int(math.ceil(math.sqrt(n_pix / MAX_IN_MEMORY_PIXELS)))
        data = src.read(band, out_shape=(src.height // factor, src.width // factor),
                        resampling=Resampling.nearest, masked=True)
        windows = [(None, data)]
        approx = True
    else:
        windows = ((w, None) for _, w in src.block_windows(band))
        approx = False
    count = 0
    s = 0.0
    s2 = 0.0
    vmin, vmax = math.inf, -math.inf
    for w, pre in windows:
        a = pre if pre is not None else src.read(band, window=w, masked=True)
        a = np.ma.masked_invalid(a.astype("float64"))
        if nodata is not None and not (isinstance(nodata, float) and math.isnan(nodata)):
            a = np.ma.masked_equal(a, nodata)
        v = a.compressed()
        if v.size == 0:
            continue
        count += v.size
        s += v.sum()
        s2 += (v ** 2).sum()
        vmin = min(vmin, float(v.min()))
        vmax = max(vmax, float(v.max()))
    if count == 0:
        return {"band": band, "valid_pixels": 0, "min": None, "max": None, "mean": None, "std": None,
                "approximate": approx}
    mean = s / count
    std = math.sqrt(max(s2 / count - mean ** 2, 0.0))
    total = n_pix if not approx else windows[0][1].size
    return {"band": band, "min": vmin, "max": vmax, "mean": mean, "std": std, "valid_pixels": int(count),
            "valid_fraction": count / total, "approximate": approx}


def raster_metadata(path: str | Path, with_stats: bool = True) -> dict[str, Any]:
    with rasterio.open(path) as src:
        crs = src.crs
        meta: dict[str, Any] = {
            "driver": src.driver, "width": src.width, "height": src.height, "band_count": src.count,
            "dtypes": list(src.dtypes), "crs": crs.to_string() if crs else None,
            "crs_wkt_name": (crs.to_wkt().split('"')[1] if crs else None),
            "is_projected": bool(crs and crs.is_projected), "epsg": crs.to_epsg() if crs else None,
            "transform": list(src.transform)[:6], "resolution": [abs(src.res[0]), abs(src.res[1])],
            "units": (crs.linear_units if crs and crs.is_projected else "degrees" if crs else None),
            "bounds": list(src.bounds), "nodata": src.nodata,
            "band_descriptions": [d for d in src.descriptions], "tags": src.tags(),
            "overviews": [src.overviews(i) for i in range(1, src.count + 1)],
            "compression": src.compression.value if src.compression else None,
            "bounds_wgs84": bounds_polygon_wgs84(src),
        }
        if crs is None:
            meta["warnings"] = ["No CRS defined – reprojection/clipping unavailable until a CRS is assigned."]
        if with_stats:
            meta["statistics"] = [_block_stats(src, b) for b in range(1, src.count + 1)]
    return meta


def register_raster(db, path: Path, name: str, kind: str, category: str | None = None,
                    parent_id: int | None = None, is_original: bool = False,
                    original_filename: str | None = None, year: int | None = None,
                    source: str | None = None, processing: dict | None = None,
                    acquired_start: datetime | None = None, acquired_end: datetime | None = None,
                    with_stats: bool = True):
    from ..models import RasterAsset
    meta = raster_metadata(path, with_stats=with_stats)
    asset = RasterAsset(
        name=name, kind=kind, category=category, path=str(path), parent_id=parent_id,
        is_original=is_original, original_filename=original_filename, crs=meta["crs"],
        width=meta["width"], height=meta["height"], band_count=meta["band_count"], dtype=meta["dtypes"][0],
        resolution_x=meta["resolution"][0], resolution_y=meta["resolution"][1],
        nodata=None if meta["nodata"] is None or (isinstance(meta["nodata"], float) and math.isnan(meta["nodata"])) else meta["nodata"],
        bounds_wgs84=meta["bounds_wgs84"], statistics={"bands": meta.get("statistics"), "band_descriptions": meta["band_descriptions"]},
        year=year, source=source, processing=processing, acquired_start=acquired_start, acquired_end=acquired_end)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _out_path(stem: str, suffix: str = ".tif") -> Path:
    return settings.processed_dir / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"


def reproject_raster(src_path: str | Path, dst_crs: str, resolution: float | None = None,
                     resampling: str = "bilinear") -> Path:
    rs = Resampling[resampling]
    out = _out_path(Path(src_path).stem + "_reproj")
    with rasterio.open(src_path) as src:
        if src.crs is None:
            raise ValueError("Source raster has no CRS")
        kw = {"resolution": resolution} if resolution else {}
        transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height,
                                                               *src.bounds, **kw)
        profile = src.profile.copy()
        profile.update(GTIFF_PROFILE, crs=dst_crs, transform=transform, width=width, height=height)
        if width < 256 or height < 256:
            profile.update(tiled=False)
            profile.pop("blockxsize", None), profile.pop("blockysize", None)
        with rasterio.open(out, "w", **profile) as dst:
            for b in range(1, src.count + 1):  # band by band, GDAL warps in chunks
                reproject(rasterio.band(src, b), rasterio.band(dst, b), src_transform=src.transform,
                          src_crs=src.crs, dst_transform=transform, dst_crs=dst_crs, resampling=rs,
                          src_nodata=src.nodata, dst_nodata=src.nodata, num_threads=2)
            dst.descriptions = src.descriptions
    return out


def clip_raster(src_path: str | Path, geometry_wgs84: dict, crop: bool = True) -> Path:
    out = _out_path(Path(src_path).stem + "_clip")
    with rasterio.open(src_path) as src:
        if src.crs is None:
            raise ValueError("Source raster has no CRS")
        geom = transform_geom("EPSG:4326", src.crs, geometry_wgs84)
        if not shape(geom).intersects(box(*src.bounds)):
            raise ValueError("Clip geometry does not intersect the raster")
        nodata = src.nodata if src.nodata is not None else (np.nan if src.dtypes[0].startswith("float") else 0)
        data, transform = rio_mask(src, [geom], crop=crop, nodata=nodata, filled=True)
        profile = src.profile.copy()
        profile.update(GTIFF_PROFILE, height=data.shape[1], width=data.shape[2], transform=transform, nodata=nodata)
        if data.shape[1] < 256 or data.shape[2] < 256:
            profile.update(tiled=False)
            profile.pop("blockxsize", None), profile.pop("blockysize", None)
        with rasterio.open(out, "w", **profile) as dst:
            dst.write(data)
            dst.descriptions = src.descriptions
    return out


def resample_raster(src_path: str | Path, resolution: float, resampling: str = "bilinear") -> Path:
    out = _out_path(Path(src_path).stem + f"_res{int(resolution)}")
    with rasterio.open(src_path) as src:
        if src.crs is None or not src.crs.is_projected:
            raise ValueError("Resampling to a metric resolution requires a projected CRS; reproject first")
        width = max(1, int(round((src.bounds.right - src.bounds.left) / resolution)))
        height = max(1, int(round((src.bounds.top - src.bounds.bottom) / resolution)))
        transform = from_origin(src.bounds.left, src.bounds.top, resolution, resolution)
        profile = src.profile.copy()
        profile.update(GTIFF_PROFILE, width=width, height=height, transform=transform)
        if width < 256 or height < 256:
            profile.update(tiled=False)
            profile.pop("blockxsize", None), profile.pop("blockysize", None)
        with rasterio.open(out, "w", **profile) as dst:
            for b in range(1, src.count + 1):
                reproject(rasterio.band(src, b), rasterio.band(dst, b), src_transform=src.transform,
                          src_crs=src.crs, dst_transform=transform, dst_crs=src.crs,
                          resampling=Resampling[resampling], src_nodata=src.nodata, dst_nodata=src.nodata)
            dst.descriptions = src.descriptions
    return out


# ----------------------------------------------------------------------------- previews

COLORMAPS = {
    "elevation": "terrain", "slope": "magma", "aspect": "twilight", "hillshade": "gray",
    "ndvi": "RdYlGn", "ndwi": "Blues", "mndwi": "Blues", "ndsi": "PuBu", "nbr": "BrBG",
    "difference": "RdBu", "depth": "Blues", "velocity": "plasma", "flow_accumulation": "Blues",
    "probability": "viridis", "default": "viridis", "hand": "YlGnBu_r", "roughness": "cividis",
}


def render_preview(path: str | Path, bands: list[int] | None = None, cmap: str | None = None,
                   vmin: float | None = None, vmax: float | None = None, max_size: int = 1400,
                   categorical: dict[int, str] | None = None, stretch: tuple[float, float] = (2, 98),
                   log_scale: bool = False, gamma: float = 1.0) -> tuple[bytes, list[list[float]]]:
    """Warp to Web Mercator and render to PNG. Returns (png_bytes, leaflet_bounds [[S,W],[N,E]])."""
    from PIL import Image
    import matplotlib
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError("Raster has no CRS; cannot place on map")
        dst_crs = "EPSG:3857"
        transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
        scale = max(width, height) / max_size
        if scale > 1:
            width, height = int(width / scale), int(height / scale)
            transform = transform * transform.scale(scale, scale)
        bands = bands or ([1, 2, 3] if src.count >= 3 and cmap is None and categorical is None else [1])
        out = np.full((len(bands), height, width), np.nan, dtype="float32")
        for i, b in enumerate(bands):
            reproject(rasterio.band(src, b), out[i], src_transform=src.transform, src_crs=src.crs,
                      dst_transform=transform, dst_crs=dst_crs,
                      resampling=Resampling.nearest if categorical else Resampling.bilinear,
                      src_nodata=src.nodata, dst_nodata=np.nan)
        if src.nodata is not None and not (isinstance(src.nodata, float) and math.isnan(src.nodata)):
            out[out == src.nodata] = np.nan
        left, top = transform.c, transform.f
        right, bottom = left + transform.a * width, top + transform.e * height
        w, s, e, n = transform_bounds(dst_crs, "EPSG:4326", left, bottom, right, top)
    valid = np.all(np.isfinite(out), axis=0)
    rgba = np.zeros((height, width, 4), dtype="uint8")
    if categorical:
        a = out[0]
        for val, hexcol in categorical.items():
            m = valid & (np.round(a) == val)
            if hexcol is None:
                continue
            c = matplotlib.colors.to_rgba(hexcol)
            rgba[m] = [int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), int(c[3] * 255)]
    elif len(bands) == 3:
        for i in range(3):
            a = out[i]
            v = a[valid]
            lo, hi = (np.percentile(v, stretch) if v.size else (0, 1)) if vmin is None else (vmin, vmax)
            x = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1 / gamma)
            rgba[..., i] = (np.nan_to_num(x) * 255).astype("uint8")
        rgba[..., 3] = np.where(valid, 255, 0)
    else:
        a = out[0]
        if log_scale:
            a = np.log10(np.where(a > 0, a, np.nan))
            valid = np.isfinite(a)
        v = a[valid]
        lo = vmin if vmin is not None else (float(np.percentile(v, stretch[0])) if v.size else 0)
        hi = vmax if vmax is not None else (float(np.percentile(v, stretch[1])) if v.size else 1)
        x = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
        cm = matplotlib.colormaps[COLORMAPS.get(cmap or "default", cmap or "viridis")]
        col = (cm(np.nan_to_num(x)) * 255).astype("uint8")
        rgba = col
        rgba[..., 3] = np.where(valid, 255, 0)
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, format="PNG", optimize=True)
    return buf.getvalue(), [[s, w], [n, e]]


def sample_profile(path: str | Path, coords_wgs84: list[tuple[float, float]], band: int = 1) -> list[float | None]:
    with rasterio.open(path) as src:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
        pts = [t.transform(lon, lat) for lon, lat in coords_wgs84]
        out = []
        for v in src.sample(pts, indexes=band, masked=True):
            out.append(None if np.ma.is_masked(v[0]) or not np.isfinite(v[0]) else float(v[0]))
        return out


def read_window_array(path: str | Path, band: int = 1, window: Window | None = None) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(band, window=window, masked=True).astype("float32")
        return a.filled(np.nan)

