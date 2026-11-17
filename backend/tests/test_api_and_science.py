"""Comprehensive API & scientific-integrity test suite for GlacioGuard AI."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.services import dl_service, hydrology, indices


def test_spectral_indices_and_otsu():
    green = np.array([[0.25, 0.08], [0.15, 0.30]], dtype="float32")
    nir = np.array([[0.05, 0.35], [0.40, 0.04]], dtype="float32")
    swir1 = np.array([[0.03, 0.25], [0.22, 0.02]], dtype="float32")
    red = np.array([[0.10, 0.06], [0.05, 0.12]], dtype="float32")

    w = indices.ndwi(green, nir)
    m = indices.mndwi(green, swir1)
    v = indices.ndvi(nir, red)
    assert w[0, 0] > 0.5 and w[0, 1] < 0
    assert m[0, 0] > 0.6 and m[1, 0] < 0
    assert v[0, 1] > 0.5 and v[0, 0] < 0


def test_d8_hydrology_on_synthetic_valley():
    r, c = np.indices((20, 20), dtype="float64")
    z = 4000.0 - r * 15.0 + np.abs(c - 10.0) * 8.0
    z[10, 10] -= 40.0  # artificial depression
    filled = hydrology.priority_flood_fill(z)
    assert filled[10, 10] > z[10, 10]
    fdir = hydrology.d8_flow_direction(filled, 30.0)
    acc, _ = hydrology.flow_accumulation(filled, fdir)
    assert acc[19, 10] > 50


def test_unet_and_deeplabv3plus_forward_shapes():
    import torch
    x = torch.randn(2, 6, 256, 256)
    for arch in ("unet", "deeplabv3plus"):
        m = dl_service.build_model(arch, in_channels=6)
        y = m(x)
        assert y.shape == (2, 1, 256, 256)


def test_all_api_endpoints():
    with TestClient(app) as client:
        # 1. Health & Study Area
        h = client.get("/api/health").json()
        assert h["status"] == "ok" and h["data"]["dem"] is True

        sa = client.get("/api/study-area").json()
        assert sa["utm_epsg"] == 32644 and "mandakini_corridor" in sa["regions"]

        # 2. Dashboard Summary
        summary = client.get("/api/dashboard/summary").json()
        assert summary["coverage"]["dem_available"] is True
        assert summary["lakes"]["count"] >= 1

        # 3. Satellite & Composites
        missions = client.get("/api/satellite/missions").json()
        assert len(missions) == 6
        comps = client.get("/api/satellite/composites").json()
        assert len(comps) >= 6

        # 4. Raster Overlays
        first_raster_id = comps[0]["raster"]["id"]
        ov = client.get(f"/api/rasters/{first_raster_id}/overlay").json()
        assert "image_url" in ov and len(ov["bounds"]) == 2
        png_resp = client.get(ov["image_url"])
        assert png_resp.status_code == 200 and png_resp.headers["content-type"] == "image/png"

        # 5. Glacial Lakes
        inv = client.get("/api/lakes/inventory").json()
        assert inv["type"] == "FeatureCollection" and len(inv["features"]) >= 1
        stats = client.get("/api/lakes/statistics").json()
        assert len(stats["annual"]) >= 1

        # 6. Historical Change & 2013 Disaster
        ind = client.get("/api/change-detection/indicators?region=full_aoi").json()
        assert "water_area_ha" in ind["indicators"]
        cd = client.post("/api/change-detection/analyse", json={"year_a": 2012, "year_b": 2013, "indicator": "water", "region": "full_aoi"})
        assert cd.status_code == 200 and "statistics" in cd.json()

        dis = client.post("/api/disaster/compare", json={"pre_year": 2011, "post_year": 2013, "region": "mandakini_corridor"})
        assert dis.status_code == 200 and len(dis.json()["affected_locations"]) >= 4

        # 7. Glacier Summary
        gl = client.get("/api/glacier/summary").json()
        assert "series" in gl and "outlines" in gl

        # 8. GLOF Susceptibility
        meth = client.get("/api/glof/methodology").json()
        assert meth["is_trained_model"] is False
        susc = client.get("/api/glof/assessments").json()
        assert len(susc) >= 1 and susc[0]["category"] in ("Low", "Moderate", "High", "Very High")

        # 9. Terrain & Flowpath
        ts = client.get("/api/terrain/summary").json()
        assert ts["available"] is True and "elevation" in ts["products"]
        fp = client.post("/api/terrain/flowpath", json={"lon": 79.0580, "lat": 30.7470})
        assert fp.status_code == 200 and fp.json()["length_m"] > 1000

        # 10. Flood Scenarios & Exposure
        scens = client.get("/api/flood/scenarios").json()
        assert len(scens) >= 1 and scens[0]["scenario_type"] == "hypothetical"
        inf_s = client.get("/api/exposure/infrastructure/summary").json()
        assert inf_s["total"] > 500
        exp = client.post("/api/exposure/analyse", json={"buffer_m": 250.0, "hand_max_m": 25.0})
        assert exp.status_code == 200 and exp.json()["statistics"]["buildings"] > 0

        # 11. Rainfall & Model Lab & PDF Report
        rain = client.get("/api/rainfall").json()
        assert len(rain["sources_available"]) >= 1
        ml = client.get("/api/models/datasets").json()
        assert ml["segmentation"]["image_tiles"] >= 1
        rep = client.post("/api/reports/generate", json={"title": "Automated Verification Report"})
        assert rep.status_code == 200
        pdf = client.get(rep.json()["download_url"])
        assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
