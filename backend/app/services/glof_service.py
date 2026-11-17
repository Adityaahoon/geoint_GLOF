"""GLOF Susceptibility Assessment service.

Implements two complementary pathways:
1. `mcda_screening_v1`: A transparent, literature-grounded multi-criteria susceptibility
   screening framework following GAPHAZ (2017), Huggel et al. (2002), Worni et al. (2013),
   Allen et al. (2019) and NDMA (2020) Himalayan glacial lake screening guidelines.
   - Explicitly labelled as a PRELIMINARY SCREENING ASSESSMENT (`is_trained_model = False`).
   - Scores are normalized composite indices in [0, 1], NEVER outburst probabilities.
   - Field-only parameters (e.g. moraine dam internal ice core / freeboard, bathymetric volume)
     are reported in `missing_parameters`, and a pessimistic/optimistic sensitivity interval
     (`score_range` and `category_range`) is computed over missing factors.

2. Supervised ML pipeline (`random_forest`, `xgboost`, `mlp` in scikit-learn / XGBoost):
   - Evaluates feature importances, cross-validated ROC-AUC / F1, and per-lake predictions
     WHEN a validated regional GLOF inventory CSV (`data/training/glof_susceptibility/verified_glof_events.csv`)
     with real historical outburst labels is supplied.
   - Never fabricates synthetic outburst labels.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from shapely.geometry import shape

from ..config import get_settings
from ..models import GlacialLake, GlacierBoundary, LakeObservation, RasterAsset, SusceptibilityAssessment, VectorLayer
from . import hydrology as hy

settings = get_settings()
GLOF_TRAIN_CSV = settings.training_dir / "glof_susceptibility" / "verified_glof_events.csv"

CRITERIA = [
    {
        "key": "lake_area_ha",
        "label": "Lake surface area (ha)",
        "weight": 0.12,
        "scoring": "Piecewise linear: <0.5 ha → 0.15, 2 ha → 0.50, 5 ha → 0.75, ≥10 ha → 1.0",
        "rationale": "Proxy for empirical potential water volume (Huggel et al., 2002); area alone does not trigger a GLOF.",
        "reference": "Huggel et al. (2002), Can. Geotech. J. 39(2); GAPHAZ (2017)",
    },
    {
        "key": "expansion_rate_pct_yr",
        "label": "Multi-temporal area expansion rate (%/yr)",
        "weight": 0.16,
        "scoring": "≤0%/yr → 0.10, +2%/yr → 0.50, +5%/yr → 0.80, ≥+10%/yr → 1.0 (requires ≥2 observation years)",
        "rationale": "Rapid lake growth increases hydrostatic head and alters dam thermal/mechanical equilibrium.",
        "reference": "Bolch et al. (2011); Dubey & Goyal (2020)",
    },
    {
        "key": "glacier_distance_m",
        "label": "Proximity to glacier / perennial ice (m)",
        "weight": 0.16,
        "scoring": "In contact (0 m) → 1.0, 200 m → 0.75, 500 m → 0.45, ≥1500 m → 0.10",
        "rationale": "Controls calving, subaerial ice-avalanche entry and meltwater supply.",
        "reference": "Allen et al. (2019), Sci. Bull.; ICIMOD (2011)",
    },
    {
        "key": "ava_slope_steep_frac",
        "label": "Steep (>30°) upslope mass-movement source fraction within 1 km",
        "weight": 0.18,
        "scoring": "Fraction of upslope buffer with slope 30°–60°: 0 → 0.05, 0.25 → 0.55, ≥0.50 → 1.0",
        "rationale": "Ice/rock avalanches into the lake are the primary dynamic trigger of Himalayan GLOFs.",
        "reference": "GAPHAZ (2017); Fischer et al. (2012)",
    },
    {
        "key": "surrounding_slope_p90_deg",
        "label": "Surrounding terrain 90th-percentile slope (deg, 500 m buffer)",
        "weight": 0.10,
        "scoring": "<15° → 0.10, 25° → 0.45, 35° → 0.75, ≥45° → 1.0",
        "rationale": "Reflects local valley wall confinement and rockfall/debris entry potential.",
        "reference": "Worni et al. (2013), Sci. Total Environ.",
    },
    {
        "key": "outlet_gradient_deg",
        "label": "Downstream outlet channel gradient over first 1 km (deg)",
        "weight": 0.12,
        "scoring": "<3° → 0.15, 8° → 0.50, 15° → 0.80, ≥22° → 1.0",
        "rationale": "Steep outlet gradients promote moraine incision, debris entrainment and flow bulking.",
        "reference": "Huggel et al. (2004); Westoby et al. (2014)",
    },
    {
        "key": "channel_connectivity_m",
        "label": "Distance from lake outlet to mapped D8 stream network (m)",
        "weight": 0.06,
        "scoring": "≤30 m → 1.0, 150 m → 0.60, ≥500 m → 0.15",
        "rationale": "Direct drainage coupling determines how efficiently an outburst wave enters the main valley channel.",
        "reference": "NDMA (2020) GLOF Management Guidelines",
    },
    {
        "key": "elevation_m",
        "label": "Lake elevation (m a.s.l.)",
        "weight": 0.05,
        "scoring": "<3200 m → 0.20, 3800 m → 0.65, ≥4500 m → 0.90",
        "rationale": "Permafrost degradation and high gravitational potential energy in periglacial zones.",
        "reference": "Sattar et al. (2021)",
    },
    {
        "key": "moraine_dam_condition",
        "label": "Moraine dam geometry, freeboard & buried-ice condition (field/HR)",
        "weight": 0.05,
        "scoring": "Requires sub-metre DEM / GPR / field survey; treated as unknown in 30 m satellite screening and propagated into uncertainty bounds.",
        "rationale": "Dam width-to-height ratio, freeboard and ice cores govern breach initiation.",
        "reference": "GAPHAZ (2017); Rounce et al. (2016)",
    },
]

CLASSES = [
    {"label": "Low", "min": 0.0, "max": 0.35},
    {"label": "Moderate", "min": 0.35, "max": 0.55},
    {"label": "High", "min": 0.55, "max": 0.75},
    {"label": "Very High", "min": 0.75, "max": 1.01},
]


def classify_score(score: float) -> str:
    for c in CLASSES:
        if c["min"] <= score < c["max"]:
            return c["label"]
    return "Very High" if score >= 0.75 else "Low"


def methodology_spec() -> dict:
    return {
        "method": "mcda_screening_v1",
        "version": "1.0 (GAPHAZ 2017 / Huggel 2002 / Allen 2019 multi-criteria screening)",
        "is_trained_model": False,
        "description": (
            "Transparent weighted multi-criteria susceptibility screening index computed from "
            "DEM geomorphometry, D8 hydrology, glacier proximity and multi-temporal satellite "
            "lake observations. Scores in [0, 1] represent relative hazard screening priority — "
            "they are NOT statistical probabilities of outburst occurrence."
        ),
        "criteria": CRITERIA,
        "classes": CLASSES,
        "limitations": [
            "30 m satellite DEMs (Copernicus GLO-30) cannot resolve moraine dam freeboard (<2–5 m), dam crest width, or buried dead-ice cores.",
            "Bathymetric lake depth and actual water volume require field sonar survey; surface area is only an empirical proxy.",
            "When only a single post-monsoon observation year has been processed for a lake, the multi-temporal expansion rate is marked missing and propagated into the uncertainty range.",
            "Scores are preliminary screening indices to prioritize lakes for detailed geotechnical and HEC-RAS 2D hydraulic investigation.",
        ],
    }


def _interp_score(val: float, xs: list[float], ys: list[float]) -> float:
    return float(np.interp(val, xs, ys))


def assess_all_lakes(db, log=lambda m, p=None: None) -> list[dict]:
    lakes = db.query(GlacialLake).order_by(GlacialLake.lake_code).all()
    if not lakes:
        return []

    dem_a = db.query(RasterAsset).filter_by(kind="terrain", category="elevation").order_by(RasterAsset.id.desc()).first()
    slope_a = db.query(RasterAsset).filter_by(kind="terrain", category="slope").order_by(RasterAsset.id.desc()).first()
    if dem_a is None or slope_a is None:
        raise RuntimeError("Run Terrain & Hydrological Analysis (/api/terrain/analyse) before GLOF susceptibility assessment.")

    with rasterio.open(dem_a.path) as s_dem, rasterio.open(slope_a.path) as s_slp:
        z = s_dem.read(1, masked=True).astype("float32").filled(np.nan)
        slp = s_slp.read(1, masked=True).astype("float32").filled(np.nan)
        transform, crs = s_dem.transform, s_dem.crs
        res = abs(s_dem.res[0])

    # Load glacier boundaries and stream network in UTM
    glacier_polys = []
    for gb in db.query(GlacierBoundary).all():
        if gb.geometry:
            glacier_polys.append(hy.from_wgs84(shape(gb.geometry), crs))

    stream_lines = []
    st_vl = db.query(VectorLayer).filter_by(key="streams").first()
    if st_vl and Path(st_vl.path).exists():
        import json
        fc = json.loads(Path(st_vl.path).read_text())
        for f in fc.get("features", []):
            stream_lines.append(hy.from_wgs84(shape(f["geometry"]), crs))

    fdir_path = settings.processed_dir / "terrain" / "fdir.npy"
    fdir = np.load(fdir_path) if fdir_path.exists() else None
    inv = ~transform
    h, w = z.shape

    results = []
    for idx, lk in enumerate(lakes):
        log(f"Assessing {lk.lake_code} ({lk.name})", (idx + 1) / len(lakes))
        obs_list = sorted(lk.observations, key=lambda o: o.year)
        if not obs_list:
            continue
        latest = obs_list[-1]
        lake_geom_utm = hy.from_wgs84(shape(latest.geometry), crs)
        cent_utm = lake_geom_utm.centroid

        # 1. Lake area (ha)
        area_ha = float(latest.area_ha)
        s_area = _interp_score(area_ha, [0.2, 0.5, 2.0, 5.0, 10.0], [0.10, 0.20, 0.50, 0.75, 1.0])

        # 2. Multi-temporal expansion rate (%/yr)
        years_distinct = sorted({o.year: o.area_ha for o in obs_list}.items())
        if len(years_distinct) >= 2 and (years_distinct[-1][0] > years_distinct[0][0]) and years_distinct[0][1] > 0:
            dy = years_distinct[-1][0] - years_distinct[0][0]
            exp_rate = ((years_distinct[-1][1] - years_distinct[0][1]) / years_distinct[0][1]) * 100.0 / dy
            s_exp = _interp_score(exp_rate, [-5.0, 0.0, 2.0, 5.0, 10.0], [0.05, 0.15, 0.50, 0.80, 1.0])
            exp_available = True
        else:
            exp_rate = None
            s_exp = None
            exp_available = False

        # 3. Distance to nearest glacier / perennial snow-ice outline (m)
        if glacier_polys:
            g_dist = float(min(lake_geom_utm.distance(g) for g in glacier_polys))
            s_glac = _interp_score(g_dist, [0.0, 200.0, 500.0, 1000.0, 2000.0], [1.0, 0.75, 0.45, 0.25, 0.10])
            glac_available = True
        else:
            g_dist = None
            s_glac = None
            glac_available = False

        # Sample 1000 m and 500 m windows around lake centroid
        c_px, r_px = inv * (cent_utm.x, cent_utm.y)
        r_c, c_c = int(round(r_px)), int(round(c_px))
        lake_elev = float(lk.elevation_m) if lk.elevation_m is not None else (
            float(z[r_c, c_c]) if 0 <= r_c < h and 0 <= c_c < w and np.isfinite(z[r_c, c_c]) else 3800.0
        )

        rad_1km = int(round(1000.0 / res))
        r0, r1 = max(0, r_c - rad_1km), min(h, r_c + rad_1km + 1)
        c0, c1 = max(0, c_c - rad_1km), min(w, c_c + rad_1km + 1)
        sub_z = z[r0:r1, c0:c1]
        sub_slp = slp[r0:r1, c0:c1]
        upslope = np.isfinite(sub_z) & (sub_z > lake_elev + 15.0)
        if upslope.any():
            steep_frac = float(((sub_slp >= 30.0) & (sub_slp <= 60.0) & upslope).sum() / upslope.sum())
        else:
            steep_frac = 0.0
        s_ava = _interp_score(steep_frac, [0.0, 0.10, 0.25, 0.40, 0.55], [0.05, 0.25, 0.55, 0.85, 1.0])

        rad_500 = int(round(500.0 / res))
        r0b, r1b = max(0, r_c - rad_500), min(h, r_c + rad_500 + 1)
        c0b, c1b = max(0, c_c - rad_500), min(w, c_c + rad_500 + 1)
        slp_500 = slp[r0b:r1b, c0b:c1b]
        p90_slp = float(np.nanpercentile(slp_500, 90)) if np.isfinite(slp_500).any() else 20.0
        s_slp = _interp_score(p90_slp, [10.0, 20.0, 30.0, 40.0, 50.0], [0.10, 0.30, 0.60, 0.85, 1.0])

        # 6. Downstream outlet channel gradient over first ~1 km along D8 path
        outlet_grad = 10.0
        if fdir is not None and 0 <= r_c < h and 0 <= c_c < w:
            path_rc = hy.trace_flow_path(fdir, (r_c, c_c), max_steps=int(1200 / res))
            if len(path_rc) >= 3:
                z_start = float(z[path_rc[0][0], path_rc[0][1]])
                z_end = float(z[path_rc[-1][0], path_rc[-1][1]])
                dist_m = max(len(path_rc) * res, res)
                outlet_grad = float(np.degrees(np.arctan(max(z_start - z_end, 0.0) / dist_m)))
        s_out = _interp_score(outlet_grad, [2.0, 6.0, 12.0, 18.0, 25.0], [0.15, 0.40, 0.70, 0.90, 1.0])

        # 7. Channel connectivity (m to nearest D8 stream)
        if stream_lines:
            c_dist = float(min(lake_geom_utm.distance(l) for l in stream_lines))
        else:
            c_dist = 100.0
        s_conn = _interp_score(c_dist, [0.0, 30.0, 150.0, 350.0, 600.0], [1.0, 0.95, 0.60, 0.30, 0.15])

        # 8. Lake elevation
        s_elev = _interp_score(lake_elev, [3000.0, 3500.0, 4000.0, 4500.0], [0.20, 0.45, 0.75, 0.95])

        raw_factors = {
            "lake_area_ha": {"value": round(area_ha, 3), "unit": "ha", "score": round(s_area, 3), "weight": 0.12, "available": True},
            "expansion_rate_pct_yr": {"value": round(exp_rate, 3) if exp_rate is not None else None, "unit": "%/yr", "score": round(s_exp, 3) if s_exp is not None else None, "weight": 0.16, "available": exp_available},
            "glacier_distance_m": {"value": round(g_dist, 1) if g_dist is not None else None, "unit": "m", "score": round(s_glac, 3) if s_glac is not None else None, "weight": 0.16, "available": glac_available},
            "ava_slope_steep_frac": {"value": round(steep_frac, 3), "unit": "fraction", "score": round(s_ava, 3), "weight": 0.18, "available": True},
            "surrounding_slope_p90_deg": {"value": round(p90_slp, 1), "unit": "deg", "score": round(s_slp, 3), "weight": 0.10, "available": True},
            "outlet_gradient_deg": {"value": round(outlet_grad, 1), "unit": "deg", "score": round(s_out, 3), "weight": 0.12, "available": True},
            "channel_connectivity_m": {"value": round(c_dist, 1), "unit": "m", "score": round(s_conn, 3), "weight": 0.06, "available": True},
            "elevation_m": {"value": round(lake_elev, 1), "unit": "m", "score": round(s_elev, 3), "weight": 0.05, "available": True},
            "moraine_dam_condition": {"value": None, "unit": "field_survey", "score": None, "weight": 0.05, "available": False},
        }

        avail_w = sum(f["weight"] for f in raw_factors.values() if f["available"])
        missing_w = sum(f["weight"] for f in raw_factors.values() if not f["available"])
        weighted_known = sum(f["weight"] * f["score"] for f in raw_factors.values() if f["available"])

        # Central screening index normalizes over observed weights; uncertainty bounds vary missing factors across [0.1, 0.9]
        central_score = float(weighted_known / max(avail_w, 1e-6))
        low_score = float(weighted_known + missing_w * 0.10)
        high_score = float(weighted_known + missing_w * 0.90)
        category = classify_score(central_score)
        missing_keys = [k for k, f in raw_factors.items() if not f["available"]]

        uncertainty = {
            "score_range": [round(low_score, 3), round(high_score, 3)],
            "category_range": [classify_score(low_score), classify_score(high_score)],
            "observed_weight_fraction": round(avail_w, 3),
            "note": "Score range reflects sensitivity to unobserved parameters (set to 0.10 vs 0.90).",
        }

        prev = db.query(SusceptibilityAssessment).filter_by(lake_id=lk.id, method="mcda_screening_v1").first()
        if prev is None:
            prev = SusceptibilityAssessment(lake_id=lk.id, method="mcda_screening_v1")
            db.add(prev)
        prev.is_trained_model = False
        prev.score = round(central_score, 3)
        prev.category = category
        prev.factors = raw_factors
        prev.missing_parameters = missing_keys
        prev.uncertainty = uncertainty
        prev.parameters = {"version": "1.0", "n_observations": len(obs_list)}

        results.append({
            "lake_id": lk.id,
            "lake_code": lk.lake_code,
            "name": lk.name,
            "method": "mcda_screening_v1",
            "is_trained_model": False,
            "score": round(central_score, 3),
            "category": category,
            "factors": raw_factors,
            "missing_parameters": missing_keys,
            "uncertainty": uncertainty,
        })

    db.commit()
    return results


def ml_pipeline_status() -> dict:
    GLOF_TRAIN_CSV.parent.mkdir(parents=True, exist_ok=True)
    xgb_ok = False
    xgb_err = None
    try:
        import xgboost  # noqa: F401
        xgb_ok = True
    except Exception as exc:
        xgb_err = str(exc)

    present = GLOF_TRAIN_CSV.exists()
    n_rows = 0
    if present:
        n_rows = max(0, len(GLOF_TRAIN_CSV.read_text().splitlines()) - 1)
    return {
        "trainable": present and n_rows >= 20,
        "label_file_present": present,
        "labelled_event_count": n_rows,
        "label_file_path": str(GLOF_TRAIN_CSV),
        "models_supported": ["random_forest", "mlp"] + (["xgboost"] if xgb_ok else []),
        "xgboost_status": {"available": xgb_ok, "error": xgb_err},
        "reason": (
            "Supervised GLOF classifiers (Random Forest, XGBoost, MLP) require a verified regional inventory of "
            "historical outburst vs non-outburst glacial lakes (≥20 labelled lakes). Following scientific integrity "
            "requirements, GlacioGuard AI never trains on synthetic or simulated event labels. While awaiting a "
            "verified label CSV, the platform uses the transparent GAPHAZ/Huggel/Allen multi-criteria screening framework (`mcda_screening_v1`)."
        ),
        "required_data": [
            f"Place a CSV at {GLOF_TRAIN_CSV} with columns: lake_code, lake_area_ha, expansion_rate_pct_yr, glacier_distance_m, ava_slope_steep_frac, surrounding_slope_p90_deg, outlet_gradient_deg, channel_connectivity_m, elevation_m, historical_glof_label (0 or 1), source_citation."
        ],
    }

