"""FastAPI application entrypoint for GlacioGuard AI."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .database import SessionLocal, init_db
from .models import StudyArea
from .services import gee_service
from .study_area import SUB_REGIONS, UTM_EPSG, region_geometry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
settings = get_settings()


def _seed_study_areas() -> None:
    db = SessionLocal()
    try:
        for key, info in SUB_REGIONS.items():
            sa = db.query(StudyArea).filter_by(key=key).first()
            if sa is None:
                db.add(StudyArea(
                    key=key,
                    name=info["name"],
                    description="Kedarnath–Chorabari–Mandakini research sub-region",
                    geometry=region_geometry(key),
                    utm_epsg=UTM_EPSG,
                ))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_dirs()
    init_db()
    _seed_study_areas()
    gee_service.initialize()
    yield


app = FastAPI(
    title="GlacioGuard AI — Kedarnath GLOF & Geospatial Intelligence API",
    version="1.0.0",
    description=(
        "Historical-to-Present Geospatial Intelligence, Deep Learning and GLOF Susceptibility "
        "Assessment Platform for the Kedarnath Region, Uttarakhand, India (2000–2026)."
    ),
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

