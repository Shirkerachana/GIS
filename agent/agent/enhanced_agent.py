"""
Enhanced GeoAI Agent with natural language intent parsing.

Combines the intent parser and tool registry to convert natural language
queries into structured GIS operations with full parameter validation.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.gis_tools import GISService
from backend.app.intent_parser import (
    AnalysisType,
    IntentParser,
    StructuredIntent,
    extract_intent_from_query,
)
from backend.app.tool_registry import (
    OperationValidator,
    ToolRegistry,
    ValidationError,
    get_tool_registry,
)
from rag.rag_engine import answer_rag_query

logger = logging.getLogger(__name__)


class EnhancedGeoAIAgent:
    """
    Enhanced GeoAI Agent with natural language interface.
    
    Converts user queries to structured intents, validates parameters,
    selects approved tools, and executes spatial analysis operations.
    """

    def __init__(self, service: GISService | None = None):
        """
        Initialize the enhanced agent.
        
        Args:
            service: GISService instance (created if None)
        """
        self.service = service or GISService()
        self.parser = IntentParser()
        self.registry = get_tool_registry()

    def process_query(
        self, 
        query: str, 
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process a natural language query end-to-end.
        
        Args:
            query: Natural language query from user
            context: Optional conversation context
            
        Returns:
            Structured response with results
        """
        context = context or {}
        
        try:
            # Step 1: Parse intent from query
            logger.info(f"Parsing query: {query}")
            intent = self.parser.parse(query, context)
            
            # Step 2: Check if unsupported
            if not intent.supported:
                return self._build_unsupported_response(query, intent)
            
            # Step 3: Handle pure RAG queries
            if intent.analysis_type == AnalysisType.RAG:
                logger.info("Processing pure RAG query")
                return self._handle_rag_query(query, intent)
            
            # Step 4: Validate operation
            logger.info(f"Validating operation: {intent.operation}")
            OperationValidator.validate_operation(intent.operation)
            
            # Step 5: Extract and validate parameters
            logger.info("Extracting parameters")
            parameters = self._extract_parameters(intent)
            tool, validated_params = self.registry.validate_and_get_tool(
                intent.operation, 
                parameters
            )
            
            # Step 6: Execute operation
            logger.info(f"Executing operation: {intent.operation}")
            result = self._execute_operation(intent, validated_params)
            
            # Step 7: Augment with RAG knowledge if this is a combined query
            if intent.requires_rag:
                logger.info("Augmenting spatial result with RAG knowledge")
                result = self._augment_with_rag(query, result, intent)
            
            # Step 8: Build response
            response = self._build_response(
                query, 
                intent, 
                tool, 
                result,
                validated_params
            )
            
            logger.info(f"Query processed successfully")
            return response
            
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return self._build_error_response(query, str(e), "validation_error")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return self._build_error_response(query, str(e), "execution_error")

    def _extract_parameters(self, intent: StructuredIntent) -> dict[str, Any]:
        """Extract parameters from structured intent."""
        params = {
            "target_area": intent.target_area,
        }
        
        # Add optional parameters if set
        if intent.distance_km is not None:
            params["distance_km"] = intent.distance_km
        if intent.percentile is not None:
            params["percentile"] = intent.percentile
        if intent.population_threshold is not None:
            params["population_threshold"] = intent.population_threshold
        if intent.target_layer is not None:
            params["target_layer"] = intent.target_layer
        if intent.reference_layer is not None:
            params["reference_layer"] = intent.reference_layer
        if intent.weights:
            params["weights"] = intent.weights
        if intent.filters:
            params["filters"] = intent.filters
        
        return params

    def _execute_operation(
        self, 
        intent: StructuredIntent, 
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute the GIS operation based on intent."""
        operation = intent.operation
        
        # Route to appropriate GIS service method
        if operation == "get_population_statistics":
            return self.service.get_population_statistics()
        
        elif operation == "find_high_population_areas":
            return self.service.find_high_population_areas_raster(
                percentile=parameters.get("percentile", 75.0)
            )
        
        elif operation == "calculate_population_near_hospitals":
            return self.service.calculate_population_near_hospitals(
                radius_km=parameters.get("distance_km", 5.0)
            )
        
        elif operation == "analyze_hospital_accessibility":
            return self.service.analyze_hospital_accessibility_advanced(
                major_road_distance_km=parameters.get("distance_km", 2.0),
                population_threshold=parameters.get("population_threshold", 500.0)
            )
        
        elif operation == "find_healthcare_gaps":
            return self.service.find_healthcare_gaps_analysis(
                min_population_threshold=parameters.get("population_threshold", 5000.0),
                max_hospital_distance_km=parameters.get("distance_km", 5.0)
            )
        
        elif operation == "calculate_site_suitability":
            return self.service.calculate_site_suitability_advanced(
                weights=parameters.get("weights")
            )
        
        elif operation == "find_nearby":
            return self.service.find_nearby(
                target_layer=parameters.get("target_layer", "hospitals"),
                reference_layer=parameters.get("reference_layer", "roads"),
                distance_km=parameters.get("distance_km", 5.0),
                filters=parameters.get("filters", {})
            )
        
        elif operation == "show_layer":
            # Return layer as GeoJSON
            result = self.service.get_layer_geojson(parameters.get("target_layer"))
            return {
                "explanation": f"Displaying {parameters['target_layer']} layer",
                "selected_tool": "Layer Display",
                "spatial_operation": "vector",
                "result_count": result.get("features", {}).__len__() 
                    if isinstance(result.get("features"), list) else 0,
                "geojson": result,
                "sources": ["OSM or Demo Data"],
            }
        
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _handle_rag_query(
        self, 
        query: str, 
        intent: StructuredIntent
    ) -> dict[str, Any]:
        """Handle knowledge-base (RAG) query."""
        try:
            answer = answer_rag_query(query)
            return {
                "query": query,
                "mode": "demo" if self.service.demo_mode else "real",
                "interpreted_request": f"Knowledge-base query: {intent.explanation}",
                "intent": intent.__dict__,
                "analysis_type": "knowledge_base",
                "tools_selected": ["RAG (Retrieval-Augmented Generation)"],
                "result_type": "text",
                "result": answer.get("answer", ""),
                "source": answer.get("source", "Knowledge Base"),
                "geojson": {"type": "FeatureCollection", "features": []},
                "explanation": answer.get("answer", ""),
                "supported": True,
            }
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "query": query,
                "error": f"Could not answer question: {str(e)}",
                "supported": False,
            }

    def _augment_with_rag(
        self,
        query: str,
        spatial_result: dict[str, Any],
        intent: StructuredIntent
    ) -> dict[str, Any]:
        """Augment spatial result with RAG knowledge."""
        try:
            # Determine what RAG knowledge to fetch based on the operation
            rag_query = query
            if intent.operation == "calculate_site_suitability":
                rag_query = "hospital site selection methodology"
            elif intent.operation == "find_high_population_areas":
                rag_query = "population dataset world pop"
            elif intent.operation == "analyze_hospital_accessibility":
                rag_query = "hospital accessibility methodology"
            
            # Get RAG answer
            rag_answer = answer_rag_query(rag_query)
            
            # Merge results
            spatial_result["explanation"] = (
                spatial_result.get("explanation", "") + 
                "\n\nMethodology:\n" + 
                rag_answer.get("answer", "")
            )
            
            # Merge sources
            existing_sources = spatial_result.get("sources", [])
            new_source = rag_answer.get("source", "Knowledge Base")
            if isinstance(existing_sources, list):
                spatial_result["sources"] = existing_sources + [new_source]
            else:
                spatial_result["sources"] = [existing_sources, new_source]
            
            return spatial_result
            
        except Exception as e:
            logger.warning(f"Failed to augment with RAG: {e}")
            return spatial_result

    def _build_response(
        self,
        query: str,
        intent: StructuredIntent,
        tool,
        result: dict[str, Any],
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Build structured response."""
        return {
            "query": query,
            "mode": "demo" if self.service.demo_mode else "real",
            
            # Interpretation
            "interpreted_request": self._build_interpretation(intent, parameters),
            "intent": {
                "operation": intent.operation,
                "analysis_type": intent.analysis_type.value,
                "target_area": intent.target_area,
                "explanation": intent.explanation,
                "confidence": intent.confidence,
            },
            
            # Tool & Analysis Details
            "analysis_type": intent.analysis_type.value,
            "tools_selected": [tool.name],
            "tool_description": tool.description,
            
            # Results
            "result_type": "geospatial_analysis",
            "selected_tool": tool.name,
            "spatial_operation": intent.operation,
            "result_count": result.get("result_count", 0),
            "geojson": result.get("geojson", {"type": "FeatureCollection", "features": []}),
            
            # Output
            "explanation": result.get("explanation", ""),
            "summary": result.get("summary", {}),
            "recommended_locations": result.get("recommended_locations", []),
            
            # Metadata
            "sources": result.get("sources", ["Real data" if not self.service.demo_mode else "Demo data"]),
            "supported": True,
            "parameters_used": parameters,
        }

    def _build_interpretation(self, intent: StructuredIntent, parameters: dict[str, Any]) -> str:
        """Build human-readable interpretation of the query."""
        interpretation = f"{intent.explanation}"
        
        if parameters.get("distance_km"):
            interpretation += f" (radius: {parameters['distance_km']} km)"
        if parameters.get("percentile"):
            interpretation += f" (percentile: {parameters['percentile']}%)"
        if parameters.get("population_threshold"):
            interpretation += f" (min population: {parameters['population_threshold']:,})"
        
        return interpretation

    def _build_unsupported_response(
        self, 
        query: str, 
        intent: StructuredIntent
    ) -> dict[str, Any]:
        """Build response for unsupported queries."""
        return {
            "query": query,
            "mode": "demo" if self.service.demo_mode else "real",
            "interpreted_request": intent.explanation,
            "intent": intent.__dict__,
            "error": "Query not supported",
            "explanation": (
                "This question is currently not supported. "
                "Try one of these queries:\n"
                "- Show high population areas in Pune\n"
                "- Find hospitals in high population areas\n"
                "- Find areas with high population but poor hospital accessibility\n"
                "- Find the best location for a new hospital\n"
                "- Find hospitals within 5 km of major roads\n"
                "- What is PopulationGIS? (knowledge-base questions)"
            ),
            "supported_operations": [
                "find_healthcare_gaps",
                "find_high_population_areas",
                "calculate_population_near_hospitals",
                "analyze_hospital_accessibility",
                "calculate_site_suitability",
                "find_nearby",
                "show_layer",
                "rag",
            ],
            "geojson": {"type": "FeatureCollection", "features": []},
            "supported": False,
        }

    def _build_error_response(
        self, 
        query: str, 
        error_message: str,
        error_type: str
    ) -> dict[str, Any]:
        """Build error response."""
        return {
            "query": query,
            "mode": "demo" if self.service.demo_mode else "real",
            "error": error_message,
            "error_type": error_type,
            "intent": {},
            "summary": {},
            "selected_tool": "None",
            "spatial_operation": "error",
            "result_count": 0,
            "explanation": f"An error occurred while processing your query: {error_message}",
            "geojson": {"type": "FeatureCollection", "features": []},
            "supported": False,
        }

    def get_available_operations(self) -> dict[str, str]:
        """Get list of available operations with descriptions."""
        operations = {}
        for name, tool in self.registry.get_available_tools().items():
            operations[tool.operation_id] = tool.description
        return operations

    def get_example_queries(self) -> list[str]:
        """Get example queries that system can handle."""
        return [
            "Show high population areas in Pune",
            "Find hospitals in high population areas",
            "Find areas with high population but poor hospital accessibility",
            "Find the best location for a new hospital",
            "Find hospitals within 5 km of major roads",
            "Show all hospitals in Pune",
            "What is WorldPop data?",
            "Explain how hospital accessibility is calculated",
        ]
