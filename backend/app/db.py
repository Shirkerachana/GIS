from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.app.config import settings

ALLOWED_TABLES = {
    "hospitals",
    "roads",
    "rivers",
    "buildings",
    "population",
    "administrative_boundaries",
}


def build_engine(database_url: str | None = None) -> Engine | None:
    url = database_url or settings.database_url
    if not url:
        return None
    return create_engine(url, future=True, pool_pre_ping=True)


@dataclass
class PostGISRepository:
    engine: Engine

    def healthcheck(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def list_features(self, table: str) -> list[dict[str, Any]]:
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Unsupported table: {table}")
        query = text(f"SELECT id, ST_AsGeoJSON(geom) AS geom FROM {table}")
        with self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [dict(row) for row in rows]

