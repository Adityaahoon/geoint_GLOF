# GlacioGuard AI — Satellite & Geospatial Dataset Documentation

All datasets integrated into GlacioGuard AI carry explicit citations, native spatial/spectral resolutions, operational periods, and quality-control rules.

## 1. Optical & SAR Satellite Missions

| Mission | GEE Collection ID | Public STAC Collection | Native Resolution | Band Mapping (`blue, green, red, nir, swir1, swir2`) | Operational Window |
|---|---|---|---|---|---|
| **Landsat 5 TM** | `LANDSAT/LT05/C02/T1_L2` | `landsat-c2-l2` (Planetary Computer) | 30 m | `SR_B1, SR_B2, SR_B3, SR_B4, SR_B5, SR_B7` + `QA_PIXEL` | 1984-03 – 2012-05 (routine India acquisitions ended Nov 2011) |
| **Landsat 7 ETM+** | `LANDSAT/LE07/C02/T1_L2` | `landsat-c2-l2` (Planetary Computer) | 30 m | `SR_B1, SR_B2, SR_B3, SR_B4, SR_B5, SR_B7` + `QA_PIXEL` | 1999-04 – 2024-01 (**SLC-off** after 31 May 2003) |
| **Landsat 8 OLI** | `LANDSAT/LC08/C02/T1_L2` | `landsat-c2-l2` (Planetary Computer) | 30 m | `SR_B2, SR_B3, SR_B4, SR_B5, SR_B6, SR_B7` + `QA_PIXEL` | 2013-04 – present |
| **Landsat 9 OLI-2** | `LANDSAT/LC09/C02/T1_L2` | `landsat-c2-l2` (Planetary Computer) | 30 m | `SR_B2, SR_B3, SR_B4, SR_B5, SR_B6, SR_B7` + `QA_PIXEL` | 2021-10 – present |
| **Sentinel-2 MSI (L2A)** | `COPERNICUS/S2_SR_HARMONIZED` | `sentinel-2-l2a` (AWS Earth Search) | 10 m (VIS/NIR), 20 m (SWIR) | `B2, B3, B4, B8, B11, B12` + `SCL` | 2015-06 – present |
| **Sentinel-1 C-SAR (GRD)** | `COPERNICUS/S1_GRD` | `sentinel-1-rtc` (Planetary Computer) | 10 m | `VV, VH, angle` | 2014-10 – present |

### Mandatory Sensor Harmonisation & Quality Rules
1. **Separate Band Configurations:** Band indices differ between TM/ETM+ (`SR_B1..B5,B7`), OLI/OLI-2 (`SR_B2..B7`), and MSI (`B2,B3,B4,B8,B11,B12`). `app/services/sensors.py` defines each sensor explicitly before renaming to harmonised internal names.
2. **Radiometric Scaling:**
   - USGS Landsat Collection 2 Level-2 surface reflectance: $\rho = \text{DN} \times 2.75\times 10^{-5} - 0.2$.
   - Sentinel-2 L2A: $\rho = \text{DN} \times 10^{-4}$ (with the Processing Baseline 04.00 $-1000$ BOA offset handled via `COPERNICUS/S2_SR_HARMONIZED` in GEE and per-asset `raster:bands` scale/offset metadata in STAC).
3. **Landsat 7 ETM+ SLC-Off Gap Handling:** On 31 May 2003 the Scan Line Corrector failed, causing wedge-shaped data loss (~22% of each scene). Gap pixels are flagged in `QA_PIXEL` bit 0 (`fill`) and `QA_PIXEL == 0`. GlacioGuard AI masks all gap pixels as `NaN` (never zero reflectance), reports `valid_pixel_fraction` per composite, and attaches the `"landsat7_slc_off_gaps"` quality flag.
4. **Comparable Seasonal Windows:** To avoid conflating seasonal snow/monsoon fluctuations with long-term environmental change, annual composites use a consistent post-monsoon autumn window (**15 September – 15/20 November**), when cloud cover and seasonal snow are near their annual minimum. Year 2026 is flagged as `"year_to_date"`.

## 2. Digital Elevation Models
- **Copernicus DEM GLO-30 (Primary):** 1 arc-second (~30 m) Digital Surface Model derived from TanDEM-X InSAR acquisitions (2011–2015), vertical datum EGM2008. Warped by bilinear interpolation onto a fixed 30 m WGS 84 / UTM Zone 44N (`EPSG:32644`) grid.
  - *Citation:* European Space Agency (2024). Copernicus Global Digital Elevation Model GLO-30. https://doi.org/10.5270/ESA-c5d3d65.
- **USGS SRTM GL1 30 m (GEE Integration):** `USGS/SRTMGL1_003` (February 2000 C-band radar epoch).

## 3. Precipitation Datasets
- **CHIRPS Daily:** `UCSB-CHG/CHIRPS/DAILY` (0.05° quasi-global infrared + station blend, 1981–present; Funk et al., 2015) via Google Earth Engine.
- **GPM IMERG V07:** `NASA/GPM_L3/IMERG_V07` (0.1° half-hourly satellite microwave/IR precipitation; Huffman et al., 2023) via Google Earth Engine.
- **NASA POWER MERRA-2 (`PRECTOTCORR`):** Publicly accessible unauthenticated daily and monthly bias-corrected precipitation over Kedarnath (`30.7346°N, 79.0669°E`) from the NASA Langley Research Center POWER API.

## 4. Infrastructure & Settlement Data
- **OpenStreetMap (Overpass API):** Live extraction of mapped `place` nodes (towns, villages, hamlets), `building` footprints, `highway` segments, `bridge` structures, `hospital`/`clinic` facilities, `school` buildings, `aeroway=helipad` pads, and public/religious sites across `[78.92°E, 30.58°N, 79.14°E, 30.82°N]`. Attribution: *© OpenStreetMap contributors (ODbL)*.

