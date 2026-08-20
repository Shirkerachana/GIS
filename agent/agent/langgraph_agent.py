"""
LangGraph-based GeoAI Agent with multi-step reasoning over vector and raster data.

This agent uses LangGraph to coordinate complex spatial analysis workflows involving:
- Vector tools: find_hospitals, find_roads, find_rivers, find_nearby, etc.
- Raster tools: get_population_statistics, find_high_population_areas, etc.
- Combined tools: find_healthcare_gaps, analyze_hospital_accessibility, etc.

The agent reasons about the data using a state machine that tracks:
1. Current step in the workflow
2. Data gathered so far
3. Intermediate results
4. Final analysis results
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from backend.app.gis_tools import GISService
from backend.app.spatial_analysis import RasterDataManager
from backend.app.demo_data import STUDY_AREA
from backend.app.config import settings

logger = logging.getLogger("geoai.langgraph_agent")


@dataclass
class AgentState:
    """
    State managed across the multi-step reasoning workflow.
    
    Tracks:
    - User query and interpretation
    - Vector features gathered (hospitals, roads, rivers)
    - Raster statistics computed
    - Intermediate analysis results
    - Final recommendations
    """
    query: str
    workflow_type: str  # healthcare_gaps, site_suitability, etc.
    
    # Gathered data
    hospitals: list[dict[str, Any]] = field(default_factory=list)
    roads: list[dict[str, Any]] = field(default_factory=list)
    rivers: list[dict[str, Any]] = field(default_factory=list)
    
    # Raster analysis
    population_stats: dict[str, Any] = field(default_factory=dict)
    high_pop_areas: list[dict[str, Any]] = field(default_factory=list)
    
    # Intermediate results
    hospital_coverage: dict[str, Any] = field(default_factory=dict)
    accessibility_scores: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    
    # Final results
    recommended_locations: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    geojson_result: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    workflow_steps: list[str] = field(default_factory=list)
    messages: Annotated[list, add_messages] = field(default_factory=list)


class VectorTools:
    """Tools for querying and analyzing vector data."""
    
    def __init__(self, service: GISService):
        self.service = service
    
    def find_hospitals(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Find hospitals in the study area."""
        logger.info("Tool: find_hospitals")
        result = self.service.find_hospitals(filters)
        return {
            "tool": "find_hospitals",
            "count": result.get("result_count", 0),
            "features": result.get("geojson", {}).get("features", []),
            "geojson": result.get("geojson", {}),
        }
    
    def find_roads(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Find roads in the study area."""
        logger.info("Tool: find_roads")
        result = self.service.find_roads(filters)
        return {
            "tool": "find_roads",
            "count": result.get("result_count", 0),
            "features": result.get("geojson", {}).get("features", []),
            "geojson": result.get("geojson", {}),
        }
    
    def find_rivers(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Find rivers in the study area."""
        logger.info("Tool: find_rivers")
        result = self.service.find_rivers(filters)
        return {
            "tool": "find_rivers",
            "count": result.get("result_count", 0),
            "features": result.get("geojson", {}).get("features", []),
            "geojson": result.get("geojson", {}),
        }
    
    def find_nearby(
        self, 
        target_layer: str,
        reference_layer: str, 
        distance_km: float
    ) -> dict[str, Any]:
        """Find features in target_layer near features in reference_layer."""
        logger.info(f"Tool: find_nearby - target={target_layer}, ref={reference_layer}, dist={distance_km}km")
        result = self.service.find_nearby(
            target_layer=target_layer,
            reference_layer=reference_layer,
            distance_km=distance_km
        )
        return {
            "tool": "find_nearby",
            "target": target_layer,
            "reference": reference_layer,
            "distance_km": distance_km,
            "count": result.get("result_count", 0),
            "features": result.get("geojson", {}).get("features", []),
            "geojson": result.get("geojson", {}),
        }
    
    def calculate_distance(self, feature1: dict, feature2: dict) -> float:
        """Calculate distance in km between two features."""
        from shapely.geometry import shape
        geom1 = shape(feature1["geometry"])
        geom2 = shape(feature2["geometry"])
        
        # Convert to Point (centroid if polygon)
        point1 = geom1.centroid if hasattr(geom1, 'centroid') else geom1
        point2 = geom2.centroid if hasattr(geom2, 'centroid') else geom2
        
        # Calculate distance using haversine
        from math import radians, cos, sin, asin, sqrt
        lon1, lat1 = point1.x, point1.y
        lon2, lat2 = point2.x, point2.y
        
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c  # Radius of Earth in km
        return km
    
    def spatial_intersection(
        self,
        layer1_features: list[dict],
        layer2_features: list[dict]
    ) -> list[dict]:
        """Find features from layer1 that intersect with layer2."""
        from shapely.geometry import shape
        intersecting = []
        
        for f1 in layer1_features:
            geom1 = shape(f1["geometry"])
            for f2 in layer2_features:
                geom2 = shape(f2["geometry"])
                if geom1.intersects(geom2):
                    intersecting.append({
                        "feature": f1,
                        "intersects_with": f2["properties"].get("name", "unknown")
                    })
        
        return intersecting
    
    def analyze_accessibility(
        self,
        hospitals: list[dict],
        target_areas: list[dict],
        distance_threshold_km: float = 5.0
    ) -> dict[str, Any]:
        """Analyze hospital accessibility for target areas."""
        accessibility_scores = []
        
        for area in target_areas:
            # Find nearest hospital
            min_distance = float('inf')
            nearest_hospital = None
            
            for hospital in hospitals:
                dist = self.calculate_distance(area, hospital)
                if dist < min_distance:
                    min_distance = dist
                    nearest_hospital = hospital
            
            # Score: 1.0 if within threshold, decreasing with distance
            if nearest_hospital:
                score = max(0, 1.0 - (min_distance / distance_threshold_km))
                accessibility_scores.append({
                    "area_id": area["properties"].get("id", "unknown"),
                    "nearest_hospital": nearest_hospital["properties"].get("name", "unknown"),
                    "distance_km": round(min_distance, 2),
                    "accessibility_score": round(score, 3),
                    "area_geom": area["geometry"],
                    "hospital_geom": nearest_hospital["geometry"],
                })
        
        return {
            "tool": "analyze_accessibility",
            "scores": accessibility_scores,
            "avg_accessibility": round(
                sum(s["accessibility_score"] for s in accessibility_scores) / len(accessibility_scores) 
                if accessibility_scores else 0, 3
            ),
        }


class RasterTools:
    """Tools for querying and analyzing raster data."""
    
    def __init__(self, raster_path: str | None = None):
        self.raster_path = raster_path or str(settings.worldpop_tif_path)
    
    def get_population_statistics(self) -> dict[str, Any]:
        """Get overall population statistics for the study area."""
        logger.info("Tool: get_population_statistics")
        try:
            with RasterDataManager(self.raster_path) as manager:
                stats = manager.get_stats()
                return {
                    "tool": "get_population_statistics",
                    "total_population": int(stats.total_population),
                    "mean_population": round(stats.mean_population, 2),
                    "median_population": round(stats.median_population, 2),
                    "std_population": round(stats.std_population, 2),
                    "min_population": int(stats.min_population),
                    "max_population": int(stats.max_population),
                    "valid_cells": stats.valid_cells,
                    "total_area_sqkm": round(stats.total_area_sqkm, 2),
                }
        except Exception as e:
            logger.error(f"Error getting population statistics: {e}")
            return {"tool": "get_population_statistics", "error": str(e)}
    
    def find_high_population_areas(self, percentile: float = 75.0) -> dict[str, Any]:
        """Identify areas with high population density (above percentile)."""
        logger.info(f"Tool: find_high_population_areas (percentile={percentile})")
        try:
            from backend.app.gis_tools import GISService
            service = GISService()
            result = service.find_high_population_areas()
            return {
                "tool": "find_high_population_areas",
                "percentile": percentile,
                "count": result.get("result_count", 0),
                "areas": result.get("geojson", {}).get("features", []),
                "geojson": result.get("geojson", {}),
            }
        except Exception as e:
            logger.error(f"Error finding high population areas: {e}")
            return {"tool": "find_high_population_areas", "error": str(e)}
    
    def calculate_population_in_area(self, area_feature: dict) -> dict[str, Any]:
        """Calculate total population in a specific area."""
        logger.info("Tool: calculate_population_in_area")
        try:
            from shapely.geometry import shape
            
            geometry = shape(area_feature["geometry"])
            with RasterDataManager(self.raster_path) as manager:
                area_pop = manager.query_polygon(geometry)
                if area_pop:
                    return {
                        "tool": "calculate_population_in_area",
                        "total_population": int(area_pop.total_population),
                        "mean_population": round(area_pop.mean_population, 2),
                        "area_sqkm": round(area_pop.area_sqkm, 2),
                        "cell_count": area_pop.cell_count,
                    }
                else:
                    return {"tool": "calculate_population_in_area", "error": "No population data in area"}
        except Exception as e:
            logger.error(f"Error calculating population in area: {e}")
            return {"tool": "calculate_population_in_area", "error": str(e)}


class CombinedTools:
    """Tools that combine vector and raster analysis."""
    
    def __init__(self, service: GISService, raster_path: str | None = None):
        self.service = service
        self.vector_tools = VectorTools(service)
        self.raster_tools = RasterTools(raster_path)
    
    def find_healthcare_gaps(self) -> dict[str, Any]:
        """Identify healthcare gaps: high population areas with poor hospital access."""
        logger.info("Tool: find_healthcare_gaps")
        try:
            # Step 1: Get high population areas (raster)
            high_pop = self.raster_tools.find_high_population_areas(percentile=75.0)
            high_pop_features = high_pop.get("areas", [])
            
            if not high_pop_features:
                return {"tool": "find_healthcare_gaps", "gaps": [], "message": "No high population areas found"}
            
            # Step 2: Get hospitals (vector)
            hospitals_result = self.vector_tools.find_hospitals()
            hospitals = hospitals_result.get("features", [])
            
            if not hospitals:
                return {
                    "tool": "find_healthcare_gaps",
                    "gaps": high_pop_features,
                    "message": "High population areas with NO hospitals",
                }
            
            # Step 3: Analyze accessibility
            accessibility = self.vector_tools.analyze_accessibility(
                hospitals, high_pop_features, distance_threshold_km=5.0
            )
            
            # Step 4: Identify gaps (low accessibility scores)
            gaps = [
                {
                    **score,
                    "is_gap": score["accessibility_score"] < 0.5,
                }
                for score in accessibility["scores"]
            ]
            
            gap_features = [g for g in gaps if g["is_gap"]]
            
            return {
                "tool": "find_healthcare_gaps",
                "total_high_pop_areas": len(high_pop_features),
                "gap_count": len(gap_features),
                "gaps": gap_features,
                "avg_accessibility": accessibility["avg_accessibility"],
                "geojson": high_pop,
            }
        except Exception as e:
            logger.error(f"Error finding healthcare gaps: {e}")
            return {"tool": "find_healthcare_gaps", "error": str(e)}
    
    def analyze_hospital_accessibility(self) -> dict[str, Any]:
        """Comprehensive hospital accessibility analysis."""
        logger.info("Tool: analyze_hospital_accessibility")
        try:
            # Get all hospitals
            hospitals = self.vector_tools.find_hospitals().get("features", [])
            
            # Get high population areas
            high_pop_areas = self.raster_tools.find_high_population_areas().get("areas", [])
            
            # Analyze accessibility
            accessibility = self.vector_tools.analyze_accessibility(
                hospitals, high_pop_areas, distance_threshold_km=5.0
            )
            
            # Calculate coverage stats
            total_areas = len(high_pop_areas)
            well_covered = len([s for s in accessibility["scores"] if s["accessibility_score"] > 0.7])
            moderate_coverage = len([s for s in accessibility["scores"] if 0.3 < s["accessibility_score"] <= 0.7])
            poor_coverage = len([s for s in accessibility["scores"] if s["accessibility_score"] <= 0.3])
            
            return {
                "tool": "analyze_hospital_accessibility",
                "total_high_pop_areas": total_areas,
                "hospitals": len(hospitals),
                "well_covered": well_covered,
                "moderate_coverage": moderate_coverage,
                "poor_coverage": poor_coverage,
                "avg_accessibility": accessibility["avg_accessibility"],
                "scores": accessibility["scores"],
            }
        except Exception as e:
            logger.error(f"Error analyzing hospital accessibility: {e}")
            return {"tool": "analyze_hospital_accessibility", "error": str(e)}
    
    def site_suitability(self) -> dict[str, Any]:
        """Identify best locations for new hospital sites."""
        logger.info("Tool: site_suitability")
        try:
            # Get high population areas
            high_pop = self.raster_tools.find_high_population_areas(percentile=85.0)
            candidates = high_pop.get("areas", [])
            
            # Get existing hospitals
            hospitals = self.vector_tools.find_hospitals().get("features", [])
            
            # Get roads
            roads = self.vector_tools.find_roads().get("features", [])
            
            # Score each candidate
            scored_sites = []
            for candidate in candidates:
                # Find nearest hospital
                distances_to_hospitals = [
                    self.vector_tools.calculate_distance(candidate, h) for h in hospitals
                ]
                min_dist_to_hospital = min(distances_to_hospitals) if distances_to_hospitals else 0
                
                # Check proximity to roads
                near_roads = [
                    r for r in roads if self.vector_tools.calculate_distance(candidate, r) < 2.0
                ]
                
                # Calculate score
                # High score if: high population, far from existing hospitals, near roads
                pop_score = 0.4  # From high population selection
                isolation_score = min(1.0, min_dist_to_hospital / 5.0)  # 0 if <5km away, 1.0 if >5km
                road_score = 0.3 if near_roads else 0
                
                total_score = pop_score + (isolation_score * 0.3) + road_score
                
                scored_sites.append({
                    "candidate_id": candidate["properties"].get("id", "unknown"),
                    "population_score": pop_score,
                    "isolation_score": round(isolation_score, 3),
                    "road_proximity_score": road_score,
                    "total_score": round(total_score, 3),
                    "nearest_hospital_km": round(min_dist_to_hospital, 2),
                    "near_roads": len(near_roads) > 0,
                    "geometry": candidate["geometry"],
                })
            
            # Sort by score
            scored_sites.sort(key=lambda x: x["total_score"], reverse=True)
            
            return {
                "tool": "site_suitability",
                "candidate_count": len(candidates),
                "scored_sites": scored_sites[:10],  # Top 10
                "best_site": scored_sites[0] if scored_sites else None,
            }
        except Exception as e:
            logger.error(f"Error analyzing site suitability: {e}")
            return {"tool": "site_suitability", "error": str(e)}


class LangGraphGeoAIAgent:
    """
    Multi-step reasoning agent using LangGraph for geospatial analysis.
    
    Workflow: query → detect workflow type → gather data → analyze → recommend
    """
    
    def __init__(self, service: GISService | None = None):
        self.service = service or GISService()
        self.vector_tools = VectorTools(self.service)
        self.raster_tools = RasterTools()
        self.combined_tools = CombinedTools(self.service)
        
        # Build the LangGraph workflow
        self.graph = self._build_workflow()
        self.compiled_graph = self.graph.compile()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph state machine for reasoning."""
        graph = StateGraph(AgentState)
        
        # Define nodes
        graph.add_node("detect_workflow", self._detect_workflow)
        graph.add_node("gather_vector_data", self._gather_vector_data)
        graph.add_node("gather_raster_data", self._gather_raster_data)
        graph.add_node("gather_both_data", self._gather_both_data)
        graph.add_node("analyze_gaps", self._analyze_gaps)
        graph.add_node("analyze_accessibility", self._analyze_accessibility)
        graph.add_node("site_suitability", self._site_suitability)
        graph.add_node("generate_report", self._generate_report)
        
        # Define edges
        graph.add_edge(START, "detect_workflow")
        
        # Conditional routing based on workflow type
        graph.add_conditional_edges(
            "detect_workflow",
            self._route_workflow,
            {
                "healthcare_gaps": "gather_raster_data",
                "accessibility": "gather_vector_data",
                "site_suitability": "gather_both_data",
                "general": "gather_vector_data",
            }
        )
        
        # Healthcare gaps workflow
        graph.add_edge("gather_raster_data", "analyze_gaps")
        graph.add_edge("analyze_gaps", "generate_report")
        
        # Accessibility workflow
        graph.add_edge("gather_vector_data", "analyze_accessibility")
        graph.add_edge("analyze_accessibility", "generate_report")
        
        # Site suitability workflow
        graph.add_edge("gather_both_data", "site_suitability")
        graph.add_edge("site_suitability", "generate_report")
        
        # All paths lead to report generation
        graph.add_edge("generate_report", END)
        
        return graph
    
    def _detect_workflow(self, state: AgentState) -> AgentState:
        """Detect which workflow type the query requires."""
        logger.info(f"Detecting workflow for query: {state.query}")
        query_lower = state.query.lower()
        
        if any(phrase in query_lower for phrase in ["healthcare gap", "poor hospital", "high population and poor", "gaps in healthcare"]):
            state.workflow_type = "healthcare_gaps"
            state.workflow_steps.append("detect_workflow: healthcare_gaps")
        elif any(phrase in query_lower for phrase in ["best location", "where should", "site", "build a hospital"]):
            state.workflow_type = "site_suitability"
            state.workflow_steps.append("detect_workflow: site_suitability")
        elif any(phrase in query_lower for phrase in ["accessibility", "hospital access", "accessible"]):
            state.workflow_type = "accessibility"
            state.workflow_steps.append("detect_workflow: accessibility")
        else:
            state.workflow_type = "general"
            state.workflow_steps.append("detect_workflow: general")
        
        return state
    
    def _route_workflow(self, state: AgentState) -> str:
        """Route to appropriate workflow branch."""
        return state.workflow_type
    
    def _gather_vector_data(self, state: AgentState) -> AgentState:
        """Gather vector data (hospitals, roads, rivers)."""
        logger.info("Gathering vector data")
        
        hospitals_result = self.vector_tools.find_hospitals()
        state.hospitals = hospitals_result.get("features", [])
        
        roads_result = self.vector_tools.find_roads()
        state.roads = roads_result.get("features", [])
        
        rivers_result = self.vector_tools.find_rivers()
        state.rivers = rivers_result.get("features", [])
        
        state.workflow_steps.append(f"gather_vector_data: {len(state.hospitals)} hospitals, {len(state.roads)} roads, {len(state.rivers)} rivers")
        
        return state
    
    def _gather_raster_data(self, state: AgentState) -> AgentState:
        """Gather raster data (population statistics)."""
        logger.info("Gathering raster data")
        
        stats = self.raster_tools.get_population_statistics()
        state.population_stats = stats
        
        high_pop = self.raster_tools.find_high_population_areas()
        state.high_pop_areas = high_pop.get("areas", [])
        
        state.workflow_steps.append(f"gather_raster_data: {len(state.high_pop_areas)} high population areas")
        
        return state
    
    def _gather_both_data(self, state: AgentState) -> AgentState:
        """Gather both vector and raster data for site suitability analysis."""
        logger.info("Gathering both vector and raster data")
        
        # Gather vector data
        hospitals_result = self.vector_tools.find_hospitals()
        state.hospitals = hospitals_result.get("features", [])
        
        roads_result = self.vector_tools.find_roads()
        state.roads = roads_result.get("features", [])
        
        rivers_result = self.vector_tools.find_rivers()
        state.rivers = rivers_result.get("features", [])
        
        # Gather raster data
        stats = self.raster_tools.get_population_statistics()
        state.population_stats = stats
        
        high_pop = self.raster_tools.find_high_population_areas()
        state.high_pop_areas = high_pop.get("areas", [])
        
        state.workflow_steps.append(
            f"gather_both_data: {len(state.hospitals)} hospitals, {len(state.roads)} roads, "
            f"{len(state.rivers)} rivers, {len(state.high_pop_areas)} high-pop areas"
        )
        
        return state
    
    def _analyze_gaps(self, state: AgentState) -> AgentState:
        """Analyze healthcare gaps."""
        logger.info("Analyzing healthcare gaps")
        
        gaps_result = self.combined_tools.find_healthcare_gaps()
        state.gaps = gaps_result.get("gaps", [])
        state.workflow_steps.append(f"analyze_gaps: {len(state.gaps)} healthcare gaps identified")
        
        return state
    
    def _analyze_accessibility(self, state: AgentState) -> AgentState:
        """Analyze hospital accessibility."""
        logger.info("Analyzing hospital accessibility")
        
        accessibility_result = self.combined_tools.analyze_hospital_accessibility()
        state.accessibility_scores = accessibility_result.get("scores", [])
        state.workflow_steps.append(f"analyze_accessibility: avg score {accessibility_result.get('avg_accessibility', 0)}")
        
        return state
    
    def _site_suitability(self, state: AgentState) -> AgentState:
        """Analyze site suitability."""
        logger.info("Analyzing site suitability")
        
        sites_result = self.combined_tools.site_suitability()
        state.recommended_locations = sites_result.get("scored_sites", [])
        state.workflow_steps.append(f"site_suitability: {len(state.recommended_locations)} candidate sites scored")
        
        return state
    
    def _generate_report(self, state: AgentState) -> AgentState:
        """Generate final report and explanation."""
        logger.info("Generating report")
        
        if state.workflow_type == "healthcare_gaps":
            gap_count = len(state.gaps)
            state.explanation = (
                f"Healthcare Gap Analysis for Pune:\n\n"
                f"Identified {gap_count} high-population areas with poor hospital accessibility "
                f"(accessibility score < 0.5).\n\n"
                f"Key Findings:\n"
                f"- Total high-population areas: {len(state.high_pop_areas)}\n"
                f"- Areas with gaps: {gap_count}\n"
                f"- Study area population: {state.population_stats.get('total_population', 'unknown'):,}\n\n"
                f"Workflow: Analyzed WorldPop raster --> Identified high-density zones --> "
                f"Queried OSM hospitals --> Calculated accessibility --> Found gaps.\n\n"
                f"Recommendation: Prioritize gap areas for new hospital infrastructure development."
            )
        
        elif state.workflow_type == "accessibility":
            avg_score = sum(s.get("accessibility_score", 0) for s in state.accessibility_scores) / len(state.accessibility_scores) if state.accessibility_scores else 0
            state.explanation = (
                f"Hospital Accessibility Analysis for Pune:\n\n"
                f"Analyzed accessibility of {len(state.hospitals)} hospitals to "
                f"{len(state.accessibility_scores)} high-population areas.\n\n"
                f"Key Metrics:\n"
                f"- Average accessibility score: {avg_score:.2%}\n"
                f"- Total hospitals: {len(state.hospitals)}\n"
                f"- High-population areas analyzed: {len(state.accessibility_scores)}\n\n"
                f"Workflow: Gathered hospitals (OSM vector) --> Gathered high-pop areas (WorldPop raster) --> "
                f"Calculated distances --> Scored accessibility.\n\n"
                f"Score interpretation: 1.0 = excellent access, 0.0 = poor access."
            )
        
        elif state.workflow_type == "site_suitability":
            best_site = state.recommended_locations[0] if state.recommended_locations else None
            state.explanation = (
                f"Hospital Site Suitability Analysis for Pune:\n\n"
                f"Evaluated {len(state.recommended_locations)} candidate sites for new hospitals.\n\n"
                f"Scoring Factors:\n"
                f"- Location in high-population area (+0.4 points)\n"
                f"- Distance from existing hospitals (+0.3 points if >5km)\n"
                f"- Proximity to roads (+0.3 points if <2km)\n\n"
                f"Top Recommendation:\n"
                f"- Site ID: {best_site['candidate_id'] if best_site else 'N/A'}\n"
                f"- Suitability Score: {best_site['total_score'] if best_site else 'N/A'}/1.0\n"
                f"- Distance to nearest hospital: {best_site['nearest_hospital_km'] if best_site else 'N/A'} km\n"
                f"- Near roads: {'Yes' if best_site and best_site['near_roads'] else 'No'}\n\n"
                f"Workflow: Gathered high-pop areas (raster) --> Evaluated proximity to infrastructure --> "
                f"Scored on multiple factors --> Ranked candidates."
            )
        
        else:
            state.explanation = (
                f"General Geospatial Query Analysis:\n\n"
                f"Query: {state.query}\n\n"
                f"Data gathered:\n"
                f"- Hospitals: {len(state.hospitals)}\n"
                f"- Roads: {len(state.roads)}\n"
                f"- Rivers: {len(state.rivers)}\n"
                f"- High-pop areas: {len(state.high_pop_areas)}\n"
                f"- Population stats: {state.population_stats}"
            )
        
        state.summary = {
            "workflow_type": state.workflow_type,
            "workflow_steps": state.workflow_steps,
            "data_gathered": {
                "hospitals": len(state.hospitals),
                "roads": len(state.roads),
                "rivers": len(state.rivers),
                "high_pop_areas": len(state.high_pop_areas),
                "gaps": len(state.gaps),
                "accessibility_scores": len(state.accessibility_scores),
            },
            "results": {
                "gaps": len(state.gaps),
                "recommendations": len(state.recommended_locations),
            }
        }
        
        state.workflow_steps.append("generate_report: completed")
        
        return state
    
    def process_query(self, query: str) -> dict[str, Any]:
        """
        Process a geospatial query through the LangGraph workflow.
        
        Args:
            query: User's natural language query
            
        Returns:
            Complete analysis result with reasoning steps
        """
        logger.info(f"Processing query: {query}")
        
        # Initialize state
        initial_state = AgentState(query=query, workflow_type="general")
        
        # Run workflow
        final_state_dict = self.compiled_graph.invoke(initial_state)
        
        # Handle both dict and object outputs from LangGraph
        if isinstance(final_state_dict, dict):
            # Extract state fields if it's a dictionary
            final_state = AgentState(
                query=final_state_dict.get("query", query),
                workflow_type=final_state_dict.get("workflow_type", "general"),
                hospitals=final_state_dict.get("hospitals", []),
                roads=final_state_dict.get("roads", []),
                rivers=final_state_dict.get("rivers", []),
                population_stats=final_state_dict.get("population_stats", {}),
                high_pop_areas=final_state_dict.get("high_pop_areas", []),
                gaps=final_state_dict.get("gaps", []),
                accessibility_scores=final_state_dict.get("accessibility_scores", []),
                recommended_locations=final_state_dict.get("recommended_locations", []),
                summary=final_state_dict.get("summary", {}),
                explanation=final_state_dict.get("explanation", ""),
                geojson_result=final_state_dict.get("geojson_result", {}),
                workflow_steps=final_state_dict.get("workflow_steps", []),
            )
        else:
            final_state = final_state_dict
        
        # Package result
        result = {
            "query": query,
            "workflow_type": final_state.workflow_type,
            "workflow_steps": final_state.workflow_steps,
            "explanation": final_state.explanation,
            "summary": final_state.summary,
            "data": {
                "hospitals": final_state.hospitals,
                "roads": final_state.roads,
                "rivers": final_state.rivers,
                "high_pop_areas": final_state.high_pop_areas,
                "gaps": final_state.gaps,
                "accessibility_scores": final_state.accessibility_scores,
                "recommended_locations": final_state.recommended_locations,
            },
            "geojson": self._build_geojson(final_state),
        }
        
        return result
    
    def _build_geojson(self, state: AgentState) -> dict[str, Any]:
        """Build GeoJSON result from final state."""
        features = []
        
        # Add hospitals
        for hospital in state.hospitals:
            features.append({
                **hospital,
                "properties": {
                    **hospital.get("properties", {}),
                    "type": "hospital",
                    "source": "OSM",
                }
            })
        
        # Add high-pop areas
        for area in state.high_pop_areas:
            features.append({
                **area,
                "properties": {
                    **area.get("properties", {}),
                    "type": "high_population_area",
                    "source": "WorldPop",
                }
            })
        
        # Add gaps
        for gap in state.gaps:
            if "geometry" in gap:
                features.append({
                    "type": "Feature",
                    "geometry": gap["geometry"],
                    "properties": {
                        "type": "healthcare_gap",
                        "accessibility_score": gap.get("accessibility_score"),
                        "nearest_hospital": gap.get("nearest_hospital"),
                        "distance_km": gap.get("distance_km"),
                    }
                })
        
        # Add recommended sites
        for site in state.recommended_locations:
            if "geometry" in site:
                features.append({
                    "type": "Feature",
                    "geometry": site["geometry"],
                    "properties": {
                        "type": "recommended_site",
                        "suitability_score": site.get("total_score"),
                        "isolation_score": site.get("isolation_score"),
                        "near_roads": site.get("near_roads"),
                    }
                })
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "workflow": state.workflow_type,
        }
