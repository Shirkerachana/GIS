from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.geometry import Polygon, mapping

from backend.app.config import settings
from backend.app.demo_data import LAYERS, Record, STUDY_AREA, to_feature, to_feature_collection


SUPPORTED_LAYERS = [
    "hospitals",
    "roads",
    "rivers",
    "buildings",
    "population",
    "administrative_boundaries",
]


def _root_dir() -> Path:
    return Path(settings.processed_data_dir).resolve()


def _real_dir() -> Path:
    return _root_dir() / "real"


def _boundary_record() -> Record:
    boundary_path = settings.study_area_boundary_path
    if boundary_path and boundary_path.exists():
        payload = json.loads(boundary_path.read_text(encoding="utf-8"))
        features = payload.get("features", [])
        if features:
            feature = features[0]
            return Record(
                id=str(feature.get("id") or "study-area"),
                properties=dict(feature.get("properties") or {"name": settings.study_area_name, "level": "study_area"}),
                geometry=shape(feature["geometry"]),
            )
    min_lon, min_lat, max_lon, max_lat = settings.study_area_bbox_tuple
    polygon = Polygon(
        [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),
        ]
    )
    return Record(
        id="study-area",
        properties={"name": settings.study_area_name, "level": "study_area"},
        geometry=polygon,
    )


def _load_geojson_records(path: Path) -> list[Record]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: list[Record] = []
    for feature in payload.get("features", []):
        geometry = shape(feature["geometry"])
        records.append(
            Record(
                id=str(feature.get("id") or feature["properties"].get("osmid") or feature["properties"].get("name") or len(records)),
                properties=dict(feature.get("properties") or {}),
                geometry=geometry,
            )
        )
    return records


@dataclass
class BaseDataStore:
    mode: str

    def layer_names(self) -> list[str]:
        return list(SUPPORTED_LAYERS)

    def layer_records(self, layer: str) -> list[Record]:
        raise NotImplementedError

    def feature_collection(self, layer: str) -> dict[str, Any]:
        return to_feature_collection(layer, self.layer_records(layer))

    def layer_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "featureCount": len(self.layer_records(name)),
                "description": _layer_description(name),
            }
            for name in self.layer_names()
        ]

    def population_stats(self) -> dict[str, Any]:
        return {}

    @property
    def is_real(self) -> bool:
        return self.mode == "real"


@dataclass
class DemoDataStore(BaseDataStore):
    def __init__(self):
        super().__init__(mode="demo")

    def layer_records(self, layer: str) -> list[Record]:
        return list(LAYERS.get(layer, []))


@dataclass
class RealDataStore(BaseDataStore):
    root: Path
    layer_paths: dict[str, Path]
    raster_stats_path: Path

    def __init__(self, root: Path | None = None):
        root = root or _real_dir()
        layer_paths = {layer: root / f"{layer}.geojson" for layer in SUPPORTED_LAYERS}
        super().__init__(mode="real")
        self.root = root
        self.layer_paths = layer_paths
        self.raster_stats_path = root / "worldpop_stats.json"

    def layer_records(self, layer: str) -> list[Record]:
        path = self.layer_paths.get(layer)
        if path is None:
            if layer == "administrative_boundaries":
                return [_boundary_record()]
            return []
        return _load_geojson_records(path)

    def population_stats(self) -> dict[str, Any]:
        if self.raster_stats_path.exists():
            return json.loads(self.raster_stats_path.read_text(encoding="utf-8"))
        return {}

    def ready(self) -> bool:
        return all(path.exists() for path in self.layer_paths.values()) and self.raster_stats_path.exists()

    def layer_summaries(self) -> list[dict[str, Any]]:
        summaries = super().layer_summaries()
        if self.raster_stats_path.exists():
            stats = self.population_stats()
            for summary in summaries:
                if summary["name"] == "population":
                    summary["featureCount"] = int(stats.get("valid_cell_count", summary["featureCount"]))
                    summary["description"] = "WorldPop clipped raster cells for Pune"
                if summary["name"] == "administrative_boundaries":
                    summary["featureCount"] = 1
        return summaries


def load_data_store() -> BaseDataStore:
    if settings.data_mode == "real":
        store = RealDataStore()
        if store.ready():
            return store
    return DemoDataStore()


ACTIVE_DATA_STORE: BaseDataStore = load_data_store()


def set_active_data_store(store: BaseDataStore) -> None:
    global ACTIVE_DATA_STORE
    ACTIVE_DATA_STORE = store


def get_active_data_store() -> BaseDataStore:
    return ACTIVE_DATA_STORE


def _layer_description(name: str) -> str:
    descriptions = {
        "hospitals": "Hospital point locations",
        "roads": "Road centerlines",
        "rivers": "River and waterway centerlines",
        "buildings": "Building footprints",
        "population": "WorldPop raster-derived population cells",
        "administrative_boundaries": "Study-area boundary",
    }
    return descriptions.get(name, "Dataset")
