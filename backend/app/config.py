from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "GeoAI Assistant API"
    api_prefix: str = "/api"
    database_url: str = os.getenv("DATABASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    use_demo_data: bool = os.getenv("USE_DEMO_DATA", "true").lower() in {"1", "true", "yes", "on"}
    data_mode: str = os.getenv("DATA_MODE", "demo").strip().lower()
    frontend_origin: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    log_level: str = os.getenv("LOG_LEVEL", "info")
    study_area_name: str = os.getenv("STUDY_AREA_NAME", "Pune, Maharashtra, India")
    processed_data_dir: str = os.getenv("PROCESSED_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data" / "processed"))
    osm_source_path: str = os.getenv("OSM_SOURCE_PATH", str(Path(__file__).resolve().parents[3] / "india-260817.osm.pbf"))
    worldpop_source_path: str = os.getenv("WORLDPOP_SOURCE_PATH", str(Path(__file__).resolve().parents[3] / "ind_pop_2025_CN_1km_R2025A_UA_v1.tif"))
    study_area_bbox: str = os.getenv("STUDY_AREA_BBOX", "73.735,18.415,73.995,18.655")
    study_area_boundary_geojson: str = os.getenv("STUDY_AREA_BOUNDARY_GEOJSON", "")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    @property
    def real_data_dir(self) -> Path:
        return Path(self.processed_data_dir).resolve() / "real"

    @property
    def osm_pbf_path(self) -> Path:
        return Path(self.osm_source_path).expanduser().resolve()

    @property
    def worldpop_tif_path(self) -> Path:
        return Path(self.worldpop_source_path).expanduser().resolve()

    @property
    def study_area_bbox_tuple(self) -> tuple[float, float, float, float]:
        values = [float(part.strip()) for part in self.study_area_bbox.split(",")]
        if len(values) != 4:
            raise ValueError("STUDY_AREA_BBOX must contain exactly four comma-separated numbers")
        return values[0], values[1], values[2], values[3]

    @property
    def study_area_boundary_path(self) -> Path | None:
        if not self.study_area_boundary_geojson.strip():
            return None
        return Path(self.study_area_boundary_geojson).expanduser().resolve()


settings = Settings()
