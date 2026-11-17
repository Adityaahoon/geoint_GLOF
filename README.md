# GlacioGuard AI
### Historical-to-Present Geospatial Intelligence, Deep Learning and GLOF Susceptibility Assessment Platform for the Kedarnath Region, Uttarakhand, India (2000–2026)

**GlacioGuard AI** is a full-stack scientific geospatial intelligence platform built for multi-decadal environmental monitoring (2000–2026 YTD), glacial lake detection, 2013 Kedarnath compound disaster impact analysis, GLOF susceptibility screening, DEM hydrological modelling, HEC-RAS 2D hydraulic scenario integration, and OpenStreetMap downstream exposure assessment across the **Kedarnath–Chorabari Glacier–Gandhi Sarovar–Mandakini River Basin**.

---

## Architecture & Technology Stack

- **Frontend (`frontend/`):** React 18, TypeScript, Vite, Tailwind CSS, React-Leaflet (Leaflet 1.9), Recharts, Lucide React icons.
- **Backend (`backend/`):** Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, GeoAlchemy2.
- **Geospatial & Remote Sensing:** Google Earth Engine Python API (`earthengine-api`), Microsoft Planetary Computer & AWS Earth Search STAC (`pystac-client`, `planetary-computer`), Rasterio / GDAL, GeoPandas, Shapely 2, PyProj, Xarray / rioxarray, NumPy / SciPy.
- **Deep Learning & Machine Learning:** PyTorch (`U-Net` & `DeepLabV3+` 6-band semantic segmentation), Albumentations, OpenCV, Scikit-learn (`RandomForest`, `MLP`), XGBoost.
- **Database (`db/`):** PostgreSQL 16 + PostGIS 3.4 (production via `docker-compose.yml`) with automatic fallback to local SQLite + GeoJSON spatial serialization for zero-config local execution.

---

## Quick Start (Local Execution)

### 1. Backend Setup & Real Data Bootstrap
```bash
# 1. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. (Optional) Copy .env.example to .env and configure Google Earth Engine or PostGIS
cp .env.example .env

# 3. Bootstrap real Copernicus GLO-30 DEM, D8 hydrology, OpenStreetMap infrastructure,
#    NASA POWER rainfall (2000-2025 + June 2013 daily), and multi-year Landsat/Sentinel-2 composites:
python backend/scripts/bootstrap_real_data.py --years 2000 2011 2012 2013 2015 2020 2024 2026 --max-scenes 2

# 4. Start the FastAPI server on http://127.0.0.1:8000 (API docs at http://127.0.0.1:8000/docs)
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** in your browser.

---

## Docker & PostGIS Deployment

```bash
docker compose up --build -d
```
- **PostgreSQL + PostGIS:** `localhost:5432` (initialized with `db/init.sql`)
- **FastAPI Backend:** `http://localhost:8000/api/health`
- **Web Interface:** `http://localhost:8080`

---

## Activating Optional External Integrations

1. **Google Earth Engine (`app/services/gee_service.py`):**
   - Register a Google Cloud project for Earth Engine, create a service account JSON key, and set `GG_GEE_PROJECT`, `GG_GEE_SERVICE_ACCOUNT`, and `GG_GEE_PRIVATE_KEY_FILE` in `.env` (or run `earthengine authenticate` and set `GG_GEE_PROJECT`).
   - Even without GEE credentials, the platform automatically retrieves the identical USGS Landsat Collection 2 Level-2, Sentinel-2 L2A, and Copernicus DEM GLO-30 datasets via public STAC Cloud-Optimised GeoTIFFs (`app/services/stac_service.py`).
2. **U-Net / DeepLabV3+ Supervised Training (`app/services/dl_service.py`):**
   - Generate $256\times 256$ 6-band image tiles and weak MNDWI pre-labels in **Model Lab** (`POST /api/models/prepare-tiles`), verify/correct masks in QGIS and save them into `data/training/lake_segmentation/verified_masks/`, then launch training via the UI or `python backend/scripts/train_unet.py`.
3. **HEC-RAS 2D Hydraulic Simulation (`app/services/flood_service.py`):**
   - Export a scenario package (`.zip`) from the **Flood Simulation** page, run unsteady 2D routing in HEC-RAS 6.x, and upload the output depth/velocity GeoTIFFs back into the scenario.

---

## Documentation Index
- [API Reference (`docs/API.md`)](docs/API.md)
- [Satellite & Geospatial Datasets (`docs/DATASETS.md`)](docs/DATASETS.md)
- [Research Methodology (`docs/METHODOLOGY.md`)](docs/METHODOLOGY.md)
- [Deep Learning & Model Evaluation (`docs/MODEL_EVALUATION.md`)](docs/MODEL_EVALUATION.md)

