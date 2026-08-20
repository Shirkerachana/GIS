CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS hospitals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS roads (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    road_type TEXT,
    geom geometry(LineString, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS rivers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    waterway_type TEXT,
    geom geometry(LineString, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS buildings (
    id TEXT PRIMARY KEY,
    building_type TEXT,
    geom geometry(Polygon, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS population (
    id TEXT PRIMARY KEY,
    population INTEGER,
    density DOUBLE PRECISION,
    geom geometry(Polygon, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS administrative_boundaries (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    level TEXT,
    geom geometry(Polygon, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hospitals_geom ON hospitals USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_rivers_geom ON rivers USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_population_geom ON population USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_boundaries_geom ON administrative_boundaries USING GIST (geom);

