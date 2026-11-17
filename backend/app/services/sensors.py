"""Mission-specific sensor definitions.

Band names, scaling factors, native resolutions and QA conventions differ between
Landsat TM/ETM+/OLI and Sentinel-2 MSI, so every mission has an explicit definition.
Common (harmonised) band names used internally: blue, green, red, nir, swir1, swir2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class SensorSpec:
    mission: str
    label: str
    gee_collection: str
    instrument: str
    native_resolution_m: dict[str, float]
    gee_bands: dict[str, str]  # common name -> GEE band name
    stac_assets: dict[str, str]  # common name -> STAC asset key (Planetary Computer / Earth Search)
    stac_collection: str
    stac_platform: str | None
    operational: tuple[date, date | None]
    scale: float
    offset: float
    notes: list[str] = field(default_factory=list)
    citation: str = ""


USGS_C2_CITATION = (
    "U.S. Geological Survey (2021). Landsat Collection 2 Level-2 Science Products. "
    "https://doi.org/10.5066/P9OGBGM6 (L4-5 TM), https://doi.org/10.5066/P9C7I13B (L7 ETM+), "
    "https://doi.org/10.5066/P9OGBGM6 (L8-9 OLI/TIRS)"
)

SENSORS: dict[str, SensorSpec] = {
    "landsat5": SensorSpec(
        mission="landsat5", label="Landsat 5 TM", instrument="TM",
        gee_collection="LANDSAT/LT05/C02/T1_L2",
        native_resolution_m={"blue": 30, "green": 30, "red": 30, "nir": 30, "swir1": 30, "swir2": 30},
        gee_bands={"blue": "SR_B1", "green": "SR_B2", "red": "SR_B3", "nir": "SR_B4", "swir1": "SR_B5", "swir2": "SR_B7", "qa": "QA_PIXEL"},
        stac_assets={"blue": "blue", "green": "green", "red": "red", "nir": "nir08", "swir1": "swir16", "swir2": "swir22", "qa": "qa_pixel"},
        stac_collection="landsat-c2-l2", stac_platform="landsat-5",
        operational=(date(1984, 3, 16), date(2012, 6, 5)), scale=2.75e-05, offset=-0.2,
        notes=["Routine TM imaging over India ended Nov 2011; 2012 coverage is effectively absent.",
               "Use 2000–2011 TM scenes for the pre-disaster baseline."],
        citation=USGS_C2_CITATION,
    ),
    "landsat7": SensorSpec(
        mission="landsat7", label="Landsat 7 ETM+", instrument="ETM+",
        gee_collection="LANDSAT/LE07/C02/T1_L2",
        native_resolution_m={"blue": 30, "green": 30, "red": 30, "nir": 30, "swir1": 30, "swir2": 30},
        gee_bands={"blue": "SR_B1", "green": "SR_B2", "red": "SR_B3", "nir": "SR_B4", "swir1": "SR_B5", "swir2": "SR_B7", "qa": "QA_PIXEL"},
        stac_assets={"blue": "blue", "green": "green", "red": "red", "nir": "nir08", "swir1": "swir16", "swir2": "swir22", "qa": "qa_pixel"},
        stac_collection="landsat-c2-l2", stac_platform="landsat-7",
        operational=(date(1999, 4, 15), date(2024, 1, 19)), scale=2.75e-05, offset=-0.2,
        notes=["Scan Line Corrector failed 31 May 2003: ~22% of each post-2003 scene is missing "
               "(wedge-shaped gaps). Gap pixels are flagged as fill in QA_PIXEL and are treated as "
               "NoData – never as valid observations. Valid-pixel fraction is reported per composite.",
               "Orbit drift after 2017 changes local acquisition time (illumination differences)."],
        citation=USGS_C2_CITATION,
    ),
    "landsat8": SensorSpec(
        mission="landsat8", label="Landsat 8 OLI", instrument="OLI",
        gee_collection="LANDSAT/LC08/C02/T1_L2",
        native_resolution_m={"blue": 30, "green": 30, "red": 30, "nir": 30, "swir1": 30, "swir2": 30},
        gee_bands={"blue": "SR_B2", "green": "SR_B3", "red": "SR_B4", "nir": "SR_B5", "swir1": "SR_B6", "swir2": "SR_B7", "qa": "QA_PIXEL"},
        stac_assets={"blue": "blue", "green": "green", "red": "red", "nir": "nir08", "swir1": "swir16", "swir2": "swir22", "qa": "qa_pixel"},
        stac_collection="landsat-c2-l2", stac_platform="landsat-8",
        operational=(date(2013, 4, 11), None), scale=2.75e-05, offset=-0.2,
        notes=["OLI has narrower spectral bands than TM/ETM+; cross-sensor index differences of a few "
               "percent are expected (Roy et al., 2016). Treat small TM/ETM+→OLI shifts with caution."],
        citation=USGS_C2_CITATION,
    ),
    "landsat9": SensorSpec(
        mission="landsat9", label="Landsat 9 OLI-2", instrument="OLI-2",
        gee_collection="LANDSAT/LC09/C02/T1_L2",
        native_resolution_m={"blue": 30, "green": 30, "red": 30, "nir": 30, "swir1": 30, "swir2": 30},
        gee_bands={"blue": "SR_B2", "green": "SR_B3", "red": "SR_B4", "nir": "SR_B5", "swir1": "SR_B6", "swir2": "SR_B7", "qa": "QA_PIXEL"},
        stac_assets={"blue": "blue", "green": "green", "red": "red", "nir": "nir08", "swir1": "swir16", "swir2": "swir22", "qa": "qa_pixel"},
        stac_collection="landsat-c2-l2", stac_platform="landsat-9",
        operational=(date(2021, 10, 31), None), scale=2.75e-05, offset=-0.2,
        citation=USGS_C2_CITATION,
    ),
    "sentinel2": SensorSpec(
        mission="sentinel2", label="Sentinel-2 MSI (L2A)", instrument="MSI",
        gee_collection="COPERNICUS/S2_SR_HARMONIZED",
        native_resolution_m={"blue": 10, "green": 10, "red": 10, "nir": 10, "swir1": 20, "swir2": 20},
        gee_bands={"blue": "B2", "green": "B3", "red": "B4", "nir": "B8", "swir1": "B11", "swir2": "B12", "scl": "SCL"},
        stac_assets={"blue": "blue", "green": "green", "red": "red", "nir": "nir", "swir1": "swir16", "swir2": "swir22", "scl": "scl"},
        stac_collection="sentinel-2-l2a", stac_platform=None,
        operational=(date(2015, 6, 23), None), scale=1e-4, offset=0.0,
        notes=["L2A surface reflectance is systematically available over India from ~2017; 2015–2016 "
               "coverage is sparse.",
               "Processing baseline 04.00 (25 Jan 2022) introduced a −1000 DN BOA offset. The GEE "
               "HARMONIZED collection and the STAC asset scale/offset metadata are used to remove it.",
               "SWIR bands are 20 m; MNDWI is computed at 20 m unless explicitly resampled."],
        citation="European Space Agency, Copernicus Sentinel-2 MSI Level-2A. Contains modified Copernicus Sentinel data.",
    ),
    "sentinel1": SensorSpec(
        mission="sentinel1", label="Sentinel-1 C-band SAR (GRD)", instrument="C-SAR",
        gee_collection="COPERNICUS/S1_GRD",
        native_resolution_m={"vv": 10, "vh": 10},
        gee_bands={"vv": "VV", "vh": "VH", "angle": "angle"},
        stac_assets={"vv": "vv", "vh": "vh"},
        stac_collection="sentinel-1-rtc", stac_platform=None,
        operational=(date(2014, 10, 3), None), scale=1.0, offset=0.0,
        notes=["Steep Himalayan terrain causes layover/shadow; radar water maps must be masked with "
               "a DEM-derived layover/shadow mask. Sentinel-1B failed Dec 2021 (reduced revisit).",
               "Radar backscatter thresholds for water are scene-dependent (Otsu per scene)."],
        citation="European Space Agency, Copernicus Sentinel-1 GRD. Contains modified Copernicus Sentinel data.",
    ),
}

LANDSAT_MISSIONS = ("landsat5", "landsat7", "landsat8", "landsat9")
OPTICAL_MISSIONS = LANDSAT_MISSIONS + ("sentinel2",)
L7_SLC_FAILURE = date(2003, 5, 31)

# Landsat C2 QA_PIXEL bit positions
QA_BITS = {"fill": 0, "dilated_cloud": 1, "cirrus": 2, "cloud": 3, "cloud_shadow": 4, "snow": 5, "clear": 6, "water": 7}
# Sentinel-2 Scene Classification Layer classes to mask
S2_SCL_MASK = {0: "no_data", 1: "saturated_defective", 3: "cloud_shadow", 8: "cloud_medium", 9: "cloud_high", 10: "thin_cirrus"}


def missions_for_year(year: int) -> list[str]:
    """Optical missions with potential data for a given year (scene availability still varies)."""
    out = []
    for m in OPTICAL_MISSIONS:
        s = SENSORS[m]
        start, end = s.operational
        if start.year <= year and (end is None or end.year >= year):
            out.append(m)
    return out


def preferred_landsat_for_year(year: int) -> str:
    """Prefer the sensor with the best quality for each year (avoid L7 SLC-off when possible)."""
    if year <= 2011:
        return "landsat5"
    if year == 2012:
        return "landsat7"  # only Landsat available; SLC-off gaps flagged
    if year >= 2022:
        return "landsat8"  # landsat9 also available; combined in multi-mission composites
    return "landsat8"

