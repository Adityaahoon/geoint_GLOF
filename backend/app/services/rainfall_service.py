"""Precipitation retrieval and anomaly analysis for the Kedarnath basin (2000–2026).

Sources supported:
- `CHIRPS` (UCSB-CHG/CHIRPS/DAILY, 0.05°) via Google Earth Engine when GEE is authenticated.
- `GPM_IMERG` (NASA/GPM_L3/IMERG_V07, 0.1°) via Google Earth Engine when GEE is authenticated.
- `NASA_POWER_MERRA2` (NASA Langley POWER API, `PRECTOTCORR` MERRA-2 /GPCP bias-corrected
  precipitation, 0.5°×0.625°) — publicly accessible without authentication and clearly
  labelled as a coarse-grid reanalysis/satellite product.
"""
from __future__ import annotations

import calendar
from datetime import datetime

import httpx
import numpy as np

from ..models import RainfallRecord
from . import gee_service

KEDARNATH_PT = {"lon": 79.0669, "lat": 30.7346}


def fetch_rainfall(db, source: str = "nasa_power", start_year: int = 2000, end_year: int = 2025, log=lambda m, p=None: None) -> dict:
    source_norm = source.lower()
    records_added = 0

    if source_norm in ("chirps", "gpm") and gee_service.status()["available"]:
        if source_norm == "chirps":
            log(f"Fetching CHIRPS monthly precipitation ({start_year}–{end_year}) via Google Earth Engine", 0.2)
            rows = gee_service.chirps_monthly(f"{start_year}-01-01", f"{end_year}-12-31")
            src_label = "CHIRPS"
            period = "monthly"
        else:
            log("Fetching GPM IMERG daily precipitation (June–Sept 2013 window) via Google Earth Engine", 0.2)
            rows = gee_service.gpm_daily("2013-06-01", "2013-06-30")
            src_label = "GPM_IMERG"
            period = "daily"
        for r in rows:
            if r.get("precipitation_mm") is None:
                continue
            dt = datetime.fromisoformat(r["date"])
            _upsert_rain(db, src_label, period, dt, float(r["precipitation_mm"]), {"provider": "gee"})
            records_added += 1
        db.commit()
        return {"source": src_label, "records_stored": records_added}

    # Open-data fallback: NASA POWER (monthly 2000..end_year + daily June 2013 extreme event window)
    src_label = "NASA_POWER_MERRA2"
    end_y = min(end_year, datetime.utcnow().year - 1)
    log(f"Fetching NASA POWER (PRECTOTCORR) monthly precipitation {start_year}–{end_y} and June 2013 daily series", 0.2)
    url_m = (
        f"https://power.larc.nasa.gov/api/temporal/monthly/point"
        f"?parameters=PRECTOTCORR&community=AG&longitude={KEDARNATH_PT['lon']}&latitude={KEDARNATH_PT['lat']}"
        f"&start={start_year}&end={end_y}&format=JSON"
    )
    with httpx.Client(timeout=45.0) as client:
        r_m = client.get(url_m)
        r_m.raise_for_status()
        pm = r_m.json()["properties"]["parameter"]["PRECTOTCORR"]
        for ym_str, val_mm_day in pm.items():
            if len(ym_str) != 6 or val_mm_day is None or float(val_mm_day) < 0:
                continue
            y = int(ym_str[:4])
            m = int(ym_str[4:6])
            if m < 1 or m > 12:
                continue
            days = calendar.monthrange(y, m)[1]
            total_mm = round(float(val_mm_day) * days, 2)
            _upsert_rain(
                db, src_label, "monthly", datetime(y, m, 1), total_mm,
                {"unit_raw": "mm/day multiplied by month days", "grid": "0.5x0.625 deg"}
            )
            records_added += 1

        # Daily series for 2013 (to resolve the 15–17 June 2013 extreme synoptic event)
        log("Fetching 2013 daily precipitation series over Kedarnath", 0.65)
        url_d = (
            f"https://power.larc.nasa.gov/api/temporal/daily/point"
            f"?parameters=PRECTOTCORR&community=AG&longitude={KEDARNATH_PT['lon']}&latitude={KEDARNATH_PT['lat']}"
            f"&start=20130501&end=20130930&format=JSON"
        )
        r_d = client.get(url_d)
        r_d.raise_for_status()
        pd = r_d.json()["properties"]["parameter"]["PRECTOTCORR"]
        for ymd_str, val_mm in pd.items():
            if len(ymd_str) != 8 or val_mm is None or float(val_mm) < 0:
                continue
            dt = datetime.strptime(ymd_str, "%Y%m%d")
            _upsert_rain(db, src_label, "daily", dt, round(float(val_mm), 2), {"event_window": "2013_monsoon"})
            records_added += 1

    db.commit()
    log(f"Stored {records_added} precipitation records ({src_label})", 1.0)
    return {"source": src_label, "records_stored": records_added}


def _upsert_rain(db, source: str, period: str, dt: datetime, mm: float, params: dict) -> None:
    row = db.query(RainfallRecord).filter_by(source=source, period=period, date=dt).first()
    if row is None:
        row = RainfallRecord(source=source, period=period, date=dt)
        db.add(row)
    row.precipitation_mm = mm
    row.location = {"type": "Point", "coordinates": [KEDARNATH_PT["lon"], KEDARNATH_PT["lat"]]}
    row.parameters = params


def rainfall_summary(db) -> dict:
    rows = db.query(RainfallRecord).order_by(RainfallRecord.date).all()
    by_src: dict[str, list[dict]] = {}
    for r in rows:
        key = f"{r.source}_{r.period}"
        by_src.setdefault(key, []).append({
            "date": r.date.strftime("%Y-%m-%d"),
            "year": r.date.year,
            "month": r.date.month,
            "precipitation_mm": r.precipitation_mm,
        })

    # Compute June anomaly statistics if monthly series exists
    june_stats = {}
    for key, items in by_src.items():
        if not key.endswith("_monthly"):
            continue
        junes = [x["precipitation_mm"] for x in items if x["month"] == 6 and x["precipitation_mm"] is not None]
        j2013 = next((x["precipitation_mm"] for x in items if x["year"] == 2013 and x["month"] == 6), None)
        if junes:
            mean_j = float(np.mean(junes))
            std_j = float(np.std(junes)) or 1.0
            june_stats[key] = {
                "climatological_june_mean_mm": round(mean_j, 1),
                "climatological_june_std_mm": round(std_j, 1),
                "june_2013_mm": j2013,
                "june_2013_z_score": round((j2013 - mean_j) / std_j, 2) if j2013 is not None else None,
            }

    return {
        "sources_available": sorted(by_src.keys()),
        "series": by_src,
        "june_anomalies": june_stats,
        "notes": [
            "CHIRPS (0.05°) and GPM IMERG (0.1°) are retrieved via Google Earth Engine when GEE credentials are configured.",
            "NASA POWER MERRA-2 (PRECTOTCORR) provides open, unauthenticated daily & monthly precipitation over 30.735°N, 79.067°E (0.5°×0.625° grid cell; coarse grid smooths localized orographic peaks relative to station gauges at Chorabari/Kedarnath).",
        ],
    }

