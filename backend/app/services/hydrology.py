"""DEM terrain derivatives and hydrological analysis.

Implemented directly in NumPy so it runs anywhere (no compiled GIS dependency):
- Slope/aspect: Horn (1981) 3×3 finite differences on the projected (UTM) grid.
- Hillshade: standard illumination model (azimuth 315°, altitude 45° by default).
- Terrain Ruggedness Index: Riley et al. (1999).
- Hydrological conditioning: Priority-Flood with ε-gradient (Barnes, Lehman & Mulla 2014),
  which fills depressions while imposing drainage across flats.
- Flow direction: D8 (O'Callaghan & Mark 1984), ESRI encoding 1..128.
- Flow accumulation: topological accumulation in elevation order.
- Streams: accumulation threshold (contributing area), Strahler order.
- Watersheds: upstream-cell tracing from snapped pour points.
- HAND (Height Above Nearest Drainage; Rennó et al. 2008) – a relative terrain index
  only. It is NOT a flood depth and is never presented as one.

If WhiteboxTools is installed it can be used as an independent cross-check
(see docs/METHODOLOGY.md); results here are self-contained and reproducible.
"""
from __future__ import annotations

import heapq
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio import features
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import linemerge, transform as shp_transform, unary_union

# D8 offsets and ESRI codes: E, SE, S, SW, W, NW, N, NE
D8_DR = np.array([0, 1, 1, 1, 0, -1, -1, -1])
D8_DC = np.array([1, 1, 0, -1, -1, -1, 0, 1])
D8_CODE = np.array([1, 2, 4, 8, 16, 32, 64, 128])


def _pad(z: np.ndarray) -> np.ndarray:
    return np.pad(z, 1, mode="edge")


def slope_aspect(z: np.ndarray, res: float) -> tuple[np.ndarray, np.ndarray]:
    """Horn's method. Returns slope (degrees) and aspect (degrees clockwise from north)."""
    p = _pad(z.astype("float64"))
    a, b, c = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    d, f = p[1:-1, :-2], p[1:-1, 2:]
    g, h, i = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * res)
    dzdy = ((g + 2 * h + i) - (a + 2 * b + c)) / (8 * res)  # positive southward
    slope = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
    # downslope direction in (east, north) components is (-dzdx, +dzdy) since dzdy is southward-positive
    aspect = (np.degrees(np.arctan2(-dzdx, dzdy)) + 360.0) % 360.0  # 0=N, 90=E (direction slope faces)
    aspect[np.hypot(dzdx, dzdy) < 1e-9] = np.nan
    return slope.astype("float32"), aspect.astype("float32")


def hillshade(z: np.ndarray, res: float, azimuth: float = 315.0, altitude: float = 45.0) -> np.ndarray:
    p = _pad(z.astype("float64"))
    dzdx = ((p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])) / (8 * res)
    dzdy = ((p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])) / (8 * res)
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(dzdy, -dzdx)
    zen = np.radians(90 - altitude)
    az = np.radians((360 - azimuth + 90) % 360)
    hs = np.cos(zen) * np.cos(slope) + np.sin(zen) * np.sin(slope) * np.cos(az - aspect)
    return (np.clip(hs, 0, 1) * 255).astype("float32")


def terrain_ruggedness(z: np.ndarray) -> np.ndarray:
    p = _pad(z.astype("float64"))
    c = p[1:-1, 1:-1]
    acc = np.zeros_like(c)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            acc += (p[1 + dr:p.shape[0] - 1 + dr, 1 + dc:p.shape[1] - 1 + dc] - c) ** 2
    return np.sqrt(acc).astype("float32")


def priority_flood_fill(z: np.ndarray, epsilon: float = 1e-3) -> np.ndarray:
    """Priority-Flood + ε (Barnes et al. 2014). NaN cells are treated as outlets (edges)."""
    rows, cols = z.shape
    filled = z.astype("float64").copy()
    nan = ~np.isfinite(filled)
    closed = np.zeros(z.shape, bool)
    closed[nan] = True
    heap: list[tuple[float, int]] = []
    # seed with edge cells and cells adjacent to NaN
    edge = np.zeros(z.shape, bool)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    if nan.any():
        nb = np.zeros(z.shape, bool)
        for k in range(8):
            nb |= np.roll(np.roll(nan, D8_DR[k], 0), D8_DC[k], 1)
        edge |= nb
    edge &= ~nan
    for idx in np.flatnonzero(edge):
        heapq.heappush(heap, (filled.flat[idx], int(idx)))
        closed.flat[idx] = True
    fflat = filled.ravel()
    cflat = closed.ravel()
    push, pop = heapq.heappush, heapq.heappop
    while heap:
        zc, idx = pop(heap)
        r, c = divmod(idx, cols)
        for k in range(8):
            rr, cc = r + D8_DR[k], c + D8_DC[k]
            if rr < 0 or rr >= rows or cc < 0 or cc >= cols:
                continue
            n = rr * cols + cc
            if cflat[n]:
                continue
            cflat[n] = True
            if fflat[n] <= zc:
                fflat[n] = zc + epsilon
            push(heap, (fflat[n], n))
    return filled


def d8_flow_direction(filled: np.ndarray, res: float) -> np.ndarray:
    """Index of the steepest-descent neighbour (0..7) or -1 for outlets/NaN."""
    rows, cols = filled.shape
    p = np.pad(filled, 1, mode="constant", constant_values=np.nan)
    best = np.full(filled.shape, -1, dtype="int8")
    best_slope = np.zeros(filled.shape)
    center = p[1:-1, 1:-1]
    for k in range(8):
        dist = res * (np.sqrt(2) if D8_DR[k] != 0 and D8_DC[k] != 0 else 1.0)
        nb = p[1 + D8_DR[k]:rows + 1 + D8_DR[k], 1 + D8_DC[k]:cols + 1 + D8_DC[k]]
        s = (center - nb) / dist
        s = np.where(np.isfinite(s), s, -np.inf)
        better = s > best_slope
        best[better] = k
        best_slope[better] = s[better]
    # edge cells with no lower neighbour drain off-grid
    best[~np.isfinite(filled)] = -1
    return best


def downstream_index(fdir: np.ndarray) -> np.ndarray:
    rows, cols = fdir.shape
    r, c = np.indices(fdir.shape)
    k = np.where(fdir >= 0, fdir, 0)
    rr = r + D8_DR[k]
    cc = c + D8_DC[k]
    ds = rr * cols + cc
    ds[(fdir < 0) | (rr < 0) | (rr >= rows) | (cc < 0) | (cc >= cols)] = -1
    return ds.ravel()


def flow_accumulation(filled: np.ndarray, fdir: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Number of upstream cells (including itself). Returns (acc, processing order)."""
    ds = downstream_index(fdir)
    zf = np.where(np.isfinite(filled), filled, -np.inf).ravel()
    order = np.argsort(-zf, kind="stable")  # high to low: every cell before its downstream
    acc = np.ones(zf.size, dtype="float64")
    acc[~np.isfinite(filled).ravel()] = 0
    for i in order:
        d = ds[i]
        if d >= 0:
            acc[d] += acc[i]
    return acc.reshape(filled.shape), order


def strahler_order(stream: np.ndarray, fdir: np.ndarray, order: np.ndarray) -> np.ndarray:
    ds = downstream_index(fdir)
    s = stream.ravel()
    so = np.zeros(s.size, dtype="int16")
    max_in = np.zeros(s.size, dtype="int16")
    cnt_max = np.zeros(s.size, dtype="int16")
    for i in order:
        if not s[i]:
            continue
        if max_in[i] == 0:
            so[i] = 1
        else:
            so[i] = max_in[i] + (1 if cnt_max[i] >= 2 else 0)
        d = ds[i]
        if d >= 0 and s[d]:
            if so[i] > max_in[d]:
                max_in[d] = so[i]
                cnt_max[d] = 1
            elif so[i] == max_in[d]:
                cnt_max[d] += 1
    return so.reshape(stream.shape)


def hand(filled: np.ndarray, z: np.ndarray, stream: np.ndarray, fdir: np.ndarray, order: np.ndarray) -> np.ndarray:
    """Height Above Nearest Drainage along D8 paths (relative terrain index, metres)."""
    ds = downstream_index(fdir)
    zf = z.ravel().astype("float64")
    drain = np.full(zf.size, np.nan)
    s = stream.ravel()
    for i in order[::-1]:  # low to high: downstream cells resolved first
        if s[i]:
            drain[i] = zf[i]
        else:
            d = ds[i]
            if d >= 0:
                drain[i] = drain[d]
    out = (zf - drain).reshape(z.shape)
    out[out < 0] = 0
    return out.astype("float32")


def upstream_mask(fdir: np.ndarray, outlet_idx: int, order: np.ndarray) -> np.ndarray:
    ds = downstream_index(fdir)
    m = np.zeros(ds.size, bool)
    m[outlet_idx] = True
    for i in order[::-1]:  # low to high: a cell is in the basin if its downstream is
        d = ds[i]
        if d >= 0 and m[d]:
            m[i] = True
    return m.reshape(fdir.shape)


def snap_pour_point(acc: np.ndarray, row: int, col: int, radius: int = 5) -> tuple[int, int]:
    r0, r1 = max(0, row - radius), min(acc.shape[0], row + radius + 1)
    c0, c1 = max(0, col - radius), min(acc.shape[1], col + radius + 1)
    sub = acc[r0:r1, c0:c1]
    k = int(np.nanargmax(sub))
    return r0 + k // sub.shape[1], c0 + k % sub.shape[1]


def trace_flow_path(fdir: np.ndarray, start_rc: tuple[int, int], max_steps: int = 100000) -> list[tuple[int, int]]:
    rows, cols = fdir.shape
    r, c = start_rc
    path = [(r, c)]
    seen = {(r, c)}
    for _ in range(max_steps):
        k = fdir[r, c]
        if k < 0:
            break
        r, c = r + D8_DR[k], c + D8_DC[k]
        if r < 0 or r >= rows or c < 0 or c >= cols or (r, c) in seen:
            break
        path.append((r, c))
        seen.add((r, c))
    return path


def esri_codes(fdir: np.ndarray) -> np.ndarray:
    out = np.zeros(fdir.shape, dtype="float32")
    valid = fdir >= 0
    out[valid] = D8_CODE[fdir[valid]]
    out[~valid] = np.nan
    return out


def streams_to_lines(stream: np.ndarray, fdir: np.ndarray, sorder: np.ndarray, transform) -> list[dict]:
    """Vectorise stream cells to merged polylines per Strahler order (projected coords)."""
    rows, cols = stream.shape
    segs: dict[int, list] = {}
    rr, cc = np.nonzero(stream)
    for r, c in zip(rr, cc):
        k = fdir[r, c]
        if k < 0:
            continue
        r2, c2 = r + D8_DR[k], c + D8_DC[k]
        if not (0 <= r2 < rows and 0 <= c2 < cols):
            continue
        x1, y1 = transform * (c + 0.5, r + 0.5)
        x2, y2 = transform * (c2 + 0.5, r2 + 0.5)
        segs.setdefault(int(sorder[r, c]), []).append(LineString([(x1, y1), (x2, y2)]))
    out = []
    for o, lines in sorted(segs.items()):
        merged = linemerge(lines)
        geoms = list(merged.geoms) if hasattr(merged, "geoms") else [merged]
        for g in geoms:
            out.append({"geometry": g, "strahler": o, "length_m": g.length})
    return out


def to_wgs84(geom, src_crs):
    from pyproj import Transformer
    t = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    return shp_transform(lambda x, y, z=None: t.transform(x, y), geom)


def from_wgs84(geom, dst_crs):
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", dst_crs, always_xy=True)
    return shp_transform(lambda x, y, z=None: t.transform(x, y), geom)


def write_geojson(path: Path, feats: list[dict], crs_note: str = "EPSG:4326") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "crs_note": crs_note, "features": [
        {"type": "Feature", "geometry": mapping(f["geometry"]) if not isinstance(f["geometry"], dict) else f["geometry"],
         "properties": {k: v for k, v in f.items() if k != "geometry"}} for f in feats]}
    path.write_text(json.dumps(fc))
    return path


def polygonize_mask(mask: np.ndarray, transform, min_area_m2: float = 0.0) -> list:
    geoms = [shape(g) for g, v in features.shapes(mask.astype("uint8"), mask=mask.astype(bool), transform=transform) if v == 1]
    geoms = [g for g in geoms if g.area >= min_area_m2]
    return geoms
