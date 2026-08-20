from __future__ import annotations

from difflib import get_close_matches


DOCUMENTS = [
    # ====== GIS Concepts ======
    {
        "title": "What is GIS",
        "keywords": ["what is gis", "geographic information system", "gis concept"],
        "answer": "Geographic Information System (GIS) is a framework for capturing, storing, analyzing, and visualizing geospatial data. GIS combines geographic location data with attribute information to support spatial reasoning and decision-making.",
        "source": "GIS Concepts",
    },
    {
        "title": "Raster data",
        "keywords": ["raster data", "raster", "grid", "pixel", "raster format"],
        "answer": "Raster data represents the world as a grid of cells (pixels), where each cell contains a value representing a phenomenon like temperature, elevation, or population density. Raster data is efficient for continuous phenomena and satellite imagery. Each cell has a location defined by row and column indices.",
        "source": "GIS Concepts",
    },
    {
        "title": "Vector data",
        "keywords": ["vector data", "vector", "geometry", "point", "line", "polygon", "vector format"],
        "answer": "Vector data represents geographic features as discrete geometric objects: points (locations), lines (paths), and polygons (areas). Vector data stores coordinates and attributes, and is ideal for discrete features like buildings, roads, and administrative boundaries. Each feature has precise geometric coordinates.",
        "source": "GIS Concepts",
    },
    {
        "title": "Raster vs Vector",
        "keywords": ["raster vs vector", "difference between raster and vector", "when to use raster", "when to use vector"],
        "answer": "Raster data uses a grid structure and is efficient for continuous phenomena, satellite imagery, and rapid analysis. Vector data uses discrete geometric objects and is precise for discrete features, better for editing, and more compact for sparse data. Choose raster for population density or climate data; vector for roads, buildings, or administrative boundaries.",
        "source": "GIS Concepts",
    },
    {
        "title": "Spatial buffer",
        "keywords": ["buffer", "5 km buffer", "distance operation", "buffering"],
        "answer": "A spatial buffer is an area surrounding a geographic feature within a specified distance. For example, a 5 km buffer around a hospital creates a 5 km radius polygon. Buffers are used to identify features within a certain distance or to analyze proximity relationships.",
        "source": "GIS Concepts",
    },
    {
        "title": "Spatial intersection",
        "keywords": ["intersection", "intersect", "overlap", "spatial relationship"],
        "answer": "Spatial intersection identifies geographic features that overlap or share common areas. For example, finding hospitals that fall within a population density buffer. This is a fundamental spatial relationship operation in GIS analysis.",
        "source": "GIS Concepts",
    },

    # ====== PostGIS Concepts ======
    {
        "title": "PostGIS",
        "keywords": ["postgis", "spatial database", "gis database", "postgresql gis"],
        "answer": "PostGIS is a PostgreSQL extension that adds geometry types, spatial indexes, and functions. Key functions include ST_DWithin (distance within), ST_Intersects (overlap detection), ST_Buffer (create buffer zones), ST_Distance (calculate distance), and ST_Within (containment check). It enables efficient spatial queries on large datasets.",
        "source": "PostGIS Documentation",
    },
    {
        "title": "Geometric types",
        "keywords": ["geometry type", "point", "linestring", "polygon", "multipoint", "geometric"],
        "answer": "PostGIS supports geometric types: Point (single location), LineString (path of connected points), Polygon (enclosed area), and Multi* variants for collections. Each type has associated functions for area calculation, length measurement, and spatial relationships.",
        "source": "PostGIS Documentation",
    },
    {
        "title": "Spatial indexing",
        "keywords": ["spatial index", "gist index", "brin index", "index performance"],
        "answer": "PostGIS uses spatial indexes (GIST, BRIN) to accelerate spatial queries. Indexes organize geometric data into hierarchies for fast lookup and filtering. Without indexes, spatial queries scan all features linearly, which is slow on large datasets.",
        "source": "PostGIS Documentation",
    },

    # ====== Datasets ======
    {
        "title": "WorldPop dataset",
        "keywords": ["worldpop", "population", "population density", "worldpop 2025", "population distribution", "population raster"],
        "answer": "WorldPop is a high-resolution gridded population dataset at 1 km resolution covering the global population distribution. In this project, we use WorldPop 2025 data as a raster to identify high-population areas and calculate population proximity scores. Data source: University of Southampton.",
        "source": "WorldPop Dataset Documentation",
    },
    {
        "title": "OpenStreetMap",
        "keywords": ["openstreetmap", "osm", "osm data", "open street map", "openstreetmap dataset"],
        "answer": "OpenStreetMap (OSM) is a free, open-access geographic database with vector data contributed by volunteers worldwide. OSM contains roads, buildings, hospitals, rivers, administrative boundaries, and points of interest. In this project, we extract hospitals, roads, and rivers from OSM for analysis.",
        "source": "OpenStreetMap Foundation",
    },
    {
        "title": "Hospital dataset",
        "keywords": ["hospital dataset", "hospitals in osm", "healthcare facilities"],
        "answer": "Hospital data in this project comes from OpenStreetMap, where healthcare facilities are tagged with amenity=hospital or related tags. The dataset includes facility location (point geometry) and attributes like name and type.",
        "source": "OpenStreetMap / Project Knowledge Base",
    },

    # ====== Hospital Site Selection ======
    {
        "title": "Hospital site-selection methodology",
        "keywords": ["hospital site selection", "site suitability", "best location", "hospital location methodology", "hospital suitability", "hospital methodology", "hospital", "site selection methodology", "hospital site-selection"],
        "answer": "The hospital site-selection methodology uses transparent multi-factor scoring: (1) Population Coverage (40%): proximity to high-population areas using WorldPop raster data. (2) Road Accessibility (30%): distance to major roads from OSM. (3) Healthcare Gap (30%): distance from existing hospitals, indicating underserved areas. Final score = 0.4*pop_score + 0.3*road_score + 0.3*gap_score, normalized to 0-100. This is for demonstration only and not professional planning advice.",
        "source": "Hospital Site Selection Methodology",
    },
    {
        "title": "Population coverage scoring",
        "keywords": ["population coverage", "population score", "population factor"],
        "answer": "Population coverage evaluates proximity to high-population areas. A 2 km buffer around each candidate location queries the WorldPop raster to find mean population density. Scoring: min(100, 100 * mean_density / 15000), where 15000 is the maximum expected density per sq km. Higher population areas receive higher scores (max 100%).",
        "source": "Hospital Site Selection Methodology",
    },
    {
        "title": "Road accessibility scoring",
        "keywords": ["road accessibility", "road score", "road factor", "accessibility"],
        "answer": "Road accessibility measures distance to major roads from OpenStreetMap. Scoring uses linear decay: max(0, 100 * (1 - distance_km / 5.0)). A location 0 km from a road scores 100%; at 5 km scores 0%. This prioritizes sites easily accessible by vehicle.",
        "source": "Hospital Site Selection Methodology",
    },
    {
        "title": "Healthcare gap scoring",
        "keywords": ["healthcare gap", "gap score", "healthcare gap factor"],
        "answer": "Healthcare gap measures distance from existing hospitals, identifying underserved areas. Scoring: min(100, 100 * distance_km / 7.0). A location 7+ km from any hospital scores 100%; at 0 km scores 0%. This identifies areas with the greatest need for new facilities.",
        "source": "Hospital Site Selection Methodology",
    },

    # ====== Project Architecture ======
    {
        "title": "Project architecture",
        "keywords": ["project architecture", "architecture", "project structure", "geoai system design"],
        "answer": "The GeoAI Assistant uses a layered architecture: (1) Frontend (React/TypeScript): Interactive map and UI. (2) Backend (FastAPI/Python): REST API with spatial analysis endpoints. (3) GIS Layer (Shapely, Rasterio): Vector and raster operations. (4) Data Layer: OSM vector data, WorldPop raster, PostGIS-ready schema. (5) Agent Layer (LangGraph): Query routing to GIS tools or RAG. This modular design allows independent scaling of each component.",
        "source": "Project Architecture Documentation",
    },
    {
        "title": "Backend components",
        "keywords": ["backend", "fastapi", "gis service", "spatial analysis", "backend architecture"],
        "answer": "The FastAPI backend provides endpoints for spatial analysis including find_hospitals, find_nearby, find_high_population_areas, analyze_accessibility, and site_suitability. GISService coordinates vector/raster operations. SpatialAnalysisModule handles population statistics and hospital location optimization. RasterDataManager queries WorldPop raster data.",
        "source": "Project Architecture Documentation",
    },
    {
        "title": "Frontend components",
        "keywords": ["frontend", "react", "typescript", "leaflet", "map", "ui component"],
        "answer": "The React frontend features a Leaflet map for GIS visualization, sidebar with layer controls and search, demo queries for quick exploration, result panel showing analysis output, and specialized components like HospitalCandidates for site-selection results. All components are TypeScript for type safety.",
        "source": "Project Architecture Documentation",
    },

    # ====== Spatial Analysis Methodology ======
    {
        "title": "Spatial-analysis methodology",
        "keywords": ["spatial analysis", "spatial methodology", "analysis method", "methodology"],
        "answer": "The spatial-analysis methodology combines vector and raster operations: (1) Vector queries extract discrete features (hospitals, roads). (2) Raster queries analyze continuous phenomena (population density). (3) Spatial relationships (proximity, intersection) connect features across layers. (4) Multi-factor scoring combines independent metrics. (5) Results are validated and returned as GeoJSON for visualization.",
        "source": "Spatial Analysis Methodology",
    },
    {
        "title": "Multi-factor scoring",
        "keywords": ["multi-factor scoring", "weighted score", "composite score", "factor weighting"],
        "answer": "Multi-factor scoring combines independent metrics using explicit weights. Each factor is normalized to 0-100, then weighted and summed: score = sum(weight_i * normalized_factor_i). This approach provides transparency and allows stakeholders to understand how each factor influences the final recommendation.",
        "source": "Spatial Analysis Methodology",
    },
    {
        "title": "Suitability score",
        "keywords": ["suitability", "suitability score", "score", "recommended location", "suitability analysis"],
        "answer": "The suitability score is a transparent weighted heuristic combining multiple factors. In site-suitability analysis, it uses population coverage (40%), road accessibility (30%), and healthcare gap (30%). The score ranges from 0-100, with higher scores indicating better suitability. This is for demonstration only and not a substitute for professional planning.",
        "source": "Project knowledge base",
    },

    # ====== Study Area ======
    {
        "title": "Study area",
        "keywords": ["pune", "study area", "dataset", "geographical area"],
        "answer": "The demo study area is Pune, Maharashtra, India. The dataset includes in-memory vector layers (hospitals, roads, rivers, buildings) inspired by OpenStreetMap features and WorldPop population raster data clipped to the Pune region. This supports rapid development and testing. The architecture is ready for production data (e.g., full OSM extracts in PostGIS).",
        "source": "Project knowledge base",
    },
]


def answer_rag_query(query: str) -> dict[str, str]:
    normalized = query.lower().strip()
    candidates = []
    for document in DOCUMENTS:
        if any(keyword in normalized for keyword in document["keywords"]):
            candidates.append(document)

    if not candidates:
        titles = [doc["title"] for doc in DOCUMENTS]
        match = get_close_matches(normalized, titles, n=1)
        if match:
            candidates = [doc for doc in DOCUMENTS if doc["title"] == match[0]]

    if not candidates:
        return {
            "answer": "I could not find a knowledge-base entry for that question yet. Try asking about PostGIS, buffers, the study area, or the suitability score.",
            "source": "Knowledge base",
        }

    chosen = candidates[0]
    return {"answer": chosen["answer"], "source": chosen["source"]}

