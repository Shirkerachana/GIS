# Data Pipeline

This project supports two data paths:

## Demo path

- Uses compact Pune-inspired in-memory layers
- Powers the UI immediately
- Keeps the app usable during presentations

## PostGIS path

1. Create the schema in `database/schema.sql`
2. Start PostGIS with `docker compose up -d postgis`
3. Import demo records with `python scripts/load_demo_data.py`
4. For real OSM data, clip the supplied `india-260817.osm.pbf` to the Pune study area and export selected layers with `python scripts/import_osm.py`
5. Clip WorldPop to Pune with `python scripts/process_worldpop.py`
6. Set `DATA_MODE=real` only after both processed outputs exist in `data/processed/real/`

The import helpers are intentionally conservative and do not load the entire India extract into the browser.
The backend reads the processed Pune layers from disk and can optionally mirror the same outputs into PostGIS.
