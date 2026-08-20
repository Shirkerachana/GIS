from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.demo_data import LAYERS


def _wkt(geometry) -> str:
    return geometry.wkt


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set. Set it first and rerun this script.")
        return 1

    schema_path = Path(__file__).resolve().parents[1] / "database" / "schema.sql"
    engine = create_engine(database_url, future=True)

    with engine.begin() as connection:
        schema_sql = schema_path.read_text(encoding="utf-8")
        for statement in [chunk.strip() for chunk in re.split(r";\s*\n", schema_sql) if chunk.strip()]:
            connection.execute(text(statement))

        for record in LAYERS["hospitals"]:
            connection.execute(
                text(
                    """
                    INSERT INTO hospitals (id, name, type, address, latitude, longitude, geom)
                    VALUES (:id, :name, :type, :address, :latitude, :longitude, ST_GeomFromText(:geom, 4326))
                    ON CONFLICT (id) DO UPDATE SET
                      name = EXCLUDED.name,
                      type = EXCLUDED.type,
                      address = EXCLUDED.address,
                      latitude = EXCLUDED.latitude,
                      longitude = EXCLUDED.longitude,
                      geom = EXCLUDED.geom
                    """
                ),
                {
                    "id": record.id,
                    "name": record.properties.get("name"),
                    "type": record.properties.get("type"),
                    "address": record.properties.get("address"),
                    "latitude": record.geometry.y,
                    "longitude": record.geometry.x,
                    "geom": _wkt(record.geometry),
                },
            )

        for table_name, column_name in [("roads", "road_type"), ("rivers", "waterway_type"), ("buildings", "building_type"), ("population", None), ("administrative_boundaries", "level")]:
            for record in LAYERS[table_name]:
                columns = ["id", "geom"]
                values = {"id": record.id, "geom": _wkt(record.geometry)}
                if table_name in {"roads", "rivers", "buildings"}:
                    columns = ["id", "name_or_type", "geom"]
                if table_name == "roads":
                    values["name_or_type"] = record.properties.get("road_type")
                    sql = """
                        INSERT INTO roads (id, name, road_type, geom)
                        VALUES (:id, :name, :name_or_type, ST_GeomFromText(:geom, 4326))
                        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, road_type = EXCLUDED.road_type, geom = EXCLUDED.geom
                    """
                    values["name"] = record.properties.get("name")
                elif table_name == "rivers":
                    values["name_or_type"] = record.properties.get("waterway_type")
                    sql = """
                        INSERT INTO rivers (id, name, waterway_type, geom)
                        VALUES (:id, :name, :name_or_type, ST_GeomFromText(:geom, 4326))
                        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, waterway_type = EXCLUDED.waterway_type, geom = EXCLUDED.geom
                    """
                    values["name"] = record.properties.get("name")
                elif table_name == "buildings":
                    sql = """
                        INSERT INTO buildings (id, building_type, geom)
                        VALUES (:id, :name_or_type, ST_GeomFromText(:geom, 4326))
                        ON CONFLICT (id) DO UPDATE SET building_type = EXCLUDED.building_type, geom = EXCLUDED.geom
                    """
                    values["name_or_type"] = record.properties.get("building_type")
                elif table_name == "population":
                    sql = """
                        INSERT INTO population (id, population, density, geom)
                        VALUES (:id, :population, :density, ST_GeomFromText(:geom, 4326))
                        ON CONFLICT (id) DO UPDATE SET population = EXCLUDED.population, density = EXCLUDED.density, geom = EXCLUDED.geom
                    """
                    values["population"] = record.properties.get("population")
                    values["density"] = record.properties.get("density")
                else:
                    sql = """
                        INSERT INTO administrative_boundaries (id, name, level, geom)
                        VALUES (:id, :name, :level, ST_GeomFromText(:geom, 4326))
                        ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, level = EXCLUDED.level, geom = EXCLUDED.geom
                    """
                    values["name"] = record.properties.get("name")
                    values["level"] = record.properties.get("level")

                connection.execute(text(sql), values)

    print("Demo data loaded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
