"""Spectral indices on harmonised surface-reflectance arrays (NumPy).

All functions take float arrays of surface reflectance (0–1) and return float32 arrays
with NaN where inputs are invalid. Thresholds are parameters, never hard-coded truths.

References
- NDWI: McFeeters (1996), Int. J. Remote Sens. 17(7).
- MNDWI: Xu (2006), Int. J. Remote Sens. 27(14).
- NDVI: Tucker (1979), Remote Sens. Environ. 8(2).
- NBR: Key & Benson (2006), FIREMON LA.
- NDSI: Hall et al. (1995), Remote Sens. Environ. 54(2); snow/ice where NDSI > ~0.4.
"""
from __future__ import annotations

import numpy as np


def _nd(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a.astype("float32")
    b = b.astype("float32")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (a - b) / (a + b)
    out[~np.isfinite(out)] = np.nan
    return np.clip(out, -1, 1).astype("float32")


def ndwi(green, nir):
    return _nd(green, nir)


def mndwi(green, swir1):
    return _nd(green, swir1)


def ndvi(nir, red):
    return _nd(nir, red)


def nbr(nir, swir2):
    return _nd(nir, swir2)


def ndsi(green, swir1):
    return _nd(green, swir1)


def snow_indices(bands: dict[str, np.ndarray], ndsi_threshold: float = 0.4, nir_min: float = 0.11,
                 green_min: float = 0.10) -> dict[str, np.ndarray]:
    """NDSI and a snow/ice mask (Dozier 1989 / Hall et al. 1995 style).

    The NIR > 0.11 rule suppresses water (which also has high NDSI); green > 0.10 suppresses
    dark shadowed pixels.
    """
    s = ndsi(bands["green"], bands["swir1"])
    mask = (s > ndsi_threshold) & (bands["nir"] > nir_min) & (bands["green"] > green_min)
    mask = mask.astype("float32")
    mask[np.isnan(s)] = np.nan
    return {"ndsi": s, "snow_ice_mask": mask}


INDEX_FUNCS = {
    "ndwi": (ndwi, ("green", "nir")),
    "mndwi": (mndwi, ("green", "swir1")),
    "ndvi": (ndvi, ("nir", "red")),
    "nbr": (nbr, ("nir", "swir2")),
    "ndsi": (ndsi, ("green", "swir1")),
}


def compute_index(name: str, bands: dict[str, np.ndarray]) -> np.ndarray:
    fn, req = INDEX_FUNCS[name]
    missing = [b for b in req if b not in bands]
    if missing:
        raise ValueError(f"Index {name} requires bands {req}; missing {missing}")
    return fn(*(bands[b] for b in req))


def otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Otsu's threshold on finite values (used for scene-adaptive water thresholds)."""
    v = values[np.isfinite(values)]
    if v.size < 100:
        raise ValueError("Too few valid pixels for Otsu thresholding")
    hist, edges = np.histogram(v, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2
    w = hist.astype("float64")
    w0 = np.cumsum(w)
    w1 = w0[-1] - w0
    m0 = np.cumsum(w * centers) / np.maximum(w0, 1)
    mt = (w * centers).sum()
    m1 = (mt - np.cumsum(w * centers)) / np.maximum(w1, 1)
    between = w0 * w1 * (m0 - m1) ** 2
    return float(centers[int(np.argmax(between))])

