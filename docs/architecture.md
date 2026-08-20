# GeoAI Assistant Architecture

This project is organized around a transparent spatial workflow:

1. React frontend captures a natural-language request.
2. FastAPI validates the request and routes it through the GeoAI agent.
3. The agent selects an approved GIS tool instead of executing arbitrary SQL.
4. Spatial operations run in the backend against demo data or PostGIS.
5. Results are emitted as GeoJSON and visualized on the map.
6. The assistant generates a clear explanation that distinguishes fact from recommendation.

Future extensions:

- RAG / GeoRAG
- Satellite imagery analysis
- Vision foundation models
- MCP tool exposure
- Live PostGIS-backed import pipeline

