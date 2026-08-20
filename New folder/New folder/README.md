# GeoAI Assistant

Natural Language Geospatial Intelligence Platform

GeoAI Assistant is a full-stack demo that turns plain-English geospatial questions into validated GIS analysis, map output, and a human-readable explanation.

## Project Overview

The system demonstrates the core loop:

`User question -> GeoAI agent -> approved GIS tool -> spatial analysis -> GeoJSON -> interactive map -> AI explanation`

The demo mode ships with a compact Pune study area so the app works without requiring a full OSM import on day one. The repository also includes a PostGIS schema and a demo data loader for a real database-backed setup.

## Problem Statement

Most GIS workflows require specialized tools and manual spatial operations. This project shows how a user can ask a natural-language question and let the backend choose a safe spatial operation instead of exposing raw SQL.

## Objectives

- Provide a professional map-first UI
- Convert text queries into structured spatial intents
- Run approved geospatial tools in the backend
- Return valid GeoJSON to the frontend
- Support suitability analysis for a new hospital site
- Keep RAG, satellite intelligence, and MCP modular

## Architecture

- React + TypeScript + Tailwind CSS + Leaflet
- FastAPI + Pydantic + SQLAlchemy
- PostgreSQL + PostGIS
- GeoAI agent layer
- Optional RAG module

## Data Sources

- Demo Pune study area layers in memory
- Real Pune study area extracted from OpenStreetMap vector data
- WorldPop raster clip for Pune population analysis
- PostGIS schema for hospitals, roads, rivers, buildings, population, and boundaries

## Installation

### Backend

```bash
cd geoai-assistant/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd geoai-assistant/frontend
npm install
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values if you want to connect to PostGIS, real Pune datasets, or an external LLM.

## Running Backend

```bash
cd geoai-assistant
uvicorn backend.app.main:app --reload --port 8000
```

Or with Docker:

```bash
docker compose up -d postgis backend
```

## Running Frontend

```bash
cd geoai-assistant/frontend
npm run dev
```

## Loading GIS Data

1. Start PostGIS with `docker compose up -d postgis`
2. Create the schema if needed
3. Load the demo data:

```bash
python scripts/load_demo_data.py
```

4. Extract Pune OSM features from the India PBF:

```bash
python scripts/import_osm.py --pbf ../india-260817.osm.pbf --output-dir data/processed/real
```

5. Clip WorldPop to Pune and generate population statistics:

```bash
python scripts/process_worldpop.py --source ../ind_pop_2025_CN_1km_R2025A_UA_v1.tif --output-dir data/processed/real
```

6. Optionally import the clipped real layers into PostGIS:

```bash
python scripts/import_osm.py --pbf ../india-260817.osm.pbf --output-dir data/processed/real --database-url postgresql+psycopg2://geoai:geoai@localhost:5432/geoai_db
```

## Running the AI Agent

The agent is deterministic in demo mode. If an `LLM_API_KEY` is present later, you can wire the same intent/output contract into a real LLM tool-calling layer without changing the frontend.

## Example Queries

- Show all hospitals in Pune.
- Find hospitals within 5 km of major roads.
- Find areas with high population density.
- Find the best location for a new hospital.
- Why was this location recommended?

## API Documentation

- `GET /api/health`
- `GET /api/layers`
- `GET /api/hospitals`
- `GET /api/roads`
- `GET /api/rivers`
- `GET /api/population`
- `POST /api/chat`
- `POST /api/geo/query`
- `POST /api/analysis/nearby`
- `POST /api/analysis/suitability`

## Future Enhancements

- Real PostGIS queries for all tools
- OSM extraction scripts for Pune and surrounding districts
- RAG over GIS documentation and methodology
- Satellite imagery and foundation-model support
- MCP tool publishing

## Limitations

- The demo layers are intentionally compact
- Suitability scoring is heuristic and for demonstration only
- External APIs are optional and not required for the core UI loop
- Real data mode uses clipped Pune analysis layers, not the full India datasets in the browser

## Demo Instructions

1. Start the backend
2. Start the frontend
3. Click one of the suggested queries
4. Inspect the map, results, and explanation
