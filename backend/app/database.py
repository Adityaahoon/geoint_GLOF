"""Database engine/session setup.

PostgreSQL + PostGIS is the production target (see db/init.sql and docker-compose.yml).
For local development without PostGIS, SQLite is used and geometries are stored as
GeoJSON text through the `GeoJSONGeometry` type, so the ORM layer is identical.
"""
from __future__ import annotations

import json
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import Text, TypeDecorator, UserDefinedType

from .config import get_settings

settings = get_settings()
IS_POSTGRES = settings.database_url.startswith("postgresql")

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class _PGGeometry(UserDefinedType):
    cache_ok = True

    def __init__(self, geometry_type: str = "GEOMETRY", srid: int = 4326):
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw):
        return f"geometry({self.geometry_type},{self.srid})"

    def bind_expression(self, bindvalue):
        from sqlalchemy import func
        return func.ST_SetSRID(func.ST_GeomFromGeoJSON(bindvalue), self.srid)

    def column_expression(self, col):
        from sqlalchemy import func
        return func.ST_AsGeoJSON(col)


class GeoJSONGeometry(TypeDecorator):
    """Geometry column: PostGIS geometry on PostgreSQL, GeoJSON text elsewhere.

    Python side always deals with GeoJSON geometry dicts (EPSG:4326).
    """

    impl = Text
    cache_ok = True

    def __init__(self, geometry_type: str = "GEOMETRY", srid: int = 4326, **kw):
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__(**kw)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PGGeometry(self.geometry_type, self.srid))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value) if not isinstance(value, str) else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value) if isinstance(value, str) else value


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)
    if IS_POSTGRES:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=engine)

