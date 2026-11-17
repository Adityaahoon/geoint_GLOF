# GlacioGuard AI — Scientific Research Methodology

## 1. Study Area & Projections
The primary study domain covers the **Kedarnath–Chorabari Glacier–Gandhi Sarovar–Mandakini River Basin** in Rudraprayag District, Uttarakhand, India (`78.92°E–79.14°E, 30.58°N–30.82°N`), spanning elevations from ~1,300 m near Sonprayag to >6,500 m along the Chorabari/Kedarnath peaks.
- All map interfaces exchange GeoJSON in `EPSG:4326` (WGS 84), while **all area, perimeter, slope, hydrological accumulation, and buffer distance computations are performed on a snapped metric grid in WGS 84 / UTM Zone 44N (`EPSG:32644`)**.

## 2. Scientific Context of the June 2013 Kedarnath Disaster
The 15–17 June 2013 catastrophe in the Mandakini valley was a **compound hydrometeorological and cryospheric disaster** (Dobhal et al., 2013; Allen et al., 2016; Rafiq et al., 2019). GlacioGuard AI explicitly separates:
1. **GLOF Hazard:** Moraine dam breach of Chorabari Lake (Gandhi Sarovar, ~3,960 m a.s.l.) on the morning of 17 June 2013 following rapid infilling by rainfall and snowmelt.
2. **Rainfall-Triggered Flash Floods:** Synoptic interaction between a mid-tropospheric western disturbance and the monsoon trough produced extreme multi-day rainfall (>300 mm over 15–17 June) across snow-covered slopes, causing severe flooding along both the Saraswati and Mandakini rivers prior to the Chorabari breach.
3. **Landslides & Debris Flows:** Widespread slope failures, moraine mobilization, and bank undercutting along the steep gorge between Kedarnath, Rambara, Gaurikund, and Sonprayag.
4. **Combined Downstream Exposure:** High concentration of pilgrimage settlements, roads, and bridges within the active valley floor.

*Satellite change maps (ΔNDVI, ΔNBR, ΔMNDWI) document the spatial footprint of vegetation stripping, channel widening, and debris deposition between pre- and post-event acquisitions, but cannot by themselves isolate the exact physical trigger at each individual pixel.*

## 3. Spectral Indices & Multi-Temporal Change Detection
On cloud-, shadow-, and saturation-masked surface reflectance ($\rho \in [0, 1]$):
- **NDWI** (McFeeters, 1996): $\frac{\rho_{\text{green}} - \rho_{\text{nir}}}{\rho_{\text{green}} + \rho_{\text{nir}}}$
- **MNDWI** (Xu, 2006): $\frac{\rho_{\text{green}} - \rho_{\text{swir1}}}{\rho_{\text{green}} + \rho_{\text{swir1}}}$
- **NDVI** (Tucker, 1979): $\frac{\rho_{\text{nir}} - \rho_{\text{red}}}{\rho_{\text{nir}} + \rho_{\text{red}}}$
- **NDSI** (Hall et al., 1995): $\frac{\rho_{\text{green}} - \rho_{\text{swir1}}}{\rho_{\text{green}} + \rho_{\text{swir1}}}$, with clean snow/ice delineated where $\text{NDSI} > 0.40$, $\rho_{\text{nir}} > 0.11$, and $\rho_{\text{green}} > 0.10$.
- **NBR** (Key & Benson, 2006): $\frac{\rho_{\text{nir}} - \rho_{\text{swir2}}}{\rho_{\text{nir}} + \rho_{\text{swir2}}}$.

To suppress dark topographic shadows on steep north-facing walls during glacial lake detection, candidate water pixels must also satisfy DEM slope $\le 22^\circ$, $\rho_{\text{nir}} < 0.22$, and elevation $\ge 2,800\text{ m}$.

## 4. DEM Conditioning & Hydrological Analysis (`app/services/hydrology.py`)
1. **Slope & Aspect:** Horn's (1981) $3\times 3$ weighted finite-difference operator on the 30 m UTM grid.
2. **Terrain Ruggedness Index (TRI):** Riley et al. (1999) root-mean-square elevation difference to the 8 neighbours.
3. **Hydrological Conditioning:** Priority-Flood depression filling with $\varepsilon$-gradient imposition across flats (Barnes, Lehman & Mulla, 2014) so every cell has a defined drainage path without flat-surface stalls.
4. **D8 Flow Direction & Accumulation:** O'Callaghan & Mark (1984) steepest-descent routing in topological elevation order.
5. **Drainage Network & Strahler Order:** Extracted at contributing area $\ge 1.0\text{ km}^2$ with topological Strahler ordering and upstream pour-point watershed delineation.
6. **Height Above Nearest Drainage (HAND):** Rennó et al. (2008) vertical elevation above the nearest D8 stream cell along the drainage path. *HAND is a relative terrain index only and is never presented as a hydraulic flood depth.*

## 5. Hydraulic Scenario Modelling & Downstream Exposure
- **No DEM-Invented Flood Depths:** Flood depth ($\text{m}$) and flow velocity ($\text{m s}^{-1}$) depend on unsteady mass and momentum conservation (`2D Shallow Water Equations`) and breach hydrograph shape. GlacioGuard AI never fabricates flood depths from a DEM.
- **HEC-RAS 2D Integration:** Users create hypothetical scenarios with a cited inflow hydrograph, export a ready-to-run HEC-RAS 2D package (`.zip` with UTM terrain GeoTIFF, 2D flow area GeoJSON, D8 thalweg, and inflow boundary CSV), and import HEC-RAS 2D output rasters (`depth`, `velocity`, `wse`, `duration`) for visualization and OpenStreetMap infrastructure overlay.

