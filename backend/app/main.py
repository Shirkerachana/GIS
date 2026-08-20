from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parents[2]
for source_root in (repo_root, repo_root / "agent", repo_root / "rag"):
    source_root_text = str(source_root)
    if source_root_text not in sys.path:
        sys.path.insert(0, source_root_text)

from starlette.routing import Router

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from agent.geoai_agent import GeoAIAgent
from agent.enhanced_agent import EnhancedGeoAIAgent
from agent.langgraph_agent import LangGraphGeoAIAgent
from backend.app.config import settings
from backend.app.data_store import get_active_data_store, load_data_store, set_active_data_store
from backend.app.models import ChatRequest, GeoAnalysisResult, SpatialRequest, SuitabilityRequest
from backend.app.gis_tools import GISService


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("geoai")


_router_init = Router.__init__


def _router_init_compat(self, *args, on_startup=None, on_shutdown=None, **kwargs):
    return _router_init(self, *args, **kwargs)


Router.__init__ = _router_init_compat  # type: ignore[assignment]

active_store = load_data_store()
set_active_data_store(active_store)

app = FastAPI(title=settings.app_name, version="1.0.0")
app.max_body_size = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://[a-z0-9-]+\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = GISService(demo_mode=not active_store.is_real)
agent = GeoAIAgent(service=service)
enhanced_agent = EnhancedGeoAIAgent(service=service)
langgraph_agent = LangGraphGeoAIAgent(service=service)


frontend_dist = repo_root / "frontend" / "dist"


@app.get("/", response_model=None)
def root() -> FileResponse | dict[str, str]:
    if frontend_dist.is_dir():
        return FileResponse(frontend_dist / "index.html")
    return {"status": "ok", "service": settings.app_name}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "requested_mode": settings.data_mode,
        "active_mode": get_active_data_store().mode,
        "demo_mode": not get_active_data_store().is_real,
        "real_data_ready": get_active_data_store().is_real,
        "layers": get_active_data_store().layer_names(),
    }


@app.get("/api/layers")
def layers() -> dict[str, Any]:
    return {
        "type": "layers",
        "items": get_active_data_store().layer_summaries(),
    }


@app.get("/api/{layer_name}")
def get_layer(layer_name: str) -> dict[str, Any]:
    store = get_active_data_store()
    if layer_name not in store.layer_names():
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")
    return store.feature_collection(layer_name)


@app.get("/api/hospitals")
def hospitals() -> dict[str, Any]:
    return get_active_data_store().feature_collection("hospitals")


@app.get("/api/roads")
def roads() -> dict[str, Any]:
    return get_active_data_store().feature_collection("roads")


@app.get("/api/rivers")
def rivers() -> dict[str, Any]:
    return get_active_data_store().feature_collection("rivers")


@app.get("/api/population")
def population() -> dict[str, Any]:
    return get_active_data_store().feature_collection("population")


@app.get("/api/population/stats")
def population_stats() -> dict[str, Any]:
    return get_active_data_store().population_stats()


@app.post("/api/analysis/nearby")
def analysis_nearby(request: SpatialRequest) -> dict[str, Any]:
    result = service.find_nearby(request.target_layer, request.reference_layer or "roads", request.distance_km or 5.0, request.filters)
    return result


@app.post("/api/analysis/suitability")
def analysis_suitability(request: SuitabilityRequest) -> dict[str, Any]:
    return service.site_suitability(request.weights, request.candidate_count)


@app.get("/api/analysis/population-statistics")
def get_population_statistics() -> dict[str, Any]:
    """Get comprehensive population statistics from raster data."""
    return service.get_population_statistics()


@app.get("/api/analysis/high-population-areas")
def get_high_population_areas(percentile: float = 75.0) -> dict[str, Any]:
    """Find high-population areas using raster analysis."""
    return service.find_high_population_areas_raster(percentile)


@app.post("/api/analysis/population-near-hospitals")
def get_population_near_hospitals(request: SpatialRequest) -> dict[str, Any]:
    """Calculate population within radius of each hospital."""
    radius_km = request.distance_km or 5.0
    return service.calculate_population_near_hospitals(radius_km)


@app.get("/api/analysis/hospital-accessibility")
def get_hospital_accessibility(
    major_road_distance_km: float = 2.0,
    population_threshold: float = 500.0
) -> dict[str, Any]:
    """Analyze hospital accessibility using population and road data."""
    return service.analyze_hospital_accessibility_advanced(
        major_road_distance_km, population_threshold
    )


@app.get("/api/analysis/healthcare-gaps")
def get_healthcare_gaps(
    min_population_threshold: float = 5000.0,
    max_hospital_distance_km: float = 5.0
) -> dict[str, Any]:
    """Identify healthcare gaps in high-population areas."""
    return service.find_healthcare_gaps_analysis(
        min_population_threshold, max_hospital_distance_km
    )


@app.post("/api/analysis/site-suitability")
def get_site_suitability(request: SuitabilityRequest) -> dict[str, Any]:
    """Calculate multi-factor site suitability for new facilities."""
    return service.calculate_site_suitability_advanced(request.weights)


@app.get("/api/analysis/hospital-site-selection")
def get_hospital_site_selection(candidate_count: int = 50) -> dict[str, Any]:
    """
    Find the best locations for a new hospital using transparent multi-factor scoring.
    
    Uses the following scoring factors:
    - Population coverage (40%): Proximity to high-population areas
    - Road accessibility (30%): Distance to major roads
    - Healthcare gap (30%): Distance from existing hospitals
    
    Returns top 5 candidate locations with detailed scoring breakdown.
    All calculations use real OpenStreetMap and WorldPop data.
    
    Args:
        candidate_count: Number of candidate locations to evaluate (default: 50)
    
    Returns:
        Dict with:
        - top_candidates: List of top 5 sites with scores and factors
        - weights: Scoring weights used (40% pop, 30% roads, 30% healthcare)
        - geojson: Map features for visualization
        - sources: Data sources used (OSM, WorldPop)
        - note: Disclaimer about AI-generated analysis
    """
    from backend.app import spatial_analysis
    return spatial_analysis.find_best_hospital_location(candidate_count)


# ============================================================================
# NATURAL LANGUAGE INTERFACE - Enhanced Agent Endpoints
# ============================================================================

@app.post("/api/query/natural-language")
def natural_language_query(request: ChatRequest) -> dict[str, Any]:
    """
    Process natural language geospatial query with intent parsing and validation.
    
    Converts queries like "Find high population areas" into structured GIS operations.
    Prevents arbitrary SQL and validates all operations against approved tool list.
    
    Args:
        request: ChatRequest with query and optional context
        
    Returns:
        Structured response with:
        - interpreted_request: Human-readable query interpretation
        - intent: Structured GIS intent with parameters
        - analysis_type: Type of analysis (vector/raster/vector_raster)
        - tools_selected: List of approved GIS tools used
        - results: GeoJSON and summary data
        - explanation: Human-readable results explanation
    """
    return enhanced_agent.process_query(request.query, request.context)


@app.get("/api/query/operations")
def list_operations() -> dict[str, Any]:
    """List all available GIS operations and descriptions."""
    return {
        "operations": enhanced_agent.get_available_operations(),
        "examples": enhanced_agent.get_example_queries(),
    }


@app.get("/api/query/examples")
def get_examples() -> dict[str, Any]:
    """Get example queries that the system can handle."""
    return {
        "examples": enhanced_agent.get_example_queries(),
        "description": "Example queries that demonstrate the natural language interface",
    }

# ============================================================================
# LANGGRAPH AGENT - Advanced Multi-Step Reasoning over Vector & Raster Data
# ============================================================================

@app.post("/api/reasoning/analyze")
def langgraph_analyze(request: ChatRequest) -> dict[str, Any]:
    """
    Advanced geospatial analysis using LangGraph agent reasoning.
    
    Uses multi-step workflows to coordinate vector and raster analysis:
    1. Healthcare gaps: Identify high-pop areas with poor hospital access
    2. Accessibility: Analyze hospital coverage and service areas
    3. Site suitability: Recommend locations for new facilities
    
    The agent:
    - Detects workflow type from query
    - Gathers vector data (hospitals, roads, rivers)
    - Gathers raster data (population statistics)
    - Performs multi-factor analysis
    - Returns transparent reasoning steps and results
    
    Example queries:
    - "Find areas in Pune with high population and poor hospital accessibility."
    - "Analyze hospital accessibility in Pune."
    - "Where should we build a new hospital?"
    
    Args:
        request: ChatRequest with natural language query
        
    Returns:
        Complete analysis with:
        - workflow_type: Type of analysis performed
        - workflow_steps: Reasoning steps taken
        - explanation: Detailed findings and recommendations
        - summary: Key metrics and data gathered
        - geojson: Results as GeoJSON features for mapping
        - data: Raw results from each tool
    """
    return langgraph_agent.process_query(request.query)


@app.get("/api/reasoning/workflows")
def list_workflows() -> dict[str, Any]:
    """
    List supported reasoning workflows.
    
    Workflow types:
    - healthcare_gaps: Identify areas with high population and poor hospital access
    - accessibility: Analyze hospital coverage metrics
    - site_suitability: Recommend optimal facility locations
    - general: Multi-layer geospatial queries
    """
    return {
        "workflows": [
            {
                "type": "healthcare_gaps",
                "description": "Identify healthcare gaps in high-population areas",
                "example_query": "Find areas in Pune with high population and poor hospital accessibility.",
                "tools_used": ["get_population_statistics", "find_high_population_areas", 
                              "find_hospitals", "analyze_accessibility"],
            },
            {
                "type": "accessibility",
                "description": "Analyze hospital accessibility and coverage",
                "example_query": "Analyze hospital accessibility in Pune.",
                "tools_used": ["find_hospitals", "find_high_population_areas", "analyze_accessibility"],
            },
            {
                "type": "site_suitability",
                "description": "Recommend locations for new hospital facilities",
                "example_query": "Where should we build a new hospital?",
                "tools_used": ["find_high_population_areas", "find_hospitals", "find_roads", "site_suitability"],
            },
            {
                "type": "general",
                "description": "Multi-layer geospatial query",
                "example_query": "Show all hospitals and major roads.",
                "tools_used": ["find_hospitals", "find_roads", "find_rivers"],
            },
        ],
        "data_sources": {
            "vector": ["hospitals (OSM)", "roads (OSM)", "rivers (OSM)"],
            "raster": ["population (WorldPop 2025, 1km resolution)"],
        },
        "reasoning": "Multi-step workflows with transparent reasoning steps and data provenance",
    }


@app.post("/api/reasoning/vector-tools")
def vector_tools_call(request: ChatRequest) -> dict[str, Any]:
    """Direct access to vector analysis tools."""
    query = request.query.lower()
    
    from agent.langgraph_agent import VectorTools
    vector_tools = VectorTools(service)
    
    if "hospitals" in query:
        return vector_tools.find_hospitals()
    elif "roads" in query:
        return vector_tools.find_roads()
    elif "rivers" in query:
        return vector_tools.find_rivers()
    else:
        return {"error": "Query must specify hospitals, roads, or rivers"}


@app.post("/api/reasoning/raster-tools")
def raster_tools_call(request: ChatRequest) -> dict[str, Any]:
    """Direct access to raster analysis tools."""
    query = request.query.lower()
    
    from agent.langgraph_agent import RasterTools
    raster_tools = RasterTools()
    
    if "statistics" in query or "population stats" in query:
        return raster_tools.get_population_statistics()
    elif "high population" in query:
        percentile = request.context.get("percentile", 75.0) if request.context else 75.0
        return raster_tools.find_high_population_areas(percentile)
    else:
        return {"error": "Query must request population statistics or high-population areas"}

@app.post("/api/geo/query")
def geo_query(request: ChatRequest) -> dict[str, Any]:
    return agent.run(request.query, request.context)


@app.post("/api/chat", response_model=GeoAnalysisResult)
def chat(request: ChatRequest) -> dict[str, Any]:
    return enhanced_agent.process_query(request.query, request.context)


@app.get("/{path:path}", include_in_schema=False, response_model=None)
def frontend_route(path: str) -> FileResponse:
    if not frontend_dist.is_dir():
        raise HTTPException(status_code=404, detail="Not Found")
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    requested_file = (frontend_dist / path).resolve()
    if frontend_dist in requested_file.parents and requested_file.is_file():
        return FileResponse(requested_file)
    return FileResponse(frontend_dist / "index.html")


@app.exception_handler(Exception)
def unhandled_exception(_, exc: Exception):
    logger.exception("Unhandled API error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred while processing the request."})
