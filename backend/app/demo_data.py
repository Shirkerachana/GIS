from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians
from typing import Any

from shapely.geometry import LineString, Point, Polygon, mapping


ORIGIN_LAT = 18.5204
ORIGIN_LON = 73.8567
KM_PER_DEG_LAT = 110.574
KM_PER_DEG_LON = 111.320 * cos(radians(ORIGIN_LAT))


@dataclass(frozen=True)
class Record:
    id: str
    properties: dict[str, Any]
    geometry: Any


def _point(lon: float, lat: float) -> Point:
    return Point(lon, lat)


def _line(coords: list[tuple[float, float]]) -> LineString:
    return LineString(coords)


def _polygon(coords: list[tuple[float, float]]) -> Polygon:
    return Polygon(coords)


STUDY_AREA = _polygon(
    [
        (73.735, 18.415),
        (73.995, 18.415),
        (73.995, 18.655),
        (73.735, 18.655),
        (73.735, 18.415),
    ]
)


LAYERS: dict[str, list[Record]] = {
    "hospitals": [
        Record("h1", {"name": "Sahyadri Hospital", "type": "multi_specialty", "address": "Deccan, Pune"}, _point(73.8385, 18.5167)),
        Record("h2", {"name": "Ruby Hall Clinic", "type": "multi_specialty", "address": "Sassoon Road, Pune"}, _point(73.8723, 18.5298)),
        Record("h3", {"name": "Jehangir Hospital", "type": "multi_specialty", "address": "Bund Garden, Pune"}, _point(73.8771, 18.5335)),
        Record("h4", {"name": "KEM Hospital", "type": "general", "address": "Rasta Peth, Pune"}, _point(73.8616, 18.5208)),
        Record("h5", {"name": "Aundh Chest Hospital", "type": "specialty", "address": "Aundh, Pune"}, _point(73.8036, 18.5602)),
    ],
    "roads": [
        Record("r1", {"name": "University Road", "road_type": "major"}, _line([(73.800, 18.540), (73.840, 18.530), (73.880, 18.525), (73.925, 18.520)])),
        Record("r2", {"name": "Nagar Road", "road_type": "major"}, _line([(73.850, 18.560), (73.875, 18.545), (73.905, 18.535), (73.940, 18.525)])),
        Record("r3", {"name": "Pune-Satara Highway", "road_type": "major"}, _line([(73.790, 18.475), (73.835, 18.480), (73.880, 18.490), (73.930, 18.500)])),
        Record("r4", {"name": "Local Connector", "road_type": "local"}, _line([(73.815, 18.505), (73.835, 18.515), (73.855, 18.525)])),
    ],
    "rivers": [
        Record("rv1", {"name": "Mutha River", "waterway_type": "river"}, _line([(73.805, 18.550), (73.830, 18.540), (73.860, 18.532), (73.890, 18.525), (73.925, 18.515)])),
        Record("rv2", {"name": "Mula River", "waterway_type": "river"}, _line([(73.770, 18.575), (73.805, 18.565), (73.840, 18.558), (73.875, 18.552)])),
    ],
    "buildings": [
        Record("b1", {"building_type": "commercial"}, _polygon([(73.850, 18.525), (73.852, 18.525), (73.852, 18.528), (73.850, 18.528), (73.850, 18.525)])),
        Record("b2", {"building_type": "residential"}, _polygon([(73.818, 18.540), (73.823, 18.540), (73.823, 18.545), (73.818, 18.545), (73.818, 18.540)])),
        Record("b3", {"building_type": "institutional"}, _polygon([(73.885, 18.515), (73.889, 18.515), (73.889, 18.519), (73.885, 18.519), (73.885, 18.515)])),
    ],
    "population": [
        Record("p1", {"population": 52000, "density": 14800, "name": "Dense Core"}, _polygon([(73.845, 18.515), (73.865, 18.515), (73.865, 18.535), (73.845, 18.535), (73.845, 18.515)])),
        Record("p2", {"population": 33000, "density": 9100, "name": "Mixed Urban Belt"}, _polygon([(73.805, 18.535), (73.830, 18.535), (73.830, 18.555), (73.805, 18.555), (73.805, 18.535)])),
        Record("p3", {"population": 21000, "density": 6200, "name": "Outer Residential Zone"}, _polygon([(73.875, 18.500), (73.900, 18.500), (73.900, 18.520), (73.875, 18.520), (73.875, 18.500)])),
    ],
    "administrative_boundaries": [
        Record("a1", {"name": "Pune Municipal Boundary", "level": "city"}, STUDY_AREA),
    ],
}


def layer_names() -> list[str]:
    return list(LAYERS.keys())


def to_feature(record: Record) -> dict[str, Any]:
    return {
        "type": "Feature",
        "id": record.id,
        "properties": record.properties,
        "geometry": mapping(record.geometry),
    }


def to_feature_collection(layer: str, records: list[Record] | None = None) -> dict[str, Any]:
    selected = records if records is not None else LAYERS[layer]
    return {
        "type": "FeatureCollection",
        "name": layer,
        "features": [to_feature(record) for record in selected],
    }

