"""Build the self-contained Master Gemini Handover & Report Context Document."""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
RESEARCH_DIR = PROJECT_DIR / "research"
TAB_DIR = RESEARCH_DIR / "tables"

HEADER = """# MASTER PROJECT HANDOVER FOR GEMINI — GLACIOGUARD AI (2000–2026)

> **HOW TO USE THIS FILE WITH GEMINI:**  
> Upload or copy-paste this entire file (`research/GEMINI_REPORT_HANDOVER.md`) along with the images from `research/figures/` and `research/graphs/` into Gemini and use this prompt:  
> *"Using the complete empirical data, methodology, equations, 12 tables, 15 figure descriptions, and 10 graph descriptions in this handover document, write a complete final-year engineering thesis / IEEE research report for GlacioGuard AI. Do not invent any numbers—use the exact values from Tables 1–12 and reference Figures 1–15 and Graphs 1–10 throughout the text."*

---

## 1. PROJECT IDENTITY & STUDY AREA

- **Full Title:** *GlacioGuard AI: Historical-to-Present Geospatial and Deep Learning-Based Glacial Lake Outburst Flood (GLOF) Susceptibility and Downstream Flood Risk Assessment of the Kedarnath Region, Uttarakhand, India (2000–2026)*
- **Primary Study Basin:** Kedarnath–Chorabari Glacier–Gandhi Sarovar–Mandakini River Basin, Rudraprayag District, Uttarakhand, India.
- **Spatial Extent (EPSG:4326):** `78.92°E to 79.14°E`, `30.58°N to 30.82°N` (`~495 km²` total AOI).
- **Metric Analysis Projection:** WGS 84 / UTM Zone 44N (`EPSG:32644`), snapped to a `30 m × 30 m` grid (`719 × 900` pixels = `647,100` grid cells).
- **Four Analysis Sub-Regions:**
  1. `full_aoi` — Upper Mandakini Basin (`78.92°E–79.14°E, 30.58°N–30.82°N`)
  2. `chorabari` — Chorabari Glacier & Gandhi Sarovar Headwaters (`79.035°E–79.095°E, 30.735°N–30.800°N`)
  3. `kedarnath_valley` — Kedarnath Township & Outwash Fan (`79.040°E–79.090°E, 30.715°N–30.750°N`)
  4. `mandakini_corridor` — Mandakini Gorge Corridor from Kedarnath to Sonprayag (`78.980°E–79.085°E, 30.620°N–30.745°N`)
- **Key Reference Landmarks:**
  - **Chorabari Lake (Gandhi Sarovar / Chorabari Tal):** `30.7470°N, 79.0580°E` (`~3,848.1 m` a.s.l. on 30 m DEM; field moraine crest `~3,960 m`)
  - **Chorabari Glacier Snout Zone:** `30.7545°N, 79.0605°E`
  - **Kedarnath Township:** `30.7346°N, 79.0669°E` (`~3,532–3,553 m` a.s.l.)
  - **Rambara Gorge:** `30.7080°N, 79.0595°E` (`~2,705–3,095 m` a.s.l.)
  - **Gaurikund:** `30.6530°N, 79.0260°E` (`~1,975–1,985 m` a.s.l.)
  - **Sonprayag Confluence (Mandakini + Basuki/Songanga):** `30.6330°N, 78.9990°E` (`~1,635–1,700 m` a.s.l.)
- **Historical Timeline:**
  - `2000–2012`: Pre-disaster environmental baseline (`Landsat 5 TM` & `Landsat 7 ETM+`).
  - `June 2013`: Compound hydrometeorological and GLOF disaster (`15–17 June 2013`).
  - `2014–2019`: Post-disaster channel reorganization and vegetation recovery (`Landsat 8 OLI` & `Sentinel-2 MSI`).
  - `2020–2026 (YTD)`: Recent environmental monitoring and present-day susceptibility screening (`Sentinel-2 L2A` & `Landsat 8/9`). *Note: 2026 is treated strictly as year-to-date.*

---

## 2. SCIENTIFIC CONTEXT OF THE JUNE 2013 KEDARNATH DISASTER

The 15–17 June 2013 catastrophe was a **compound multi-hazard event** and must not be attributed to a single mechanism:
1. **Extreme Orographic Rainfall & Snowmelt Flash Floods (15–16 June 2013):** Interaction between an upper-tropospheric western disturbance and the monsoonal trough produced extreme continuous rainfall across snow-covered catchments, causing severe flash flooding along both the Saraswati and Mandakini rivers on 16 June 2013 before the lake breach.
2. **Glacial Lake Outburst Flood (17 June 2013 morning, ~06:45–07:00 IST):** Rapid infilling of Chorabari Lake (Gandhi Sarovar) to `~4.10 ha` (`~3.7 × 10⁵ m³`, max depth `~14.6 m`) overtopped and breached the unconsolidated moraine dam, releasing a catastrophic water-debris wave down the steep (`>15°`) Chorabari stream channel onto Kedarnath.
3. **Landslides, Bank Undercutting & Debris Flows:** Saturated moraine and colluvial valley walls failed throughout the gorge (`Kedarnath → Rambara → Gaurikund → Sonprayag`), stripping riparian vegetation (`+122 ha` new exposed bare debris in the Mandakini corridor) and bulking peak flood discharges.
4. **Combined Downstream Exposure:** Dense pilgrimage settlements, roads, and bridges located inside the low-HAND valley floor experienced compound hydro-geomorphic destruction.

---

## 3. COMPLETE SYSTEM ARCHITECTURE & METHODOLOGY

### 3.1 Full-Stack Software Architecture
- **Frontend (`frontend/`):** React 18, TypeScript, Vite 5, Tailwind CSS, React-Leaflet (Leaflet 1.9), Recharts, Lucide React icons. Implements 12 dedicated scientific modules (`OverviewDashboard`, `SatelliteExplorer`, `GlacialLakeDetection`, `HistoricalChangeAnalysis`, `DisasterImpactAnalysis`, `GlacierMonitoring`, `GlofSusceptibility`, `FloodSimulation`, `InfrastructureExposure`, `GeoTiffWorkspace`, `ModelLab`, `ReportGenerator`) plus a dual-overlay `<SwipeCompare>` slider and `<GeoMap>` GIS controller.
- **Backend (`backend/`):** Python, FastAPI, Pydantic v2, SQLAlchemy 2.0 + GeoAlchemy2 (`17` spatial/relational tables in PostgreSQL 16 + PostGIS 3.4 / SQLite GeoJSON).
- **Geospatial & Hydrological Engine:** Google Earth Engine Python API (`13` server-side processing functions in `gee_service.py`) + public STAC Cloud-Optimised GeoTIFF pipeline (`stac_service.py` via Microsoft Planetary Computer & AWS Earth Search), Rasterio/GDAL, GeoPandas, Shapely 2, PyProj.

### 3.2 Sensor Harmonisation & Spectral Indices
- **Landsat 5 TM / 7 ETM+ (`LANDSAT/LT05/C02/T1_L2`, `LE07`):** Bands `SR_B1..SR_B5, SR_B7` scaled via $\\rho = \\text{DN} \\times 2.75\\times 10^{-5} - 0.2$; cloud/shadow/fill masked via `QA_PIXEL`. Post-May 2003 Landsat 7 SLC-off wedge gaps (`~22%` of scene) are masked as `NaN` (`fill` bit 0) and never treated as valid observations.
- **Landsat 8 OLI / 9 OLI-2 (`LC08`, `LC09`):** Bands `SR_B2..SR_B7` scaled via $\\rho = \\text{DN} \\times 2.75\\times 10^{-5} - 0.2$; cirrus (`bit 2`) + cloud/shadow masked.
- **Sentinel-2 MSI L2A (`COPERNICUS/S2_SR_HARMONIZED`):** Bands `B2, B3, B4, B8, B11, B12` scaled by $10^{-4}$ with Baseline `04.00` BOA offset harmonised; masked using Scene Classification Layer (`SCL` classes `0, 1, 3, 8, 9, 10`).
- **Spectral Indices:**
  - $\\text{NDWI} = \\frac{\\rho_{\\text{green}} - \\rho_{\\text{nir}}}{\\rho_{\\text{green}} + \\rho_{\\text{nir}}}$ (McFeeters, 1996)
  - $\\text{MNDWI} = \\frac{\\rho_{\\text{green}} - \\rho_{\\text{swir1}}}{\\rho_{\\text{green}} + \\rho_{\\text{swir1}}}$ (Xu, 2006)
  - $\\text{NDVI} = \\frac{\\rho_{\\text{nir}} - \\rho_{\\text{red}}}{\\rho_{\\text{nir}} + \\rho_{\\text{red}}}$ (Tucker, 1979)
  - $\\text{NDSI} = \\frac{\\rho_{\\text{green}} - \\rho_{\\text{swir1}}}{\\rho_{\\text{green}} + \\rho_{\\text{swir1}}}$ (Hall et al., 1995; snow/ice where $\\text{NDSI} > 0.40, \\rho_{\\text{nir}} > 0.11, \\rho_{\\text{green}} > 0.10$)
  - $\\text{NBR} = \\frac{\\rho_{\\text{nir}} - \\rho_{\\text{swir2}}}{\\rho_{\\text{nir}} + \\rho_{\\text{swir2}}}$ (Key & Benson, 2006)
- **Topographically Conditioned Glacial Lake Detection:** Combines adaptive Otsu thresholding on `MNDWI` (`clipped to [0.12, 0.30]`), `NDWI > 0.08`, `green > 0.035`, `nir < 0.18`, `swir1 < 0.12`, DEM slope $\\le 16^\\circ$, DEM hillshade $\\ge 105$ (suppressing deep mountain cast shadows), and elevation $\\ge 2,800\\text{ m}$.

### 3.3 DEM Terrain & Priority-Flood D8 Hydrological Conditioning
- **Source DEM:** Copernicus Global DEM GLO-30 (`30 m`, TanDEM-X InSAR epoch, EGM2008 orthometric height) warped to `EPSG:32644`.
- **Derivatives (`hydrology.py`):** Horn (1981) $3\\times 3$ slope and aspect, standard hillshade (azimuth $315^\\circ$, altitude $45^\\circ$), Riley et al. (1999) Terrain Ruggedness Index (TRI), Barnes et al. (2014) Priority-Flood $+\\varepsilon$ depression filling, O'Callaghan & Mark (1984) D8 flow direction & topological flow accumulation, Strahler stream ordering (threshold $\\ge 1.0\\text{ km}^2$, yielding `51.94 km` of mapped streams up to Strahler order `3`), watershed delineation (`4` basins), and Height Above Nearest Drainage (`HAND`, Rennó et al., 2008).

### 3.4 Deep Learning Semantic Segmentation (`U-Net` vs `DeepLabV3+`)
- **Input Tensor:** 6-band harmonised optical reflectance (`blue, green, red, nir, swir1, swir2`) sliced into $128\\times 128$ patches (`65` verified water-containing multi-temporal tiles across 2000–2024).
- **Leakage-Free Partitioning:** Geographic longitudinal block split (`West 60% = 39 train tiles`, `Central 20% = 13 validation tiles`, `East 20% = 13 held-out test tiles`) stratified by foreground presence.
- **Architectures & Normalization:** 4-stage `UNet` (`32→64→128→256→512` channels) and `DeepLabV3Plus` (ASPP dilation rates `1, 6, 12, 18` + low-level skip decoder) using `GroupNorm` for batch-size-invariant evaluation stability.
- **Loss Function:** Class-imbalance-weighted $0.35 \\times \\text{BCEWithLogitsLoss}(w_{\\text{pos}}=6.0) + 0.65 \\times \\text{SoftDiceLoss}$, trained for `32` epochs with AdamW ($\\text{lr}=2\\times 10^{-3}$).
- **Held-Out Geographic Test Split Results:**
  - **`U-Net` (Best Epoch 32):** `IoU = 0.6105`, `Dice / F1 = 0.7582`, `Precision = 0.8197`, `Recall = 0.7052`, `Pixel Accuracy = 0.9857` (`TN = 205,194, FP = 1,047, FN = 1,990, TP = 4,761`). Live sliding-window inference on the 2024 Sentinel-2 composite detected `25` lakes (`60.39 ha`).
  - **`DeepLabV3+` (Best Epoch 31):** `IoU = 0.4618`, `Dice / F1 = 0.6319`, `Precision = 0.6025`, `Recall = 0.6642`, `Pixel Accuracy = 0.9755` (`TN = 203,283, FP = 2,958, FN = 2,267, TP = 4,484`).

### 3.5 GLOF Multi-Criteria Susceptibility Screening (`mcda_screening_v1`)
Grounded in GAPHAZ (2017), Huggel et al. (2002), Worni et al. (2013), and Allen et al. (2019), evaluating 9 weighted criteria:
1. Steep ($30^\\circ\\text{–}60^\\circ$) upslope avalanche source area fraction within `1 km` (`weight = 0.18`)
2. Multi-temporal lake expansion rate (`%/yr`, `weight = 0.16`)
3. Proximity to glacier / perennial ice (`m`, `weight = 0.16`)
4. Lake surface area (`ha`, proxy for volume, `weight = 0.12`)
5. Downstream outlet channel gradient over first `1 km` (`deg`, `weight = 0.12`)
6. Surrounding 90th-percentile slope within `500 m` (`deg`, `weight = 0.10`)
7. Distance from outlet to mapped D8 stream (`m`, `weight = 0.06`)
8. Lake elevation (`m a.s.l.`, `weight = 0.05`)
9. Moraine dam freeboard / internal ice core (`field survey parameter`, `weight = 0.05`, propagated into uncertainty bounds `[score_low, score_high]`).
- **Top-Ranked Lake:** `KED-GL-003 Chorabari Lake (Gandhi Sarovar)` at `3,848.1 m` achieved the `#1` screening index of **`0.805` (`Very High`, sensitivity interval `[0.657, 0.825]`)**, followed by `KED-GL-007` (`5,144.7 m`, index **`0.776`**, `Very High`).

---

## 4. COMPLETE CATALOG OF FIGURES (`research/figures/`) & GRAPHS (`research/graphs/`)

### Spatial Map Figures (`300 DPI` PNGs in `research/figures/`)
- **`fig01_study_area_and_dem.png`:** Kedarnath–Chorabari–Mandakini study area showing Copernicus GLO-30 elevation (`1,396–6,862 m`), hillshade, Strahler D8 drainage network (`51.94 km`), and key settlements/glaciers.
- **`fig02_terrain_and_hydrology_6panel.png`:** 6-panel DEM geomorphometry (`Elevation`, `Horn Slope`, `Aspect`, `TRI Roughness`, `Log10 Flow Accumulation`, `HAND`).
- **`fig03_satellite_composites_timeline_2000_2026.png`:** Post-monsoon true-colour satellite composite gallery across `2000, 2011, 2012, 2013, 2015, 2020, 2024, 2026-YTD`.
- **`fig04_historical_change_maps_6pairs.png`:** Multi-decadal transition maps (`Stable`, `Gain/Recovery`, `Loss/Disturbance`) across all 6 mandated epochs (`2000→2012`, `2012→2013`, `2013→2015`, `2015→2020`, `2020→2024`, `2024→2026-YTD`).
- **`fig05_2013_kedarnath_disaster_impact.png`:** 4-panel June 2013 Kedarnath disaster analysis (`2011 Pre-Disaster RGB`, `2013 Post-Disaster RGB`, `ΔNDVI` corridor vegetation stripping in bright red, and `+122 ha` exposed debris/sediment transition).
- **`fig06_glacial_lake_inventory_and_chorabari.png`:** Regional glacial lake inventory (`n = 33`) coloured by GLOF susceptibility category + headwater zoom on Chorabari Lake and its `23.7 km` D8 outburst flow path.
- **`fig07_glacier_snow_ice_retreat_chorabari.png`:** False-colour (`SWIR1-NIR-Red`) and `NDSI` snow/ice change in the Chorabari zone (`2000 → 2024`).
- **`fig08_downstream_infrastructure_exposure_map.png`:** `1,191` OpenStreetMap infrastructure features overlaid with the Chorabari → Mandakini D8 + HAND potential exposure corridor (`236` exposed features: `148` buildings, `11.66 km` roads, `17` bridges, and settlements `Gaurikund`, `Mundhya Chak`, `Sonprayag`).
- **`fig09_2013_pre_during_post_satellite_and_ndwi.png`:** 8-panel intra-2013 flood progression (`Pre-Flood May 2013`, `During-Flood June 2013`, `Monsoon High-Flow July–Aug 2013`, `Post-Flood Sept–Nov 2013`) displaying optical RGB and corridor `max(NDWI, MNDWI)` water intensity.
- **`fig10_chorabari_lake_pre_during_post_2013_zoom.png`:** High-resolution zoom on Chorabari Lake (Gandhi Sarovar) & Kedarnath Township across `Autumn 2012`, `May 2013`, `June 2013 Outburst`, and `Autumn 2013 Drained Basin`.
- **`fig11_mandakini_corridor_water_depth_pre_during_post.png`:** 4-stage valley flow depth (`Δh`, m) and inundation area progression (`160.1 ha` Pre-Flood baseflow → `196.3 ha` on 16 June rainfall flash flood → `259.5 ha` on 17 June Chorabari GLOF outburst peak → `163.6 ha` Post-Flood autumn recession).
- **`fig12_settlement_zoom_water_levels_4sites.png`:** `4×3` settlement-scale water depth comparison (`Pre-Flood`, `17 June Peak`, `Post-Flood`) at Kedarnath, Rambara, Gaurikund, and Sonprayag.
- **`fig13_valley_cross_section_water_levels_2013.png`:** Real Copernicus GLO-30 DEM cross-sections showing exact water surface elevations (`WSE`), flow depth rise (`+12.5 m` at Kedarnath overtopping the dual-channel divide; `+17.5 m` at Rambara gorge; `+15.8 m` at Gaurikund; `+14.2 m` at Sonprayag), and wetted top widths.
- **`fig14_water_difference_maps_pre_vs_during_vs_post.png`:** Differential water-index maps (`During − Pre`, `Post − During`) and peak water-level surge (`ΔWSE`).
- **`fig15_3d_perspective_mandakini_flood_inundation_2013.png`:** 3D topographic gorge perspective comparing Pre-Flood baseflow (`~1.8 m`) vs 17 June 2013 GLOF peak inundation (`~17.5 m`).

### Analytical Graphs (`300 DPI` PNGs in `research/graphs/`)
- **`graph01_environmental_indicators_2000_2026.png`:** 2000–2026 trajectories of Surface Water Area (`ha`), Snow/Ice Area (`ha`), Mean `NDVI`, and Exposed Bare Ground (`ha`).
- **`graph02_standard_epoch_changes_bar.png`:** Epoch-by-epoch area gains vs losses for vegetation and surface water.
- **`graph03_rainfall_climatology_and_june2013_anomaly.png`:** 2000–2025 June rainfall climatology (`June 2013 = 670.8 mm`, `z = +3.32σ`) and daily June 2013 rainfall time series.
- **`graph04_glof_susceptibility_ranking_and_uncertainty.png`:** Top 15 lakes ranked by GLOF susceptibility index with uncertainty bars + factor breakdown for `#1 KED-GL-003 (Chorabari Lake)`.
- **`graph05_chorabari_mandakini_flowpath_profile.png`:** `23.7 km` longitudinal elevation drop (`2,218 m` total drop from `3,848 m` to `1,630 m`) from Chorabari Lake to Sonprayag.
- **`graph06_unet_vs_deeplabv3plus_training_and_metrics.png`:** PyTorch `U-Net` vs `DeepLabV3+` loss curves, validation IoU/Dice progression, and held-out geographic test split metrics.
- **`graph07_infrastructure_exposure_breakdown.png`:** AOI total vs corridor potentially exposed OpenStreetMap infrastructure counts.
- **`graph08_intra2013_monthly_water_and_wetness_progression.png`:** Intra-2013 stage-by-stage active wet corridor area (`21.1 ha → 228.0 ha → 21.2 ha`) and 90th-percentile water index surge (`-0.226 → +0.455 → -0.126`).
- **`graph09_water_level_and_depth_by_location_pre_during_post.png`:** Quantitative water depth rise (`m`) and wetted valley top width (`m`) across Pre-, During-, and Post-Flood stages at the 4 settlements.
- **`graph10_chorabari_lake_volume_and_area_timeline.png`:** Chorabari Lake surface area (`1.53 ha → 4.10 ha peak → 0.12 ha drained`), max water depth (`~14.6 m` peak), and storage volume (`~3.7 × 10⁵ m³` peak) evolution.

---

## 5. COMPLETE EMPIRICAL DATA TABLES (TABLES 1 TO 12)
"""

FOOTER = """
---

## 6. KEY ACADEMIC REFERENCES FOR CITATION IN THE REPORT

1. **Allen, S. K., Rastner, P., Arora, M., Huggel, C., & Stoffel, M. (2016).** Lake outburst and debris flow disasters, with a focus on the June 2013 event in Uttarakhand, India. *Landslides*, 13(6), 1479–1491.
2. **Allen, S. K., Zhang, G., Wang, W., Yao, T., & Bolch, T. (2019).** Potentially dangerous glacial lakes across the Tibetan Plateau revealed using a large-scale automated assessment approach. *Science Bulletin*, 64(7), 435–445.
3. **Barnes, R., Lehman, C., & Mulla, D. (2014).** Priority-flood: An optimal depression-filling and watershed-labeling algorithm for digital elevation models. *Computers & Geosciences*, 62, 117–127.
4. **Chen, L. C., Zhu, Y., Papandreou, G., Schroff, F., & Adam, H. (2018).** Encoder-decoder with atrous separable convolution for semantic image segmentation (DeepLabV3+). *ECCV 2018*, 801–818.
5. **Das, S., Kar, N. S., & Bandyopadhyay, S. (2015).** Glacial lake outburst flood at Kedarnath, Indian Himalaya: a study using digital elevation models and satellite images. *Natural Hazards*, 77(2), 769–786.
6. **Dobhal, D. P., Gupta, A. K., Mehta, M., & Khandelwal, D. D. (2013).** Kedarnath disaster: facts and plausible causes. *Current Science*, 105(2), 171–174.
7. **GAPHAZ (2017).** *Assessment of Glacier and Permafrost Hazards in Mountain Regions: Technical Guidance Document*. Standing Group on Glacier and Permafrost Hazards in Mountains (IACS/IPA), Zurich.
8. **Hall, D. K., Riggs, G. A., & Salomonson, V. V. (1995).** Development of methods for mapping global snow cover using moderate resolution imaging spectroradiometer data. *Remote Sensing of Environment*, 54(2), 127–140.
9. **Horn, B. K. P. (1981).** Hill shading and the reflectance map. *Proceedings of the IEEE*, 69(1), 14–47.
10. **Huggel, C., Kääb, A., Haeberli, W., Teysseire, P., & Paul, F. (2002).** Remote sensing based assessment of hazards from glacier lake outbursts: a case study in the Swiss Alps. *Canadian Geotechnical Journal*, 39(2), 316–330.
11. **McFeeters, S. K. (1996).** The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. *International Journal of Remote Sensing*, 17(7), 1425–1432.
12. **O'Callaghan, J. F., & Mark, D. M. (1984).** The extraction of drainage networks from digital elevation data. *Computer Vision, Graphics, and Image Processing*, 28(3), 323–344.
13. **Rafiq, M., Romshoo, S. A., Mishra, A. K., & Jalal, F. (2019).** Modelling Chorabari Lake outburst flood, Kedarnath, India. *Geomatics, Natural Hazards and Risk*, 10(1), 735–752.
14. **Rennó, C. D., Nobre, A. D., Cuartas, L. A., Soares, J. V., Hodnett, M. G., Tomasella, J., & Waterloo, M. J. (2008).** HAND, a new terrain descriptor using SRTM-DEM: Mapping terra-firme rainforest environments in Amazonia. *Remote Sensing of Environment*, 112(9), 3469–3481.
15. **Ronneberger, O., Fischer, P., & Brox, T. (2015).** U-Net: Convolutional networks for biomedical image segmentation. *MICCAI 2015*, 234–241.
16. **Sattar, A., Goswami, A., Kulkarni, A. V., Emmer, A., Haritashya, U. K., Allen, S., Frey, H., & Huggel, C. (2021).** Future glacial lake outburst flood (GLOF) hazard of the South Lhonak Lake, Sikkim Himalaya. *Geomorphology*, 388, 107783.
17. **Xu, H. (2006).** Modification of normalised difference water index (MNDWI) to enhance open water features in remotely sensed imagery. *International Journal of Remote Sensing*, 27(14), 3025–3033.
"""


def main() -> None:
    parts = [HEADER]
    for md_file in sorted(TAB_DIR.glob("table*.md")):
        parts.append("\n---\n\n" + md_file.read_text(encoding="utf-8"))
    parts.append(FOOTER)
    text = "\n".join(parts)
    out = RESEARCH_DIR / "GEMINI_REPORT_HANDOVER.md"
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out} ({len(text):,} characters, {len(text.splitlines()):,} lines)")


if __name__ == "__main__":
    main()
