from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import osmium
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.validation import make_valid
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config import settings


MAJOR_ROAD_TYPES = {"motorway", "trunk", "primary", "secondary", "tertiary", "motorway_link", "trunk_link", "primary_link"}


@dataclass
class ExtractedFeature:
    id: str
    properties: dict[str, Any]
    geometry: Any


class PuneOSMExtractor(osmium.SimpleHandler):
    def __init__(self, study_area: Polygon):
        super().__init__()
        self.study_area = study_area
        self.layers: dict[str, list[ExtractedFeature]] = {
            "hospitals": [],
            "roads": [],
            "rivers": [],
            "buildings": [],
        }

    def node(self, node: osmium.osm.Node) -> None:  # type: ignore[override]
        if not node.location.valid():
            return
        tags = dict(node.tags)
        if not _is_hospital(tags):
            return
        geom = Point(node.location.lon, node.location.lat)
        if not geom.intersects(self.study_area):
            return
        self.layers["hospitals"].append(
            ExtractedFeature(
                id=f"node-{node.id}",
                properties=_hospital_properties(tags, node.id),
                geometry=geom,
            )
        )

    def way(self, way: osmium.osm.Way) -> None:  # type: ignore[override]
        tags = dict(way.tags)
        coords = _way_coordinates(way)
        if len(coords) < 2:
            return

        is_closed = bool(way.is_closed())
        is_area = bool(way.is_area())

        if _is_hospital(tags) and (is_closed or is_area):
            polygon = _close_ring(coords)
            geom = Polygon(polygon)
            if geom.is_empty or not geom.intersects(self.study_area):
                return
            self.layers["hospitals"].append(
                ExtractedFeature(
                    id=f"way-{way.id}",
                    properties=_hospital_properties(tags, way.id),
                    geometry=geom.representative_point(),
                )
            )
            return

        if "highway" in tags:
            geom = LineString(coords)
            if geom.is_empty or not geom.intersects(self.study_area):
                return
            highway = tags.get("highway", "")
            self.layers["roads"].append(
                ExtractedFeature(
                    id=f"way-{way.id}",
                    properties={
                        "name": tags.get("name") or f"OSM road {way.id}",
                        "highway": highway,
                        "road_type": "major" if highway in MAJOR_ROAD_TYPES else "local",
                        "source": "OpenStreetMap",
                    },
                    geometry=geom,
                )
            )
            return

        if "waterway" in tags or tags.get("natural") == "water":
            geom = LineString(coords)
            if geom.is_empty or not geom.intersects(self.study_area):
                return
            self.layers["rivers"].append(
                ExtractedFeature(
                    id=f"way-{way.id}",
                    properties={
                        "name": tags.get("name") or f"OSM waterway {way.id}",
                        "waterway_type": tags.get("waterway") or tags.get("natural") or "waterway",
                        "source": "OpenStreetMap",
                    },
                    geometry=geom,
                )
            )
            return

        if "building" in tags and (is_closed or is_area):
            polygon = _close_ring(coords)
            geom = Polygon(polygon)
            geom = _valid_geom(geom)
            if geom.is_empty or not geom.intersects(self.study_area):
                return
            self.layers["buildings"].append(
                ExtractedFeature(
                    id=f"way-{way.id}",
                    properties={
                        "building_type": tags.get("building") or "yes",
                        "name": tags.get("name"),
                        "source": "OpenStreetMap",
                    },
                    geometry=geom,
                )
            )


def _is_hospital(tags: dict[str, str]) -> bool:
    return tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital"


def _hospital_properties(tags: dict[str, str], osm_id: int) -> dict[str, Any]:
    return {
        "name": tags.get("name") or f"Hospital {osm_id}",
        "type": tags.get("healthcare") or tags.get("amenity") or "hospital",
        "address": tags.get("addr:full") or tags.get("addr:street") or "",
        "source": "OpenStreetMap",
        "osmid": str(osm_id),
    }


def _way_coordinates(way: osmium.osm.Way) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for node in way.nodes:
        if node.location.valid():
            coords.append((node.location.lon, node.location.lat))
    return coords


def _is_closed(coords: list[tuple[float, float]]) -> bool:
    return len(coords) >= 3 and coords[0] == coords[-1]


def _close_ring(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    closed = list(coords)
    if closed[0] != closed[-1]:
        closed.append(closed[0])
    return closed


def _valid_geom(geom):
    try:
        return make_valid(geom)
    except Exception:
        return geom.buffer(0)


def _study_area_bbox() -> Polygon:
    min_lon, min_lat, max_lon, max_lat = settings.study_area_bbox_tuple
    return box(min_lon, min_lat, max_lon, max_lat)


def _write_geojson(path: Path, layer_name: str, features: list[ExtractedFeature]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "FeatureCollection",
        "name": layer_name,
        "features": [
            {
                "type": "Feature",
                "id": feature.id,
                "properties": feature.properties,
                "geometry": mapping(feature.geometry),
            }
            for feature in features
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _dedupe_features(features: list[ExtractedFeature]) -> list[ExtractedFeature]:
    seen: set[str] = set()
    deduped: list[ExtractedFeature] = []
    for feature in features:
        if feature.id in seen:
            continue
        seen.add(feature.id)
        deduped.append(feature)
    return deduped


def _import_postgis(database_url: str, output_dir: Path) -> None:
    schema_path = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        schema_sql = schema_path.read_text(encoding="utf-8")
        for statement in [chunk.strip() for chunk in schema_sql.split(";") if chunk.strip()]:
            connection.execute(text(statement))

        for layer_name, table_name in [("hospitals", "hospitals"), ("roads", "roads"), ("rivers", "rivers"), ("buildings", "buildings")]:
            features = json.loads((output_dir / f"{layer_name}.geojson").read_text(encoding="utf-8")).get("features", [])
            for feature in features:
                geometry = feature["geometry"]
                props = feature.get("properties") or {}
                if table_name == "hospitals":
                    sql = """
                        INSERT INTO hospitals (id, name, type, address, latitude, longitude, geom)
                        VALUES (:id, :name, :type, :address, :latitude, :longitude, ST_SetSRID(ST_MakeValid(ST_GeomFromText(:wkt)), 4326))
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            type = EXCLUDED.type,
                            address = EXCLUDED.address,
                            latitude = EXCLUDED.latitude,
                            longitude = EXCLUDED.longitude,
                            geom = EXCLUDED.geom
                    """
                    point = geometry
                    connection.execute(
                        text(sql),
                        {
                            "id": feature["id"],
                            "name": props.get("name"),
                            "type": props.get("type"),
                            "address": props.get("address"),
                            "latitude": point["coordinates"][1],
                            "longitude": point["coordinates"][0],
                            "wkt": Point(point["coordinates"]).wkt,
                        },
                    )
                elif table_name == "roads":
                    sql = """
                        INSERT INTO roads (id, name, road_type, geom)
                        VALUES (:id, :name, :road_type, ST_SetSRID(ST_MakeValid(ST_GeomFromText(:wkt)), 4326))
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            road_type = EXCLUDED.road_type,
                            geom = EXCLUDED.geom
                    """
                    connection.execute(
                        text(sql),
                        {
                            "id": feature["id"],
                            "name": props.get("name"),
                            "road_type": props.get("road_type"),
                            "wkt": LineString(geometry["coordinates"]).wkt,
                        },
                    )
                elif table_name == "rivers":
                    sql = """
                        INSERT INTO rivers (id, name, waterway_type, geom)
                        VALUES (:id, :name, :waterway_type, ST_SetSRID(ST_MakeValid(ST_GeomFromText(:wkt)), 4326))
                        ON CONFLICT (id) DO UPDATE SET
                            name = EXCLUDED.name,
                            waterway_type = EXCLUDED.waterway_type,
                            geom = EXCLUDED.geom
                    """
                    connection.execute(
                        text(sql),
                        {
                            "id": feature["id"],
                            "name": props.get("name"),
                            "waterway_type": props.get("waterway_type"),
                            "wkt": LineString(geometry["coordinates"]).wkt,
                        },
                    )
                elif table_name == "buildings":
                    sql = """
                        INSERT INTO buildings (id, building_type, geom)
                        VALUES (:id, :building_type, ST_SetSRID(ST_MakeValid(ST_GeomFromText(:wkt)), 4326))
                        ON CONFLICT (id) DO UPDATE SET
                            building_type = EXCLUDED.building_type,
                            geom = EXCLUDED.geom
                    """
                    connection.execute(
                        text(sql),
                        {
                            "id": feature["id"],
                            "building_type": props.get("building_type"),
                            "wkt": Polygon(geometry["coordinates"][0]).wkt,
                        },
                    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Pune OSM features and optionally import them into PostGIS.")
    parser.add_argument("--pbf", default=str(settings.osm_pbf_path), help="Path to the India OSM PBF file")
    parser.add_argument("--bbox", default=settings.study_area_bbox, help="Study-area bounding box minLon,minLat,maxLon,maxLat")
    parser.add_argument("--output-dir", default=str(settings.real_data_dir), help="Directory for the extracted analysis-ready layers")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""), help="Optional PostGIS URL for import")
    args = parser.parse_args()

    pbf_path = Path(args.pbf).expanduser().resolve()
    if not pbf_path.exists():
        raise SystemExit(f"OSM source file not found: {pbf_path}")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bbox_values = [float(part.strip()) for part in args.bbox.split(",")]
    if len(bbox_values) != 4:
        raise SystemExit("bbox must contain exactly four comma-separated numbers")
    study_area = box(*bbox_values)

    extractor = PuneOSMExtractor(study_area)
    filter_keys = ["amenity", "healthcare", "highway", "waterway", "building"]
    for key in filter_keys:
        key_filter = osmium.filter.KeyFilter(key)
        key_filter.enable_for(osmium.osm.osm_entity_bits.NODE | osmium.osm.osm_entity_bits.WAY)
        extractor.apply_file(str(pbf_path), locations=True, filters=[key_filter])

    boundary_feature = ExtractedFeature(
        id="study-area",
        properties={"name": settings.study_area_name, "level": "study_area", "source": "Configured Pune boundary"},
        geometry=study_area,
    )

    extractor.layers["hospitals"] = _dedupe_features(extractor.layers["hospitals"])

    _write_geojson(output_dir / "hospitals.geojson", "hospitals", extractor.layers["hospitals"])
    _write_geojson(output_dir / "roads.geojson", "roads", extractor.layers["roads"])
    _write_geojson(output_dir / "rivers.geojson", "rivers", extractor.layers["rivers"])
    _write_geojson(output_dir / "buildings.geojson", "buildings", extractor.layers["buildings"])
    _write_geojson(output_dir / "administrative_boundaries.geojson", "administrative_boundaries", [boundary_feature])

    manifest = {
        "source": str(pbf_path),
        "bbox": bbox_values,
        "study_area": settings.study_area_name,
        "counts": {layer: len(features) for layer, features in extractor.layers.items()},
        "output_dir": str(output_dir),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))

    database_url = args.database_url.strip()
    if database_url:
        _import_postgis(database_url, output_dir)
        print("PostGIS import completed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
