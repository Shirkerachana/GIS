# Demo Data

This folder is reserved for extracted and transformed geospatial data.

Suggested layout:

- `data/demo/` for small demo GeoJSON exports
- `data/raw/` for source extracts such as OSM PBF or WorldPop rasters
- `data/processed/` for clipped or simplified analysis-ready layers
- `data/processed/real/` for Pune OSM and WorldPop outputs used by the backend in real mode

The backend demo mode uses compact in-memory study-area layers so the UI works even when PostGIS has not been provisioned yet.
