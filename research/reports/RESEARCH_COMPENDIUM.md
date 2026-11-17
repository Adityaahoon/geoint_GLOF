# GlacioGuard AI — Complete Research Results Compendium (2000–2026 YTD)
**Study Area:** Kedarnath–Chorabari Glacier–Gandhi Sarovar–Mandakini River Basin, Uttarakhand, India (`78.92°E–79.14°E, 30.58°N–30.82°N`, `EPSG:32644` UTM Zone 44N)  
**Generated:** 2026-11-17 04:44 UTC

---

## 1. Directory Structure of `/research`

### A. Spatial Maps & Satellite Figures (`research/figures/`)
1. `fig01_study_area_and_dem.png` — Copernicus GLO-30 shaded-relief elevation map, D8 Strahler drainage network (`51.9 km`), and reference settlements/glaciers.
2. `fig02_terrain_and_hydrology_6panel.png` — 6-panel DEM geomorphometric and Priority-Flood hydrological derivatives (`Elevation`, `Slope`, `Aspect`, `TRI Roughness`, `Log10 Flow Accumulation`, `HAND`).
3. `fig03_satellite_composites_timeline_2000_2026.png` — True-colour post-monsoon satellite composite gallery across `2000, 2011, 2012, 2013, 2015, 2020, 2024, 2026-YTD`.
4. `fig04_historical_change_maps_6pairs.png` — Multi-decadal transition maps across all 6 mandated comparison epochs (`2000→2012`, `2012→2013`, `2013→2015`, `2015→2020`, `2020→2024`, `2024→2026-YTD`).
5. `fig05_2013_kedarnath_disaster_impact.png` — Pre-disaster (`2011`) vs Post-disaster (`2013`) imagery, `ΔNDVI` riparian vegetation stripping map, and exposed debris/sediment transition along the Mandakini corridor.
6. `fig06_glacial_lake_inventory_and_chorabari.png` — Mapped high-altitude water bodies (`n = 33`), GLOF susceptibility categories, and the `23.7 km` D8 flow path from Chorabari Lake (Gandhi Sarovar).
7. `fig07_glacier_snow_ice_retreat_chorabari.png` — False-colour (`SWIR1-NIR-Red`) and `NDSI` snow/ice transition across the Chorabari Glacier sub-region (`2000 → 2024`).
8. `fig08_downstream_infrastructure_exposure_map.png` — OpenStreetMap infrastructure (`1,191` features) overlaid with the Chorabari → Mandakini potential exposure corridor (`236` potentially exposed features).

### B. Analytical Graphs & Plots (`research/graphs/`)
1. `graph01_environmental_indicators_2000_2026.png` — 2000–2026 time series of Surface Water Area (`ha`), Snow & Ice Cover Area (`ha`), Mean `NDVI`, and Exposed Bare Ground/Debris (`ha`).
2. `graph02_standard_epoch_changes_bar.png` — Epoch-by-epoch area gains and losses for vegetation and surface water.
3. `graph03_rainfall_climatology_and_june2013_anomaly.png` — 2000–2025 June precipitation climatology and daily June 2013 rainfall highlighting the 15–17 June extreme event.
4. `graph04_glof_susceptibility_ranking_and_uncertainty.png` — Top 15 glacial lakes ranked by multi-criteria GLOF screening index (`mcda_screening_v1`) with uncertainty bounds and factor breakdown for `#1 KED-GL-003 (Chorabari Lake, score = 0.805, Very High)`.
5. `graph05_chorabari_mandakini_flowpath_profile.png` — Longitudinal elevation profile from Chorabari Lake (`3,848 m`) through Kedarnath, Rambara, Gaurikund, and Sonprayag (`~1,630 m`).
6. `graph06_unet_vs_deeplabv3plus_training_and_metrics.png` — PyTorch `U-Net` vs `DeepLabV3+` training/validation loss curves, IoU/Dice progression, and held-out geographic test split metrics.
7. `graph07_infrastructure_exposure_breakdown.png` — Downstream OpenStreetMap infrastructure exposure counts by category.

### C. Research Tables (`research/tables/` — `.csv` and `.md`)
1. `table01_satellite_composites_coverage` — Scene counts, seasonal windows, valid fractions, and quality flags (`2000–2026 YTD`).
2. `table02_glacial_lake_inventory_and_observations` — Coordinates, elevations, areas (`ha`), and perimeters (`m`) of all `33` mapped water bodies.
3. `table03_annual_environmental_indicators_2000_2026` — All `192` indicator values across the 4 sub-regions.
4. `table04_historical_change_detection_pairs` — Gain, loss, stable, and net change statistics across comparison pairs.
5. `table05_2013_disaster_affected_locations` — `ΔNDVI` and `ΔNBR` statistics around Chorabari Lake, Chorabari Glacier, Kedarnath, Rambara, Gaurikund, and Sonprayag.
6. `table06_glof_susceptibility_assessments_full` — Full 9-factor susceptibility screening table with uncertainty ranges and missing-parameter flags for all `33` lakes.
7. `table07_terrain_and_watershed_statistics` — DEM elevation, slope, Strahler stream network, and sub-basin drainage areas.
8. `table08_downstream_infrastructure_exposure` — OpenStreetMap infrastructure totals vs corridor potential exposure (`148` buildings, `11.66 km` roads, `17` bridges).
9. `table09_precipitation_june2013_daily` — Daily precipitation series for June 2013.
10. `table10_deep_learning_model_evaluation` — `U-Net` and `DeepLabV3+` evaluation metrics (`IoU, Dice, Precision, Recall, F1, Accuracy`) and confusion matrices.

### D. Vector GIS Layers (`research/geojson/`) & Reports (`research/reports/`)
- `glacial_lakes_inventory.geojson`, `glacier_outlines.geojson`, `streams.geojson`, `watersheds.geojson`, `chorabari_flowpath.geojson`, `infrastructure.geojson`, `exposed_infrastructure_corridor.geojson`
- `GlacioGuard_AI_Kedarnath_GLOF_Research_Report.pdf`
