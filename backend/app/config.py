"""Central configuration for GlacioGuard AI.

All secrets (Earth Engine service-account key, database password) are read from
environment variables / a .env file and are never sent to the frontend.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_DIR / ".env"), str(BACKEND_DIR / ".env")),
        env_prefix="GG_",
        extra="ignore",
    )

    app_name: str = "GlacioGuard AI"
    environment: str = "development"

    # Database. Production: postgresql+psycopg2://user:pass@host:5432/glacioguard (PostGIS).
    # Local fallback: SQLite (geometries stored as GeoJSON text).
    database_url: str = f"sqlite:///{PROJECT_DIR / 'data' / 'glacioguard.db'}"

    # Storage
    data_dir: Path = PROJECT_DIR / "data"

    # Google Earth Engine
    gee_project: str | None = None  # Cloud project registered for Earth Engine
    gee_service_account: str | None = None  # e.g. glacioguard@project.iam.gserviceaccount.com
    gee_private_key_file: str | None = None  # path to service-account JSON key (never commit)
    gee_drive_folder: str = "GlacioGuard_exports"

    # Open STAC fallbacks (no credentials needed)
    pc_stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    earth_search_url: str = "https://earth-search.aws.element84.com/v1"
    overpass_url: str = "https://overpass-api.de/api/interpreter"

    # Allowed browser origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Analysis defaults
    utm_epsg: int = 32644  # WGS 84 / UTM zone 44N – used for all area/distance computations

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def training_dir(self) -> Path:
        return self.data_dir / "training"

    @property
    def flood_dir(self) -> Path:
        return self.data_dir / "flood"

    @property
    def previews_dir(self) -> Path:
        return self.data_dir / "previews"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.raw_dir, self.processed_dir, self.uploads_dir,
                  self.models_dir, self.reports_dir, self.training_dir, self.flood_dir,
                  self.previews_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s

