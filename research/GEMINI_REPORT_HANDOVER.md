# MASTER PROJECT HANDOVER FOR GEMINI — GLACIOGUARD AI (2000–2026)

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
- **Landsat 5 TM / 7 ETM+ (`LANDSAT/LT05/C02/T1_L2`, `LE07`):** Bands `SR_B1..SR_B5, SR_B7` scaled via $\rho = \text{DN} \times 2.75\times 10^{-5} - 0.2$; cloud/shadow/fill masked via `QA_PIXEL`. Post-May 2003 Landsat 7 SLC-off wedge gaps (`~22%` of scene) are masked as `NaN` (`fill` bit 0) and never treated as valid observations.
- **Landsat 8 OLI / 9 OLI-2 (`LC08`, `LC09`):** Bands `SR_B2..SR_B7` scaled via $\rho = \text{DN} \times 2.75\times 10^{-5} - 0.2$; cirrus (`bit 2`) + cloud/shadow masked.
- **Sentinel-2 MSI L2A (`COPERNICUS/S2_SR_HARMONIZED`):** Bands `B2, B3, B4, B8, B11, B12` scaled by $10^{-4}$ with Baseline `04.00` BOA offset harmonised; masked using Scene Classification Layer (`SCL` classes `0, 1, 3, 8, 9, 10`).
- **Spectral Indices:**
  - $\text{NDWI} = \frac{\rho_{\text{green}} - \rho_{\text{nir}}}{\rho_{\text{green}} + \rho_{\text{nir}}}$ (McFeeters, 1996)
  - $\text{MNDWI} = \frac{\rho_{\text{green}} - \rho_{\text{swir1}}}{\rho_{\text{green}} + \rho_{\text{swir1}}}$ (Xu, 2006)
  - $\text{NDVI} = \frac{\rho_{\text{nir}} - \rho_{\text{red}}}{\rho_{\text{nir}} + \rho_{\text{red}}}$ (Tucker, 1979)
  - $\text{NDSI} = \frac{\rho_{\text{green}} - \rho_{\text{swir1}}}{\rho_{\text{green}} + \rho_{\text{swir1}}}$ (Hall et al., 1995; snow/ice where $\text{NDSI} > 0.40, \rho_{\text{nir}} > 0.11, \rho_{\text{green}} > 0.10$)
  - $\text{NBR} = \frac{\rho_{\text{nir}} - \rho_{\text{swir2}}}{\rho_{\text{nir}} + \rho_{\text{swir2}}}$ (Key & Benson, 2006)
- **Topographically Conditioned Glacial Lake Detection:** Combines adaptive Otsu thresholding on `MNDWI` (`clipped to [0.12, 0.30]`), `NDWI > 0.08`, `green > 0.035`, `nir < 0.18`, `swir1 < 0.12`, DEM slope $\le 16^\circ$, DEM hillshade $\ge 105$ (suppressing deep mountain cast shadows), and elevation $\ge 2,800\text{ m}$.

### 3.3 DEM Terrain & Priority-Flood D8 Hydrological Conditioning
- **Source DEM:** Copernicus Global DEM GLO-30 (`30 m`, TanDEM-X InSAR epoch, EGM2008 orthometric height) warped to `EPSG:32644`.
- **Derivatives (`hydrology.py`):** Horn (1981) $3\times 3$ slope and aspect, standard hillshade (azimuth $315^\circ$, altitude $45^\circ$), Riley et al. (1999) Terrain Ruggedness Index (TRI), Barnes et al. (2014) Priority-Flood $+\varepsilon$ depression filling, O'Callaghan & Mark (1984) D8 flow direction & topological flow accumulation, Strahler stream ordering (threshold $\ge 1.0\text{ km}^2$, yielding `51.94 km` of mapped streams up to Strahler order `3`), watershed delineation (`4` basins), and Height Above Nearest Drainage (`HAND`, Rennó et al., 2008).

### 3.4 Deep Learning Semantic Segmentation (`U-Net` vs `DeepLabV3+`)
- **Input Tensor:** 6-band harmonised optical reflectance (`blue, green, red, nir, swir1, swir2`) sliced into $128\times 128$ patches (`65` verified water-containing multi-temporal tiles across 2000–2024).
- **Leakage-Free Partitioning:** Geographic longitudinal block split (`West 60% = 39 train tiles`, `Central 20% = 13 validation tiles`, `East 20% = 13 held-out test tiles`) stratified by foreground presence.
- **Architectures & Normalization:** 4-stage `UNet` (`32→64→128→256→512` channels) and `DeepLabV3Plus` (ASPP dilation rates `1, 6, 12, 18` + low-level skip decoder) using `GroupNorm` for batch-size-invariant evaluation stability.
- **Loss Function:** Class-imbalance-weighted $0.35 \times \text{BCEWithLogitsLoss}(w_{\text{pos}}=6.0) + 0.65 \times \text{SoftDiceLoss}$, trained for `32` epochs with AdamW ($\text{lr}=2\times 10^{-3}$).
- **Held-Out Geographic Test Split Results:**
  - **`U-Net` (Best Epoch 32):** `IoU = 0.6105`, `Dice / F1 = 0.7582`, `Precision = 0.8197`, `Recall = 0.7052`, `Pixel Accuracy = 0.9857` (`TN = 205,194, FP = 1,047, FN = 1,990, TP = 4,761`). Live sliding-window inference on the 2024 Sentinel-2 composite detected `25` lakes (`60.39 ha`).
  - **`DeepLabV3+` (Best Epoch 31):** `IoU = 0.4618`, `Dice / F1 = 0.6319`, `Precision = 0.6025`, `Recall = 0.6642`, `Pixel Accuracy = 0.9755` (`TN = 203,283, FP = 2,958, FN = 2,267, TP = 4,484`).

### 3.5 GLOF Multi-Criteria Susceptibility Screening (`mcda_screening_v1`)
Grounded in GAPHAZ (2017), Huggel et al. (2002), Worni et al. (2013), and Allen et al. (2019), evaluating 9 weighted criteria:
1. Steep ($30^\circ\text{–}60^\circ$) upslope avalanche source area fraction within `1 km` (`weight = 0.18`)
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


---

# Table 1: Multi-Temporal Satellite Composites Coverage (2000–2026 YTD)

*Exported from GlacioGuard AI database (`table01_satellite_composites_coverage.csv`)*

| Year | Mission | Region | Seasonal Window | Scene Count | Valid Coverage | Resolution (m) | Quality Flags | Sample Scene IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2000 | landsat5 | full_aoi | 2000-09-15 to 2000-11-20 | 1 | 31.3% | 30.0 | low_valid_coverage, single_scene_composite | LT05_L2SP_145039_20000923_02_T1 |
| 2011 | landsat5 | full_aoi | 2011-09-15 to 2011-11-20 | 4 | 58.8% | 30.0 | low_valid_coverage | LT05_L2SP_146039_20110929_02_T1, LT05_L2SP_145039_20111109_02_T1, LT05_L2SP_145039_20111024_02_T1 |
| 2012 | landsat7 | full_aoi | 2012-09-15 to 2012-11-20 | 4 | 69.1% | 30.0 | landsat7_slc_off_gaps, low_valid_coverage | LE07_L2SP_145039_20121119_02_T1, LE07_L2SP_146039_20121025_02_T1, LE07_L2SP_145039_20121103_02_T1 |
| 2013 | landsat8 | full_aoi | 2013-09-15 to 2013-11-20 | 4 | 75.4% | 30.0 | low_valid_coverage | LC08_L2SP_146039_20130918_02_T1, LC08_L2SP_145039_20131029_02_T1, LC08_L2SP_146039_20131020_02_T1 |
| 2015 | landsat8 | full_aoi | 2015-09-15 to 2015-11-20 | 4 | 79.1% | 30.0 | low_valid_coverage | LC08_L2SP_146039_20151010_02_T1, LC08_L2SP_146039_20151111_02_T1, LC08_L2SP_145039_20151120_02_T1 |
| 2020 | sentinel2 | full_aoi | 2020-09-15 to 2020-11-20 | 4 | 50.1% | 30.0 | low_valid_coverage | S2A_44RLV_20201028_1_L2A, S2B_44RLV_20201112_1_L2A, S2A_44RLV_20201018_1_L2A |
| 2024 | sentinel2 | full_aoi | 2024-09-15 to 2024-11-20 | 4 | 45.4% | 30.0 | low_valid_coverage | S2B_44RLV_20241101_0_L2A, S2A_44RLV_20241116_0_L2A, S2A_44RLV_20241027_0_L2A |
| 2026 | landsat8 | full_aoi | 2026-04-01 to 2026-11-15 | 4 | 79.5% | 30.0 | low_valid_coverage | LC08_L2SP_146039_20260415_02_T1, LC08_L2SP_146039_20260517_02_T1, LC08_L2SP_146039_20260922_02_T1 |

### Notes
- All composites are projected to WGS 84 / UTM Zone 44N (EPSG:32644).
- 2026 is treated as a year-to-date observation window.


---

# Table 2: Kedarnath Region High-Altitude & Glacial Lake Inventory (UTM Zone 44N)

*Exported from GlacioGuard AI database (`table02_glacial_lake_inventory_and_observations.csv`)*

| Lake Code | Name | Lat (°N) | Lon (°E) | Elevation (m) | Obs Count | First Year | First Area (ha) | Latest Year | Latest Area (ha) | Latest Perimeter (m) | Detection Method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KED-GL-001 | High-altitude water body KED-GL-001 | 30.7491 | 78.9766 | 4561.8 | 2 | 2000 | 2.070 | 2011 | 2.160 | 780.0 | mndwi_otsu |
| KED-GL-002 | High-altitude water body KED-GL-002 | 30.7392 | 78.9643 | 4796.8 | 1 | 2000 | 1.080 | 2000 | 1.080 | 660.0 | mndwi_otsu |
| KED-GL-003 | Chorabari Lake (Gandhi Sarovar) | 30.7472 | 79.0613 | 3848.1 | 1 | 2000 | 0.720 | 2000 | 0.720 | 360.0 | mndwi_otsu |
| KED-GL-004 | High-altitude water body KED-GL-004 | 30.7803 | 79.1082 | 5105.1 | 2 | 2011 | 3.330 | 2015 | 0.630 | 480.0 | mndwi_otsu |
| KED-GL-005 | High-altitude water body KED-GL-005 | 30.7550 | 79.0138 | 5005.1 | 1 | 2011 | 1.530 | 2011 | 1.530 | 600.0 | mndwi_otsu |
| KED-GL-006 | High-altitude water body KED-GL-006 | 30.7588 | 79.0107 | 4972.7 | 1 | 2011 | 1.080 | 2011 | 1.080 | 540.0 | mndwi_otsu |
| KED-GL-007 | High-altitude water body KED-GL-007 | 30.7816 | 79.1120 | 5144.7 | 2 | 2011 | 0.900 | 2012 | 12.510 | 2700.0 | mndwi_otsu |
| KED-GL-008 | High-altitude water body KED-GL-008 | 30.8013 | 79.1173 | 4816.6 | 3 | 2012 | 6.570 | 2024 | 1.620 | 900.0 | unet |
| KED-GL-009 | High-altitude water body KED-GL-009 | 30.8093 | 79.0005 | 4537.1 | 3 | 2012 | 5.670 | 2024 | 1.620 | 780.0 | unet |
| KED-GL-010 | High-altitude water body KED-GL-010 | 30.8060 | 79.0098 | 4733.2 | 3 | 2012 | 3.150 | 2024 | 0.720 | 480.0 | unet |
| KED-GL-011 | High-altitude water body KED-GL-011 | 30.7259 | 79.0364 | 4221.5 | 1 | 2012 | 1.980 | 2012 | 1.980 | 780.0 | mndwi_otsu |
| KED-GL-012 | High-altitude water body KED-GL-012 | 30.7982 | 79.0031 | 5120.9 | 1 | 2012 | 0.810 | 2012 | 0.810 | 420.0 | mndwi_otsu |
| KED-GL-013 | High-altitude water body KED-GL-013 | 30.8099 | 78.9945 | 4421.4 | 3 | 2012 | 0.630 | 2024 | 2.070 | 660.0 | unet |
| KED-GL-014 | High-altitude water body KED-GL-014 | 30.7728 | 78.9790 | 4991.7 | 1 | 2012 | 0.630 | 2012 | 0.630 | 420.0 | mndwi_otsu |
| KED-GL-015 | High-altitude water body KED-GL-015 | 30.7418 | 79.0094 | 4760.5 | 1 | 2013 | 1.980 | 2013 | 1.980 | 720.0 | mndwi_otsu |
| KED-GL-016 | High-altitude water body KED-GL-016 | 30.7463 | 78.9852 | 4739.0 | 1 | 2015 | 1.980 | 2015 | 1.980 | 720.0 | mndwi_otsu |
| KED-GL-017 | High-altitude water body KED-GL-017 | 30.8190 | 79.1238 | 4677.0 | 2 | 2020 | 1.980 | 2024 | 5.310 | 2760.0 | mndwi_otsu |
| KED-GL-018 | High-altitude water body KED-GL-018 | 30.8154 | 79.1207 | 4687.7 | 3 | 2020 | 0.810 | 2024 | 1.530 | 840.0 | unet |
| KED-GL-019 | High-altitude water body KED-GL-019 | 30.7434 | 78.9901 | 4756.8 | 3 | 2020 | 0.540 | 2024 | 1.170 | 720.0 | unet |
| KED-GL-020 | High-altitude water body KED-GL-020 | 30.8052 | 79.1353 | 4732.4 | 1 | 2024 | 7.740 | 2024 | 7.740 | 3240.0 | mndwi_otsu |
| KED-GL-021 | High-altitude water body KED-GL-021 | 30.8106 | 79.1335 | 4705.6 | 1 | 2024 | 4.860 | 2024 | 4.860 | 2340.0 | mndwi_otsu |
| KED-GL-022 | High-altitude water body KED-GL-022 | 30.8097 | 79.1274 | 4706.2 | 1 | 2024 | 0.540 | 2024 | 0.540 | 420.0 | mndwi_otsu |
| KED-GL-023 | High-altitude water body KED-GL-023 | 30.8097 | 79.1188 | 4710.0 | 2 | 2024 | 0.540 | 2024 | 5.580 | 2400.0 | unet |
| KED-GL-024 | High-altitude water body KED-GL-024 | 30.8056 | 79.1138 | 4732.2 | 2 | 2024 | 0.720 | 2024 | 4.140 | 2100.0 | unet |
| KED-GL-025 | High-altitude water body KED-GL-025 | 30.8062 | 79.1103 | 4750.0 | 3 | 2024 | 1.530 | 2024 | 1.350 | 780.0 | unet |
| KED-GL-026 | High-altitude water body KED-GL-026 | 30.8087 | 79.1386 | 4724.8 | 3 | 2024 | 1.710 | 2024 | 6.930 | 3000.0 | unet |
| KED-GL-027 | High-altitude water body KED-GL-027 | 30.8091 | 79.1147 | 4723.4 | 2 | 2024 | 0.630 | 2024 | 1.080 | 600.0 | unet |
| KED-GL-028 | High-altitude water body KED-GL-028 | 30.8068 | 79.1233 | 4699.6 | 2 | 2024 | 1.080 | 2024 | 0.810 | 480.0 | unet |
| KED-GL-029 | High-altitude water body KED-GL-029 | 30.8046 | 79.1258 | 4708.8 | 2 | 2024 | 0.990 | 2024 | 0.900 | 480.0 | unet |
| KED-GL-030 | High-altitude water body KED-GL-030 | 30.8042 | 79.1072 | 4771.6 | 2 | 2024 | 0.720 | 2024 | 0.720 | 480.0 | unet |
| KED-GL-031 | High-altitude water body KED-GL-031 | 30.7493 | 78.9845 | 4738.9 | 2 | 2024 | 0.630 | 2024 | 0.630 | 360.0 | unet |
| KED-GL-032 | High-altitude water body KED-GL-032 | 30.8172 | 78.9178 | 4694.1 | 2 | 2024 | 0.630 | 2024 | 1.350 | 960.0 | unet |
| KED-GL-033 | High-altitude water body KED-GL-033 | 30.7414 | 78.9865 | 4766.0 | 2 | 2024 | 0.630 | 2024 | 0.900 | 480.0 | unet |
| KED-GL-034 | High-altitude water body KED-GL-034 | 30.8076 | 79.1308 | 4715.7 | 1 | 2024 | 15.210 | 2024 | 15.210 | 6120.0 | unet |
| KED-GL-035 | High-altitude water body KED-GL-035 | 30.8149 | 79.1255 | 4695.2 | 1 | 2024 | 5.670 | 2024 | 5.670 | 2400.0 | unet |
| KED-GL-036 | High-altitude water body KED-GL-036 | 30.8005 | 78.9242 | 4762.7 | 1 | 2024 | 0.990 | 2024 | 0.990 | 660.0 | unet |
| KED-GL-037 | High-altitude water body KED-GL-037 | 30.8016 | 79.1396 | 4749.8 | 1 | 2024 | 0.720 | 2024 | 0.720 | 540.0 | unet |
| KED-GL-038 | High-altitude water body KED-GL-038 | 30.7578 | 78.9860 | 4722.7 | 2 | 2024 | 0.630 | 2024 | 0.540 | 360.0 | unet |

### Notes
- Candidate water pixels filtered by MNDWI, NDWI > 0.08, DEM slope <= 16°, hillshade >= 105, and elevation >= 2800 m.


---

# Table 3: Annual Environmental Indicator Time Series by Sub-Region (2000–2026 YTD)

*Exported from GlacioGuard AI database (`table03_annual_environmental_indicators_2000_2026.csv`)*

| Year | Sub-Region | Mission | Indicator | Value | Unit | Valid Pixel Fraction | Scenes | Quality Flags |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2000 | chorabari | landsat5 | exposed_ground_area_ha | 161.91 | ha | 13.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | chorabari | landsat5 | mndwi_mean | -0.326 | index | 13.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | chorabari | landsat5 | ndvi_mean | 0.3135 | index | 13.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | chorabari | landsat5 | snow_ice_area_ha | 8.46 | ha | 13.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | chorabari | landsat5 | vegetated_area_ha | 345.69 | ha | 13.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | chorabari | landsat5 | water_area_ha | 4.5 | ha | 13.3% | 1 | low_valid_coverage, single_scene_composite |
| 2011 | chorabari | landsat5 | exposed_ground_area_ha | 288.09 | ha | 24.4% | 4 | low_valid_coverage |
| 2011 | chorabari | landsat5 | mndwi_mean | -0.3165 | index | 24.4% | 4 | low_valid_coverage |
| 2011 | chorabari | landsat5 | ndvi_mean | 0.268 | index | 24.4% | 4 | low_valid_coverage |
| 2011 | chorabari | landsat5 | snow_ice_area_ha | 67.14 | ha | 24.4% | 4 | low_valid_coverage |
| 2011 | chorabari | landsat5 | vegetated_area_ha | 560.79 | ha | 24.4% | 4 | low_valid_coverage |
| 2011 | chorabari | landsat5 | water_area_ha | 45.0 | ha | 24.4% | 4 | low_valid_coverage |
| 2012 | chorabari | landsat7 | exposed_ground_area_ha | 319.23 | ha | 31.1% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | chorabari | landsat7 | mndwi_mean | -0.1426 | index | 31.1% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | chorabari | landsat7 | ndvi_mean | 0.1416 | index | 31.1% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | chorabari | landsat7 | snow_ice_area_ha | 288.81 | ha | 31.1% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | chorabari | landsat7 | vegetated_area_ha | 387.72 | ha | 31.1% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | chorabari | landsat7 | water_area_ha | 98.46 | ha | 31.1% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2013 | chorabari | landsat8 | exposed_ground_area_ha | 381.06 | ha | 50.5% | 4 | low_valid_coverage |
| 2013 | chorabari | landsat8 | mndwi_mean | -0.2797 | index | 50.5% | 4 | low_valid_coverage |
| 2013 | chorabari | landsat8 | ndvi_mean | 0.2572 | index | 50.5% | 4 | low_valid_coverage |
| 2013 | chorabari | landsat8 | snow_ice_area_ha | 315.36 | ha | 50.5% | 4 | low_valid_coverage |
| 2013 | chorabari | landsat8 | vegetated_area_ha | 1221.66 | ha | 50.5% | 4 | low_valid_coverage |
| 2013 | chorabari | landsat8 | water_area_ha | 34.38 | ha | 50.5% | 4 | low_valid_coverage |
| 2015 | chorabari | landsat8 | exposed_ground_area_ha | 336.15 | ha | 60.1% | 4 | low_valid_coverage |
| 2015 | chorabari | landsat8 | mndwi_mean | -0.0341 | index | 60.1% | 4 | low_valid_coverage |
| 2015 | chorabari | landsat8 | ndvi_mean | 0.1707 | index | 60.1% | 4 | low_valid_coverage |
| 2015 | chorabari | landsat8 | snow_ice_area_ha | 832.32 | ha | 60.1% | 4 | low_valid_coverage |
| 2015 | chorabari | landsat8 | vegetated_area_ha | 1055.34 | ha | 60.1% | 4 | low_valid_coverage |
| 2015 | chorabari | landsat8 | water_area_ha | 58.68 | ha | 60.1% | 4 | low_valid_coverage |
| 2020 | chorabari | sentinel2 | exposed_ground_area_ha | 684.09 | ha | 85.3% | 4 | low_valid_coverage |
| 2020 | chorabari | sentinel2 | mndwi_mean | -0.2295 | index | 85.3% | 4 | low_valid_coverage |
| 2020 | chorabari | sentinel2 | ndvi_mean | 0.3157 | index | 85.3% | 4 | low_valid_coverage |
| 2020 | chorabari | sentinel2 | snow_ice_area_ha | 855.18 | ha | 85.3% | 4 | low_valid_coverage |
| 2020 | chorabari | sentinel2 | vegetated_area_ha | 1556.1 | ha | 85.3% | 4 | low_valid_coverage |
| 2020 | chorabari | sentinel2 | water_area_ha | 372.06 | ha | 85.3% | 4 | low_valid_coverage |
| 2024 | chorabari | sentinel2 | exposed_ground_area_ha | 660.06 | ha | 74.4% | 4 | low_valid_coverage |
| 2024 | chorabari | sentinel2 | mndwi_mean | -0.3222 | index | 74.4% | 4 | low_valid_coverage |
| 2024 | chorabari | sentinel2 | ndvi_mean | 0.3547 | index | 74.4% | 4 | low_valid_coverage |
| 2024 | chorabari | sentinel2 | snow_ice_area_ha | 594.27 | ha | 74.4% | 4 | low_valid_coverage |
| 2024 | chorabari | sentinel2 | vegetated_area_ha | 1449.54 | ha | 74.4% | 4 | low_valid_coverage |
| 2024 | chorabari | sentinel2 | water_area_ha | 353.7 | ha | 74.4% | 4 | low_valid_coverage |
| 2026 | chorabari | landsat8 | exposed_ground_area_ha | 99.27 | ha | 50.7% | 4 | low_valid_coverage |
| 2026 | chorabari | landsat8 | mndwi_mean | 0.325 | index | 50.7% | 4 | low_valid_coverage |
| 2026 | chorabari | landsat8 | ndvi_mean | 0.1154 | index | 50.7% | 4 | low_valid_coverage |
| 2026 | chorabari | landsat8 | snow_ice_area_ha | 1330.47 | ha | 50.7% | 4 | low_valid_coverage |
| 2026 | chorabari | landsat8 | vegetated_area_ha | 636.48 | ha | 50.7% | 4 | low_valid_coverage |
| 2026 | chorabari | landsat8 | water_area_ha | 42.48 | ha | 50.7% | 4 | low_valid_coverage |
| 2000 | full_aoi | landsat5 | exposed_ground_area_ha | 329.67 | ha | 30.5% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | full_aoi | landsat5 | mndwi_mean | -0.5084 | index | 30.5% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | full_aoi | landsat5 | ndvi_mean | 0.7006 | index | 30.5% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | full_aoi | landsat5 | snow_ice_area_ha | 35.01 | ha | 30.5% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | full_aoi | landsat5 | vegetated_area_ha | 17093.34 | ha | 30.5% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | full_aoi | landsat5 | water_area_ha | 48.6 | ha | 30.5% | 1 | low_valid_coverage, single_scene_composite |
| 2011 | full_aoi | landsat5 | exposed_ground_area_ha | 1148.13 | ha | 57.0% | 4 | low_valid_coverage |
| 2011 | full_aoi | landsat5 | mndwi_mean | -0.496 | index | 57.0% | 4 | low_valid_coverage |
| 2011 | full_aoi | landsat5 | ndvi_mean | 0.6368 | index | 57.0% | 4 | low_valid_coverage |
| 2011 | full_aoi | landsat5 | snow_ice_area_ha | 396.54 | ha | 57.0% | 4 | low_valid_coverage |
| 2011 | full_aoi | landsat5 | vegetated_area_ha | 30736.53 | ha | 57.0% | 4 | low_valid_coverage |
| 2011 | full_aoi | landsat5 | water_area_ha | 212.13 | ha | 57.0% | 4 | low_valid_coverage |
| 2012 | full_aoi | landsat7 | exposed_ground_area_ha | 993.33 | ha | 67.0% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | full_aoi | landsat7 | mndwi_mean | -0.4272 | index | 67.0% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | full_aoi | landsat7 | ndvi_mean | 0.4942 | index | 67.0% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | full_aoi | landsat7 | snow_ice_area_ha | 2582.37 | ha | 67.0% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | full_aoi | landsat7 | vegetated_area_ha | 32440.41 | ha | 67.0% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | full_aoi | landsat7 | water_area_ha | 1082.61 | ha | 67.0% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2013 | full_aoi | landsat8 | exposed_ground_area_ha | 1300.95 | ha | 72.8% | 4 | low_valid_coverage |
| 2013 | full_aoi | landsat8 | mndwi_mean | -0.4757 | index | 72.8% | 4 | low_valid_coverage |
| 2013 | full_aoi | landsat8 | ndvi_mean | 0.6024 | index | 72.8% | 4 | low_valid_coverage |
| 2013 | full_aoi | landsat8 | snow_ice_area_ha | 2631.6 | ha | 72.8% | 4 | low_valid_coverage |
| 2013 | full_aoi | landsat8 | vegetated_area_ha | 37050.75 | ha | 72.8% | 4 | low_valid_coverage |
| 2013 | full_aoi | landsat8 | water_area_ha | 234.27 | ha | 72.8% | 4 | low_valid_coverage |
| 2015 | full_aoi | landsat8 | exposed_ground_area_ha | 1395.54 | ha | 76.6% | 4 | low_valid_coverage |
| 2015 | full_aoi | landsat8 | mndwi_mean | -0.4015 | index | 76.6% | 4 | low_valid_coverage |
| 2015 | full_aoi | landsat8 | ndvi_mean | 0.5245 | index | 76.6% | 4 | low_valid_coverage |
| 2015 | full_aoi | landsat8 | snow_ice_area_ha | 3962.97 | ha | 76.6% | 4 | low_valid_coverage |
| 2015 | full_aoi | landsat8 | vegetated_area_ha | 36601.02 | ha | 76.6% | 4 | low_valid_coverage |
| 2015 | full_aoi | landsat8 | water_area_ha | 523.71 | ha | 76.6% | 4 | low_valid_coverage |
| 2020 | full_aoi | sentinel2 | exposed_ground_area_ha | 4341.87 | ha | 48.1% | 4 | low_valid_coverage |
| 2020 | full_aoi | sentinel2 | mndwi_mean | -0.3674 | index | 48.1% | 4 | low_valid_coverage |
| 2020 | full_aoi | sentinel2 | ndvi_mean | 0.4075 | index | 48.1% | 4 | low_valid_coverage |
| 2020 | full_aoi | sentinel2 | snow_ice_area_ha | 5521.32 | ha | 48.1% | 4 | low_valid_coverage |
| 2020 | full_aoi | sentinel2 | vegetated_area_ha | 14751.63 | ha | 48.1% | 4 | low_valid_coverage |
| 2020 | full_aoi | sentinel2 | water_area_ha | 1996.29 | ha | 48.1% | 4 | low_valid_coverage |
| 2024 | full_aoi | sentinel2 | exposed_ground_area_ha | 3823.74 | ha | 43.8% | 4 | low_valid_coverage |
| 2024 | full_aoi | sentinel2 | mndwi_mean | -0.4336 | index | 43.8% | 4 | low_valid_coverage |
| 2024 | full_aoi | sentinel2 | ndvi_mean | 0.4512 | index | 43.8% | 4 | low_valid_coverage |
| 2024 | full_aoi | sentinel2 | snow_ice_area_ha | 4295.7 | ha | 43.8% | 4 | low_valid_coverage |
| 2024 | full_aoi | sentinel2 | vegetated_area_ha | 14361.84 | ha | 43.8% | 4 | low_valid_coverage |
| 2024 | full_aoi | sentinel2 | water_area_ha | 1930.32 | ha | 43.8% | 4 | low_valid_coverage |
| 2026 | full_aoi | landsat8 | exposed_ground_area_ha | 394.92 | ha | 76.8% | 4 | low_valid_coverage |
| 2026 | full_aoi | landsat8 | mndwi_mean | -0.2192 | index | 76.8% | 4 | low_valid_coverage |
| 2026 | full_aoi | landsat8 | ndvi_mean | 0.4957 | index | 76.8% | 4 | low_valid_coverage |
| 2026 | full_aoi | landsat8 | snow_ice_area_ha | 10956.24 | ha | 76.8% | 4 | low_valid_coverage |
| 2026 | full_aoi | landsat8 | vegetated_area_ha | 32636.34 | ha | 76.8% | 4 | low_valid_coverage |
| 2026 | full_aoi | landsat8 | water_area_ha | 124.29 | ha | 76.8% | 4 | low_valid_coverage |
| 2000 | kedarnath_valley | landsat5 | exposed_ground_area_ha | 33.84 | ha | 20.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | kedarnath_valley | landsat5 | mndwi_mean | -0.4124 | index | 20.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | kedarnath_valley | landsat5 | ndvi_mean | 0.4467 | index | 20.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | kedarnath_valley | landsat5 | snow_ice_area_ha | 0.0 | ha | 20.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | kedarnath_valley | landsat5 | vegetated_area_ha | 334.53 | ha | 20.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | kedarnath_valley | landsat5 | water_area_ha | 0.99 | ha | 20.3% | 1 | low_valid_coverage, single_scene_composite |
| 2011 | kedarnath_valley | landsat5 | exposed_ground_area_ha | 34.74 | ha | 37.7% | 4 | low_valid_coverage |
| 2011 | kedarnath_valley | landsat5 | mndwi_mean | -0.5065 | index | 37.7% | 4 | low_valid_coverage |
| 2011 | kedarnath_valley | landsat5 | ndvi_mean | 0.467 | index | 37.7% | 4 | low_valid_coverage |
| 2011 | kedarnath_valley | landsat5 | snow_ice_area_ha | 0.09 | ha | 37.7% | 4 | low_valid_coverage |
| 2011 | kedarnath_valley | landsat5 | vegetated_area_ha | 656.1 | ha | 37.7% | 4 | low_valid_coverage |
| 2011 | kedarnath_valley | landsat5 | water_area_ha | 0.18 | ha | 37.7% | 4 | low_valid_coverage |
| 2012 | kedarnath_valley | landsat7 | exposed_ground_area_ha | 81.36 | ha | 62.5% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | kedarnath_valley | landsat7 | mndwi_mean | -0.4852 | index | 62.5% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | kedarnath_valley | landsat7 | ndvi_mean | 0.2924 | index | 62.5% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | kedarnath_valley | landsat7 | snow_ice_area_ha | 38.7 | ha | 62.5% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | kedarnath_valley | landsat7 | vegetated_area_ha | 900.45 | ha | 62.5% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | kedarnath_valley | landsat7 | water_area_ha | 20.88 | ha | 62.5% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2013 | kedarnath_valley | landsat8 | exposed_ground_area_ha | 103.5 | ha | 88.7% | 4 | low_valid_coverage |
| 2013 | kedarnath_valley | landsat8 | mndwi_mean | -0.5515 | index | 88.7% | 4 | low_valid_coverage |
| 2013 | kedarnath_valley | landsat8 | ndvi_mean | 0.4029 | index | 88.7% | 4 | low_valid_coverage |
| 2013 | kedarnath_valley | landsat8 | snow_ice_area_ha | 0.63 | ha | 88.7% | 4 | low_valid_coverage |
| 2013 | kedarnath_valley | landsat8 | vegetated_area_ha | 1499.85 | ha | 88.7% | 4 | low_valid_coverage |
| 2013 | kedarnath_valley | landsat8 | water_area_ha | 0.36 | ha | 88.7% | 4 | low_valid_coverage |
| 2015 | kedarnath_valley | landsat8 | exposed_ground_area_ha | 126.9 | ha | 86.5% | 4 | low_valid_coverage |
| 2015 | kedarnath_valley | landsat8 | mndwi_mean | -0.4834 | index | 86.5% | 4 | low_valid_coverage |
| 2015 | kedarnath_valley | landsat8 | ndvi_mean | 0.3516 | index | 86.5% | 4 | low_valid_coverage |
| 2015 | kedarnath_valley | landsat8 | snow_ice_area_ha | 43.65 | ha | 86.5% | 4 | low_valid_coverage |
| 2015 | kedarnath_valley | landsat8 | vegetated_area_ha | 1351.62 | ha | 86.5% | 4 | low_valid_coverage |
| 2015 | kedarnath_valley | landsat8 | water_area_ha | 14.49 | ha | 86.5% | 4 | low_valid_coverage |
| 2020 | kedarnath_valley | sentinel2 | exposed_ground_area_ha | 51.57 | ha | 79.2% | 4 | low_valid_coverage |
| 2020 | kedarnath_valley | sentinel2 | mndwi_mean | -0.8694 | index | 79.2% | 4 | low_valid_coverage |
| 2020 | kedarnath_valley | sentinel2 | ndvi_mean | 0.7069 | index | 79.2% | 4 | low_valid_coverage |
| 2020 | kedarnath_valley | sentinel2 | snow_ice_area_ha | 13.68 | ha | 79.2% | 4 | low_valid_coverage |
| 2020 | kedarnath_valley | sentinel2 | vegetated_area_ha | 1389.87 | ha | 79.2% | 4 | low_valid_coverage |
| 2020 | kedarnath_valley | sentinel2 | water_area_ha | 31.41 | ha | 79.2% | 4 | low_valid_coverage |
| 2024 | kedarnath_valley | sentinel2 | exposed_ground_area_ha | 40.41 | ha | 65.7% | 4 | low_valid_coverage |
| 2024 | kedarnath_valley | sentinel2 | mndwi_mean | -0.9479 | index | 65.7% | 4 | low_valid_coverage |
| 2024 | kedarnath_valley | sentinel2 | ndvi_mean | 0.7948 | index | 65.7% | 4 | low_valid_coverage |
| 2024 | kedarnath_valley | sentinel2 | snow_ice_area_ha | 0.0 | ha | 65.7% | 4 | low_valid_coverage |
| 2024 | kedarnath_valley | sentinel2 | vegetated_area_ha | 1207.71 | ha | 65.7% | 4 | low_valid_coverage |
| 2024 | kedarnath_valley | sentinel2 | water_area_ha | 0.09 | ha | 65.7% | 4 | low_valid_coverage |
| 2026 | kedarnath_valley | landsat8 | exposed_ground_area_ha | 24.3 | ha | 76.0% | 4 | low_valid_coverage |
| 2026 | kedarnath_valley | landsat8 | mndwi_mean | 0.0021 | index | 76.0% | 4 | low_valid_coverage |
| 2026 | kedarnath_valley | landsat8 | ndvi_mean | 0.2489 | index | 76.0% | 4 | low_valid_coverage |
| 2026 | kedarnath_valley | landsat8 | snow_ice_area_ha | 584.82 | ha | 76.0% | 4 | low_valid_coverage |
| 2026 | kedarnath_valley | landsat8 | vegetated_area_ha | 795.96 | ha | 76.0% | 4 | low_valid_coverage |
| 2026 | kedarnath_valley | landsat8 | water_area_ha | 10.08 | ha | 76.0% | 4 | low_valid_coverage |
| 2000 | mandakini_corridor | landsat5 | exposed_ground_area_ha | 14.67 | ha | 39.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | mandakini_corridor | landsat5 | mndwi_mean | -0.4977 | index | 39.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | mandakini_corridor | landsat5 | ndvi_mean | 0.6908 | index | 39.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | mandakini_corridor | landsat5 | snow_ice_area_ha | 0.0 | ha | 39.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | mandakini_corridor | landsat5 | vegetated_area_ha | 5665.59 | ha | 39.3% | 1 | low_valid_coverage, single_scene_composite |
| 2000 | mandakini_corridor | landsat5 | water_area_ha | 1.08 | ha | 39.3% | 1 | low_valid_coverage, single_scene_composite |
| 2011 | mandakini_corridor | landsat5 | exposed_ground_area_ha | 20.34 | ha | 58.9% | 4 | low_valid_coverage |
| 2011 | mandakini_corridor | landsat5 | mndwi_mean | -0.5224 | index | 58.9% | 4 | low_valid_coverage |
| 2011 | mandakini_corridor | landsat5 | ndvi_mean | 0.7037 | index | 58.9% | 4 | low_valid_coverage |
| 2011 | mandakini_corridor | landsat5 | snow_ice_area_ha | 8.64 | ha | 58.9% | 4 | low_valid_coverage |
| 2011 | mandakini_corridor | landsat5 | vegetated_area_ha | 8477.28 | ha | 58.9% | 4 | low_valid_coverage |
| 2011 | mandakini_corridor | landsat5 | water_area_ha | 4.86 | ha | 58.9% | 4 | low_valid_coverage |
| 2012 | mandakini_corridor | landsat7 | exposed_ground_area_ha | 104.85 | ha | 83.9% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | mandakini_corridor | landsat7 | mndwi_mean | -0.5167 | index | 83.9% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | mandakini_corridor | landsat7 | ndvi_mean | 0.5245 | index | 83.9% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | mandakini_corridor | landsat7 | snow_ice_area_ha | 175.32 | ha | 83.9% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | mandakini_corridor | landsat7 | vegetated_area_ha | 11214.72 | ha | 83.9% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2012 | mandakini_corridor | landsat7 | water_area_ha | 61.56 | ha | 83.9% | 4 | landsat7_slc_off_gaps, low_valid_coverage |
| 2013 | mandakini_corridor | landsat8 | exposed_ground_area_ha | 201.87 | ha | 89.9% | 4 | low_valid_coverage |
| 2013 | mandakini_corridor | landsat8 | mndwi_mean | -0.5661 | index | 89.9% | 4 | low_valid_coverage |
| 2013 | mandakini_corridor | landsat8 | ndvi_mean | 0.6329 | index | 89.9% | 4 | low_valid_coverage |
| 2013 | mandakini_corridor | landsat8 | snow_ice_area_ha | 104.04 | ha | 89.9% | 4 | low_valid_coverage |
| 2013 | mandakini_corridor | landsat8 | vegetated_area_ha | 12381.66 | ha | 89.9% | 4 | low_valid_coverage |
| 2013 | mandakini_corridor | landsat8 | water_area_ha | 8.37 | ha | 89.9% | 4 | low_valid_coverage |
| 2015 | mandakini_corridor | landsat8 | exposed_ground_area_ha | 236.7 | ha | 89.7% | 4 | low_valid_coverage |
| 2015 | mandakini_corridor | landsat8 | mndwi_mean | -0.5272 | index | 89.7% | 4 | low_valid_coverage |
| 2015 | mandakini_corridor | landsat8 | ndvi_mean | 0.5753 | index | 89.7% | 4 | low_valid_coverage |
| 2015 | mandakini_corridor | landsat8 | snow_ice_area_ha | 154.98 | ha | 89.7% | 4 | low_valid_coverage |
| 2015 | mandakini_corridor | landsat8 | vegetated_area_ha | 12005.46 | ha | 89.7% | 4 | low_valid_coverage |
| 2015 | mandakini_corridor | landsat8 | water_area_ha | 25.65 | ha | 89.7% | 4 | low_valid_coverage |
| 2020 | mandakini_corridor | sentinel2 | exposed_ground_area_ha | 219.87 | ha | 40.2% | 4 | low_valid_coverage |
| 2020 | mandakini_corridor | sentinel2 | mndwi_mean | -0.8477 | index | 40.2% | 4 | low_valid_coverage |
| 2020 | mandakini_corridor | sentinel2 | ndvi_mean | 0.72 | index | 40.2% | 4 | low_valid_coverage |
| 2020 | mandakini_corridor | sentinel2 | snow_ice_area_ha | 170.01 | ha | 40.2% | 4 | low_valid_coverage |
| 2020 | mandakini_corridor | sentinel2 | vegetated_area_ha | 5146.47 | ha | 40.2% | 4 | low_valid_coverage |
| 2020 | mandakini_corridor | sentinel2 | water_area_ha | 128.07 | ha | 40.2% | 4 | low_valid_coverage |
| 2024 | mandakini_corridor | sentinel2 | exposed_ground_area_ha | 236.7 | ha | 40.1% | 4 | low_valid_coverage |
| 2024 | mandakini_corridor | sentinel2 | mndwi_mean | -0.8686 | index | 40.1% | 4 | low_valid_coverage |
| 2024 | mandakini_corridor | sentinel2 | ndvi_mean | 0.7642 | index | 40.1% | 4 | low_valid_coverage |
| 2024 | mandakini_corridor | sentinel2 | snow_ice_area_ha | 115.2 | ha | 40.1% | 4 | low_valid_coverage |
| 2024 | mandakini_corridor | sentinel2 | vegetated_area_ha | 5211.27 | ha | 40.1% | 4 | low_valid_coverage |
| 2024 | mandakini_corridor | sentinel2 | water_area_ha | 61.56 | ha | 40.1% | 4 | low_valid_coverage |
| 2026 | mandakini_corridor | landsat8 | exposed_ground_area_ha | 51.12 | ha | 87.0% | 4 | low_valid_coverage |
| 2026 | mandakini_corridor | landsat8 | mndwi_mean | -0.3608 | index | 87.0% | 4 | low_valid_coverage |
| 2026 | mandakini_corridor | landsat8 | ndvi_mean | 0.5674 | index | 87.0% | 4 | low_valid_coverage |
| 2026 | mandakini_corridor | landsat8 | snow_ice_area_ha | 1837.8 | ha | 87.0% | 4 | low_valid_coverage |
| 2026 | mandakini_corridor | landsat8 | vegetated_area_ha | 10585.08 | ha | 87.0% | 4 | low_valid_coverage |
| 2026 | mandakini_corridor | landsat8 | water_area_ha | 35.82 | ha | 87.0% | 4 | low_valid_coverage |


---

# Table 4: Multi-Temporal Environmental Change Detection Statistics (2000–2026 YTD)

*Exported from GlacioGuard AI database (`table04_historical_change_detection_pairs.csv`)*

| Epoch Pair | Indicator | Region | Sensor A | Sensor B | Area A (ha) | Area B (ha) | Stable (ha) | Gain (ha) | Loss (ha) | Net Change (ha) | Mean ΔIndex | Joint Valid % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2000 → 2012 | exposed_ground | full_aoi | landsat5 | landsat7 | 171.45 | 239.31 | 155.79 | 83.52 | 15.66 | 67.86 | -0.1283 | 29.9% |
| 2000 → 2012 | snow_ice | full_aoi | landsat5 | landsat7 | 12.87 | 74.97 | 9.09 | 65.88 | 3.78 | 62.1 | -0.0121 | 29.9% |
| 2000 → 2012 | vegetation | full_aoi | landsat5 | landsat7 | 17096.58 | 16741.35 | 16739.55 | 1.8 | 357.03 | -355.23 | -0.0943 | 29.9% |
| 2000 → 2012 | water | full_aoi | landsat5 | landsat7 | 19.71 | 103.05 | 7.02 | 96.03 | 12.69 | 83.34 | -0.0121 | 29.9% |
| 2000 → 2024 | snow_ice | chorabari | landsat5 | sentinel2 | 7.11 | 6.39 | 6.3 | 0.09 | 0.81 | -0.72 | -0.5104 | 10.9% |
| 2011 → 2013 | exposed_ground | mandakini_corridor | landsat5 | landsat8 | 21.96 | 139.68 | 18.0 | 121.68 | 3.96 | 117.72 | -0.0983 | 60.9% |
| 2011 → 2013 | vegetation | mandakini_corridor | landsat5 | landsat8 | 8786.88 | 8610.57 | 8595.72 | 14.85 | 191.16 | -176.31 | 0.0098 | 60.9% |
| 2011 → 2013 | water | mandakini_corridor | landsat5 | landsat8 | 4.77 | 0.0 | 0.0 | 0.0 | 4.77 | -4.77 | -0.0529 | 60.9% |
| 2012 → 2013 | exposed_ground | full_aoi | landsat7 | landsat8 | 798.39 | 685.89 | 418.23 | 267.66 | 380.16 | -112.5 | 0.0579 | 63.3% |
| 2012 → 2013 | snow_ice | full_aoi | landsat7 | landsat8 | 981.0 | 846.36 | 750.69 | 95.67 | 230.31 | -134.64 | -0.0472 | 63.2% |
| 2012 → 2013 | vegetation | full_aoi | landsat7 | landsat8 | 32837.49 | 34687.53 | 32518.71 | 2168.82 | 318.78 | 1850.04 | 0.1328 | 63.2% |
| 2012 → 2013 | water | full_aoi | landsat7 | landsat8 | 513.0 | 138.33 | 122.31 | 16.02 | 390.69 | -374.67 | -0.0472 | 63.2% |
| 2013 → 2015 | exposed_ground | full_aoi | landsat8 | landsat8 | 1073.52 | 973.17 | 723.51 | 249.66 | 350.01 | -100.35 | -0.0344 | 71.3% |
| 2013 → 2015 | snow_ice | full_aoi | landsat8 | landsat8 | 2015.55 | 2352.15 | 1827.0 | 525.15 | 188.55 | 336.6 | 0.0357 | 71.3% |
| 2013 → 2015 | vegetation | full_aoi | landsat8 | landsat8 | 37302.03 | 36426.06 | 36145.98 | 280.08 | 1156.05 | -875.97 | -0.0578 | 71.2% |
| 2013 → 2015 | water | full_aoi | landsat8 | landsat8 | 219.06 | 318.15 | 118.71 | 199.44 | 100.35 | 99.09 | 0.0357 | 71.3% |
| 2015 → 2020 | exposed_ground | full_aoi | landsat8 | sentinel2 | 1390.86 | 1206.45 | 493.11 | 713.34 | 897.75 | -184.41 | -0.0564 | 30.3% |
| 2015 → 2020 | snow_ice | full_aoi | landsat8 | sentinel2 | 3586.77 | 2623.5 | 2284.65 | 338.85 | 1302.12 | -963.27 | -0.3821 | 30.3% |
| 2015 → 2020 | vegetation | full_aoi | landsat8 | sentinel2 | 10209.24 | 12651.84 | 9849.96 | 2801.88 | 359.28 | 2442.6 | 0.2929 | 30.1% |
| 2015 → 2020 | water | full_aoi | landsat8 | sentinel2 | 654.48 | 618.66 | 206.64 | 412.02 | 447.84 | -35.82 | -0.3821 | 30.3% |
| 2020 → 2024 | exposed_ground | full_aoi | sentinel2 | sentinel2 | 4508.82 | 3924.81 | 3143.61 | 781.2 | 1365.21 | -584.01 | -0.0298 | 41.4% |
| 2020 → 2024 | snow_ice | full_aoi | sentinel2 | sentinel2 | 3866.13 | 4385.43 | 3293.73 | 1091.7 | 572.4 | 519.3 | 0.0068 | 41.5% |
| 2020 → 2024 | vegetation | full_aoi | sentinel2 | sentinel2 | 12627.54 | 13042.62 | 12294.09 | 748.53 | 333.45 | 415.08 | 0.027 | 41.2% |
| 2020 → 2024 | water | full_aoi | sentinel2 | sentinel2 | 1893.15 | 2034.63 | 1008.27 | 1026.36 | 884.88 | 141.48 | 0.0068 | 41.5% |
| 2024 → 2026 | exposed_ground | full_aoi | sentinel2 | landsat8 | 1897.47 | 376.56 | 219.51 | 157.05 | 1677.96 | -1520.91 | 0.4342 | 28.7% |
| 2024 → 2026 | snow_ice | full_aoi | sentinel2 | landsat8 | 2324.79 | 8869.86 | 2315.34 | 6554.52 | 9.45 | 6545.07 | 0.7559 | 28.7% |
| 2024 → 2026 | vegetation | full_aoi | sentinel2 | landsat8 | 11136.24 | 6830.28 | 6655.41 | 174.87 | 4480.83 | -4305.96 | -0.3247 | 28.6% |
| 2024 → 2026 | water | full_aoi | sentinel2 | landsat8 | 734.04 | 110.97 | 11.34 | 99.63 | 722.7 | -623.07 | 0.7559 | 28.7% |


---

# Table 5: June 2013 Kedarnath Compound Disaster Spectral Change around Key Locations (2011 vs 2013)

*Exported from GlacioGuard AI database (`table05_2013_disaster_affected_locations.csv`)*

| Location | Category | Lat (°N) | Lon (°E) | Mean ΔNDVI (240m) | Mean ΔNBR (240m) | Observed Change Interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| Chorabari Lake (Gandhi Sarovar) | lake | 30.747 | 79.058 | 0.0976 | 0.0071 | Mean ΔNDVI = +0.098, ΔNBR = +0.007 within ~240 m radius (negative values indicate vegetation stripping / fresh sediment or debris deposition). |
| Kedarnath | settlement | 30.7346 | 79.0669 | -0.1785 | -0.1939 | Mean ΔNDVI = -0.179, ΔNBR = -0.194 within ~240 m radius (negative values indicate vegetation stripping / fresh sediment or debris deposition). |
| Rambara (pre-2013 location) | settlement | 30.708 | 79.049 | -0.0331 | -0.1465 | Mean ΔNDVI = -0.033, ΔNBR = -0.146 within ~240 m radius (negative values indicate vegetation stripping / fresh sediment or debris deposition). |
| Gaurikund | settlement | 30.653 | 79.026 | -0.0415 | -0.1172 | Mean ΔNDVI = -0.041, ΔNBR = -0.117 within ~240 m radius (negative values indicate vegetation stripping / fresh sediment or debris deposition). |
| Sonprayag | settlement | 30.633 | 78.999 | -0.0957 | -0.1686 | Mean ΔNDVI = -0.096, ΔNBR = -0.169 within ~240 m radius (negative values indicate vegetation stripping / fresh sediment or debris deposition). |

### Notes
- Cross-sensor comparison (Landsat 5 TM in 2011 vs Landsat 8 OLI in 2013): bandpass and native resolution differences have been harmonised to a common 30 m UTM grid, but small spectral index shifts (±0.02–0.04) may reflect sensor response.
- Joint valid (cloud- & gap-free in both years) coverage is 60.9% of the region; area changes apply strictly to this jointly observed footprint.
- The June 2013 Kedarnath disaster (16–17 June 2013) resulted from a combination of extreme, early-onset monsoon rainfall, rapid snowmelt, landslides and debris flows, and the breach/overflow of Chorabari Lake (Gandhi Sarovar). It must not be attributed to a single GLOF mechanism. This platform separates GLOF-related hazards, rainfall-triggered flash floods, landslides/debris flows and combined downstream exposure.
- Optical satellite change maps document where vegetation loss, channel widening and sediment/debris deposition occurred between acquisitions, but cannot by themselves isolate the exact physical trigger (GLOF wave vs rainfall-runoff flash flood vs local hillslope debris flow) at each pixel.


---

# Table 6: Multi-Criteria GLOF Susceptibility Screening Inventory (`mcda_screening_v1`)

*Exported from GlacioGuard AI database (`table06_glof_susceptibility_assessments_full.csv`)*

| Lake Code | Name | Elev (m) | Area (ha) | Expansion (%/yr) | Glacier Dist (m) | Upslope Steep Frac | P90 Slope (°) | Outlet Grad (°) | Screening Index | Category | Uncertainty Range | Missing Parameters |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| KED-GL-003 | Chorabari Lake (Gandhi Sarovar) | 3848.1 | 0.72 | - | 0.0 | 0.482 | 47.8 | 13.4 | 0.805 | Very High | [0.657, 0.825] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-007 | High-altitude water body KED-GL-007 | 5144.7 | 12.51 | 1290.0 | 1260.0 | 0.739 | 56.2 | 11.0 | 0.776 | Very High | [0.743, 0.783] | moraine_dam_condition |
| KED-GL-013 | High-altitude water body KED-GL-013 | 4421.4 | 1.71 | 14.286 | 3955.5 | 0.61 | 51.0 | 7.7 | 0.692 | High | [0.662, 0.702] | moraine_dam_condition |
| KED-GL-011 | High-altitude water body KED-GL-011 | 4221.5 | 1.98 | - | 930.0 | 0.343 | 37.1 | 16.7 | 0.655 | High | [0.539, 0.707] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-012 | High-altitude water body KED-GL-012 | 5120.9 | 0.81 | - | 3029.3 | 0.503 | 51.9 | 20.9 | 0.65 | High | [0.535, 0.703] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-014 | High-altitude water body KED-GL-014 | 4991.7 | 0.63 | - | 5280.0 | 0.717 | 49.0 | 18.2 | 0.616 | High | [0.507, 0.675] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-015 | High-altitude water body KED-GL-015 | 4760.5 | 1.98 | - | 2340.0 | 0.341 | 42.9 | 12.9 | 0.573 | High | [0.474, 0.642] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-002 | High-altitude water body KED-GL-002 | 4796.8 | 1.08 | - | 6660.6 | 0.525 | 38.3 | 10.4 | 0.559 | High | [0.462, 0.63] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-010 | High-altitude water body KED-GL-010 | 4733.2 | 0.81 | -6.19 | 2617.1 | 0.604 | 54.4 | 12.3 | 0.551 | High | [0.528, 0.568] | moraine_dam_condition |
| KED-GL-001 | High-altitude water body KED-GL-001 | 4561.8 | 2.16 | 0.395 | 5506.0 | 0.288 | 41.1 | 14.9 | 0.542 | Moderate | [0.52, 0.56] | moraine_dam_condition |
| KED-GL-029 | High-altitude water body KED-GL-029 | 4708.8 | 0.99 | - | 3005.1 | 0.51 | 41.8 | 0.9 | 0.533 | Moderate | [0.442, 0.61] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-009 | High-altitude water body KED-GL-009 | 4537.1 | 0.54 | -7.54 | 3542.0 | 0.602 | 52.6 | 9.6 | 0.531 | Moderate | [0.51, 0.55] | moraine_dam_condition |
| KED-GL-031 | High-altitude water body KED-GL-031 | 4738.9 | 0.63 | - | 4770.0 | 0.281 | 31.7 | 14.7 | 0.531 | Moderate | [0.441, 0.609] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-004 | High-altitude water body KED-GL-004 | 5105.1 | 0.63 | -20.27 | 1290.0 | 0.67 | 48.8 | 10.8 | 0.521 | Moderate | [0.5, 0.54] | moraine_dam_condition |
| KED-GL-016 | High-altitude water body KED-GL-016 | 4739.0 | 1.98 | - | 4680.9 | 0.258 | 32.7 | 7.8 | 0.499 | Moderate | [0.415, 0.583] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-008 | High-altitude water body KED-GL-008 | 4816.6 | 1.71 | -6.164 | 2050.8 | 0.652 | 52.5 | 6.0 | 0.489 | Moderate | [0.47, 0.51] | moraine_dam_condition |
| KED-GL-020 | High-altitude water body KED-GL-020 | 4732.4 | 7.74 | - | 3597.6 | 0.432 | 10.2 | 1.6 | 0.485 | Moderate | [0.404, 0.572] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-028 | High-altitude water body KED-GL-028 | 4699.6 | 1.08 | - | 2847.6 | 0.32 | 34.2 | 1.0 | 0.474 | Moderate | [0.395, 0.563] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-032 | High-altitude water body KED-GL-032 | 4694.1 | 0.63 | - | 11461.1 | 0.395 | 38.6 | 4.9 | 0.471 | Moderate | [0.393, 0.561] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-018 | High-altitude water body KED-GL-018 | 4687.7 | 1.35 | 16.667 | 3030.6 | 0.167 | 15.1 | 2.7 | 0.464 | Moderate | [0.446, 0.486] | moraine_dam_condition |
| KED-GL-024 | High-altitude water body KED-GL-024 | 4732.2 | 0.72 | - | 2187.5 | 0.375 | 27.2 | 1.9 | 0.464 | Moderate | [0.388, 0.556] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-017 | High-altitude water body KED-GL-017 | 4677.0 | 5.31 | 42.045 | 3406.0 | 0.042 | 15.1 | 2.9 | 0.451 | Moderate | [0.433, 0.473] | moraine_dam_condition |
| KED-GL-027 | High-altitude water body KED-GL-027 | 4723.4 | 0.63 | - | 2413.6 | 0.392 | 15.5 | 2.2 | 0.432 | Moderate | [0.362, 0.53] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-025 | High-altitude water body KED-GL-025 | 4750.0 | 1.53 | - | 1597.1 | 0.229 | 15.6 | 2.8 | 0.401 | Moderate | [0.338, 0.506] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-030 | High-altitude water body KED-GL-030 | 4771.6 | 0.72 | - | 1307.0 | 0.267 | 12.1 | 3.2 | 0.4 | Moderate | [0.337, 0.505] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-023 | High-altitude water body KED-GL-023 | 4710.0 | 0.54 | - | 2588.5 | 0.312 | 14.1 | 2.4 | 0.391 | Moderate | [0.33, 0.498] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-021 | High-altitude water body KED-GL-021 | 4705.6 | 4.86 | - | 3730.1 | 0.17 | 16.2 | 1.7 | 0.344 | Low | [0.293, 0.461] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-033 | High-altitude water body KED-GL-033 | 4766.0 | 0.63 | - | 4590.0 | 0.218 | 27.0 | 1.7 | 0.329 | Low | [0.281, 0.449] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-019 | High-altitude water body KED-GL-019 | 4756.8 | 0.54 | 0.0 | 4230.0 | 0.203 | 34.1 | 2.4 | 0.322 | Low | [0.311, 0.351] | moraine_dam_condition |
| KED-GL-005 | High-altitude water body KED-GL-005 | 5005.1 | 1.53 | - | 1968.6 | 0.173 | 16.6 | 3.1 | 0.316 | Low | [0.27, 0.438] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-026 | High-altitude water body KED-GL-026 | 4724.8 | 1.53 | - | 3948.2 | 0.233 | 13.2 | 1.8 | 0.315 | Low | [0.27, 0.438] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-006 | High-altitude water body KED-GL-006 | 4972.7 | 1.08 | - | 2250.0 | 0.059 | 19.3 | 2.7 | 0.306 | Low | [0.263, 0.431] | expansion_rate_pct_yr, moraine_dam_condition |
| KED-GL-022 | High-altitude water body KED-GL-022 | 4706.2 | 0.54 | - | 3415.4 | 0.248 | 11.1 | 1.9 | 0.296 | Low | [0.255, 0.423] | expansion_rate_pct_yr, moraine_dam_condition |

### Notes
- Preliminary multi-criteria screening index in [0, 1] following GAPHAZ (2017) / Huggel et al. (2002) / Allen et al. (2019). Scores are relative priority indices, NOT outburst probabilities.


---

# Table 7: Copernicus GLO-30 DEM Geomorphometry & D8 Watershed Characteristics

*Exported from GlacioGuard AI database (`table07_terrain_and_watershed_statistics.csv`)*

| Watershed / Basin | Drainage Area (km²) | Outlet Elevation (m) | AOI Min Elev (m) | AOI Max Elev (m) | AOI Mean Slope (°) | AOI P90 Slope (°) | Total Stream Length (km) | Max Strahler Order |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AOI main outlet | 280.36 | 1287.6 | 1284.7 | 6901.9 | 32.25 | 47.51 | 373.14 | 5 |
| Upstream of Kedarnath | 38.43 | 3515.8 | 1284.7 | 6901.9 | 32.25 | 47.51 | 373.14 | 5 |
| Upstream of Rambara (pre-2013 location) | 0.36 | 3712.5 | 1284.7 | 6901.9 | 32.25 | 47.51 | 373.14 | 5 |
| Upstream of Gaurikund | 86.6 | 1962.9 | 1284.7 | 6901.9 | 32.25 | 47.51 | 373.14 | 5 |
| Upstream of Sonprayag | 219.41 | 1695.0 | 1284.7 | 6901.9 | 32.25 | 47.51 | 373.14 | 5 |


---

# Table 8: OpenStreetMap Infrastructure Inventory & Downstream Potential Exposure Screening

*Exported from GlacioGuard AI database (`table08_downstream_infrastructure_exposure.csv`)*

| Infrastructure Category | Total Mapped in AOI | Potentially Exposed in Corridor | Exposed Share | Screening Methodology |
| --- | --- | --- | --- | --- |
| Bridge | 35 | 17 | 48.6% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Building | 905 | 148 | 16.4% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Helipad | 9 | 2 | 22.2% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Hospital | 1 | 0 | 0.0% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Power | 1 | 1 | 100.0% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Public | 15 | 4 | 26.7% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Road | 166 | 61 | 36.7% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |
| Settlement | 59 | 3 | 5.1% | Potential valley-corridor exposure (D8 buffer ≤ 250 m & HAND ≤ 25 m) |

### Notes
- Total mapped road network length in AOI: 241.36 km; potentially exposed corridor road length: 11.66 km.
- Potentially exposed settlements along corridor: Gaurikund, Mundhya Chak, Sonprayag.
- Strictly represents potential spatial exposure, NOT confirmed historical damage.


---

# Table 9: Daily Precipitation Series over Kedarnath during June 2013 (NASA POWER MERRA-2)

*Exported from GlacioGuard AI database (`table09_precipitation_june2013_daily.csv`)*

| Date | Dataset Source | Period | Precipitation (mm/day) |
| --- | --- | --- | --- |
| 2013-06-01 | NASA_POWER_MERRA2 | daily | 0.02 |
| 2013-06-02 | NASA_POWER_MERRA2 | daily | 0.0 |
| 2013-06-03 | NASA_POWER_MERRA2 | daily | 0.89 |
| 2013-06-04 | NASA_POWER_MERRA2 | daily | 0.04 |
| 2013-06-05 | NASA_POWER_MERRA2 | daily | 4.55 |
| 2013-06-06 | NASA_POWER_MERRA2 | daily | 0.3 |
| 2013-06-07 | NASA_POWER_MERRA2 | daily | 0.37 |
| 2013-06-08 | NASA_POWER_MERRA2 | daily | 4.84 |
| 2013-06-09 | NASA_POWER_MERRA2 | daily | 0.08 |
| 2013-06-10 | NASA_POWER_MERRA2 | daily | 13.96 |
| 2013-06-11 | NASA_POWER_MERRA2 | daily | 13.48 |
| 2013-06-12 | NASA_POWER_MERRA2 | daily | 2.84 |
| 2013-06-13 | NASA_POWER_MERRA2 | daily | 37.95 |
| 2013-06-14 | NASA_POWER_MERRA2 | daily | 20.27 |
| 2013-06-15 | NASA_POWER_MERRA2 | daily | 55.44 |
| 2013-06-16 | NASA_POWER_MERRA2 | daily | 116.18 |
| 2013-06-17 | NASA_POWER_MERRA2 | daily | 57.07 |
| 2013-06-18 | NASA_POWER_MERRA2 | daily | 3.43 |
| 2013-06-19 | NASA_POWER_MERRA2 | daily | 0.25 |
| 2013-06-20 | NASA_POWER_MERRA2 | daily | 0.0 |
| 2013-06-21 | NASA_POWER_MERRA2 | daily | 0.0 |
| 2013-06-22 | NASA_POWER_MERRA2 | daily | 18.34 |
| 2013-06-23 | NASA_POWER_MERRA2 | daily | 11.39 |
| 2013-06-24 | NASA_POWER_MERRA2 | daily | 35.33 |
| 2013-06-25 | NASA_POWER_MERRA2 | daily | 37.1 |
| 2013-06-26 | NASA_POWER_MERRA2 | daily | 4.67 |
| 2013-06-27 | NASA_POWER_MERRA2 | daily | 9.9 |
| 2013-06-28 | NASA_POWER_MERRA2 | daily | 6.01 |
| 2013-06-29 | NASA_POWER_MERRA2 | daily | 7.89 |
| 2013-06-30 | NASA_POWER_MERRA2 | daily | 0.35 |


---

# Table 10: Deep Learning Glacial Lake Segmentation Evaluation (`U-Net` vs `DeepLabV3+`)

*Exported from GlacioGuard AI database (`table10_deep_learning_model_evaluation.csv`)*

| Run ID | Model | Split | Tile Count | Best Epoch | IoU | Dice | Precision | Recall | F1-Score | Pixel Accuracy | TN Pixels | FP Pixels | FN Pixels | TP Pixels |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | UNET | val | 13 | 32 | 0.452 | 0.6226 | 0.6383 | 0.6077 | 0.6226 | 0.992 | 209877 | 798 | 909 | 1408 |
| 1 | UNET | test | 13 | 32 | 0.6105 | 0.7582 | 0.8197 | 0.7052 | 0.7582 | 0.9857 | 205194 | 1047 | 1990 | 4761 |
| 2 | DEEPLABV3PLUS | val | 13 | 31 | 0.2547 | 0.406 | 0.3453 | 0.4924 | 0.406 | 0.9843 | 208512 | 2163 | 1176 | 1141 |
| 2 | DEEPLABV3PLUS | test | 13 | 31 | 0.4618 | 0.6319 | 0.6025 | 0.6642 | 0.6319 | 0.9755 | 203283 | 2958 | 2267 | 4484 |

### Notes
- Dataset partitioned via Geographic Longitudinal Block Split (West 60% train / Central 20% val / East 20% test) to prevent spatial autocorrelation leakage.


---

# Table 11: Intra-2013 Pre-Flood, During-Flood, Monsoon High-Flow & Post-Flood Satellite Water Metrics

*Exported from GlacioGuard AI 2013 Flood Water-Level Analysis (`table11_2013_pre_during_post_flood_stages.csv`)*

| Flood Stage | Date Window | Scenes Used | Corridor Valid % | Observed Wet Area (ha) | Coverage-Normalized Wet Area (ha) | Mean Corridor Index | 90th-Pct Water Index | Key Scene Acquisitions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1. Pre-Flood (May 2013) | 2013-05-01 to 2013-05-31 | 5 | 34.6% | 7.3 | 21.1 | -0.3788 | -0.2264 | 2013-05-21 (LANDSAT7), 2013-05-29 (LANDSAT8), 2013-05-13 (LANDSAT8) |
| 2. During / Immediate Flood (June 2013) | 2013-06-05 to 2013-06-30 | 5 | 35.5% | 2.8 | 7.9 | -0.2837 | -0.1189 | 2013-06-30 (LANDSAT8), 2013-06-22 (LANDSAT7), 2013-06-30 (LANDSAT8) |
| 3. Peak Monsoon High-Flow (July–Aug 2013) | 2013-07-01 to 2013-08-31 | 5 | 33.5% | 76.3 | 228.0 | -0.1023 | +0.4550 | 2013-08-01 (LANDSAT8), 2013-08-25 (LANDSAT7), 2013-08-26 (LANDSAT8) |
| 4. Post-Flood Recession (Sept–Nov 2013) | 2013-09-15 to 2013-11-25 | 6 | 71.6% | 15.2 | 21.2 | -0.3496 | -0.1256 | 2013-09-18 (LANDSAT8), 2013-11-21 (LANDSAT8), 2013-09-18 (LANDSAT8) |

### Scientific Notes
- Pre-Flood (May 2013) captures pre-monsoon snowmelt conditions immediately prior to the June 2013 extreme rainfall.
- During/Immediate Flood (June 2013) combines acquisitions from 6–30 June 2013 (including 22 & 23 June 2013, 5–6 days after the 17 June Chorabari Lake breach).
- Coverage-normalized wet area scales observed valley-floor wet pixels (HAND <= 45 m) by the cloud-free valid fraction in that stage.


---

# Table 12: Cross-Sectional Water Surface Elevation (WSE), Flow Depth & Wetted Width across Pre-, During-, and Post-Flood 2013 Stages

*Exported from GlacioGuard AI 2013 Flood Water-Level Analysis (`table12_settlement_water_level_rise_2013.csv`)*

| Station / Settlement | Thalweg Bed (m) | Pre Q (m³/s) | Pre Depth (m) | Pre WSE (m) | Pre Width (m) | 16-Jun Q (m³/s) | 16-Jun Depth (m) | 16-Jun WSE (m) | 16-Jun Width (m) | 17-Jun GLOF Q (m³/s) | 17-Jun Depth (m) | 17-Jun WSE (m) | 17-Jun Width (m) | Post Q (m³/s) | Post Stage (m) | Post WSE (m) | Post Width (m) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Kedarnath Outwash Fan | 3531.6 | 25 | 1.5 | 3533.1 | 30 | 1100 | 6.8 | 3538.4 | 120 | 3500 | 12.5 | 3544.1 | 210 | 40 | 2.8 | 3534.4 | 30 |
| Rambara Narrow Gorge | 3094.8 | 30 | 1.8 | 3096.6 | 60 | 1350 | 9.5 | 3104.3 | 90 | 4200 | 17.5 | 3112.3 | 120 | 50 | 3.4 | 3098.2 | 60 |
| Gaurikund Gorge | 1974.7 | 35 | 2.0 | 1976.7 | 60 | 1500 | 9.0 | 1983.7 | 120 | 3900 | 15.8 | 1990.5 | 150 | 55 | 3.2 | 1977.9 | 60 |
| Sonprayag Confluence | 1700.4 | 55 | 2.2 | 1702.6 | 60 | 2100 | 8.2 | 1708.6 | 90 | 4800 | 14.2 | 1714.6 | 120 | 80 | 3.0 | 1703.4 | 60 |

### Scientific Notes
- Cross-sections extracted directly from the 30 m Copernicus GLO-30 DEM (UTM Zone 44N) across the Mandakini thalweg at each settlement.
- Peak discharge & stage values correspond to published hydrometeorological and paleohydraulic/high-water-mark reconstructions of the 16–17 June 2013 event (Dobhal et al., 2013; Das et al., 2015; Rafiq et al., 2019; Sattar et al., 2021).
- Post-Flood stage includes ~1.5–2.0 m of boulder/gravel aggradation deposited on the channel bed at Kedarnath and Sonprayag.


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
