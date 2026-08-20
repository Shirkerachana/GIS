from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.app.demo_data import LAYERS, to_feature_collection
from backend.app.gis_tools import GISService
from rag.rag_engine import answer_rag_query


@dataclass
class Intent:
    operation: str
    target_layer: str | None = None
    reference_layer: str | None = None
    distance_km: float | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    wants_rag: bool = False
    supported: bool = True


class GeoAIAgent:
    def __init__(self, service: GISService | None = None):
        self.service = service or GISService()

    def parse_intent(self, query: str, context: dict[str, Any] | None = None) -> Intent:
        normalized = query.lower().strip()
        context = context or {}

        # Check for combined queries (GIS + RAG) - MUST CHECK BEFORE KNOWLEDGE-ONLY QUERIES
        # E.g., "Find the best hospital location and explain the methodology"
        has_spatial_intent = any(phrase in normalized for phrase in [
            "find", "show", "locate", "best", "suitability", 
            "high population", "accessibility", "nearby", "within"
        ])
        has_knowledge_intent = any(phrase in normalized for phrase in [
            "explain", "describe", "methodology", "method"
        ])
        
        if has_spatial_intent and has_knowledge_intent:
            # Combined query: first do spatial analysis, then provide knowledge context
            # Extract the spatial operation based on the query
            if ("best" in normalized and "hospital" in normalized and "location" in normalized):
                return Intent(operation="site_suitability_with_explanation", target_layer="hospitals", wants_rag=True)
            elif "high population" in normalized and ("explain" in normalized or "describe" in normalized or "methodology" in normalized):
                return Intent(operation="find_high_population_areas_explained", target_layer="population", wants_rag=True)

        # Explanation/Why queries (RAG)
        if "why was" in normalized or "why is" in normalized or ("why" in normalized and "recommended" in normalized):
            return Intent(operation="explain_recommendation", wants_rag=True)

        # Knowledge-only queries (RAG)
        knowledge_keywords = [
            "what does", "what is postgis", "how was", "what dataset",
            "what is raster", "what is vector", "raster vs vector",
            "what is gis", "geographic information", "spatial buffer",
            "postGIS", "worldpop", "openstreetmap", "hospital site selection",
            "spatial analysis"
        ]
        if any(phrase in normalized for phrase in knowledge_keywords):
            return Intent(operation="rag", wants_rag=True)

        match = re.search(r"within\s+(\d+(?:\.\d+)?)\s*km\s+of\s+(major roads|roads|rivers)", normalized)
        if match:
            distance = float(match.group(1))
            reference = "roads" if "road" in match.group(2) else "rivers"
            return Intent(operation="find_nearby", target_layer="hospitals", reference_layer=reference, distance_km=distance)

        if "near rivers" in normalized or "hospitals near rivers" in normalized:
            return Intent(operation="find_nearby", target_layer="hospitals", reference_layer="rivers", distance_km=2.0)

        if "near major roads" in normalized or "hospitals near roads" in normalized:
            return Intent(operation="find_nearby", target_layer="hospitals", reference_layer="roads", distance_km=5.0)

        if "hospitals in pune" in normalized or "show all hospitals in pune" in normalized or "show hospitals in pune" in normalized:
            return Intent(operation="find_hospitals", target_layer="hospitals")

        if "high population density" in normalized or "high population areas" in normalized:
            return Intent(operation="find_high_population_areas", target_layer="population")

        if "low hospital accessibility" in normalized:
            return Intent(operation="analyze_accessibility", target_layer="hospitals")

        if "best location for a new hospital" in normalized or "site suitability" in normalized:
            return Intent(operation="site_suitability", target_layer="hospitals")

        if "closest to this river" in normalized or "hospitals closest to this river" in normalized:
            selected = context.get("selected_feature")
            if selected and selected.get("layer") == "rivers":
                return Intent(operation="find_nearby", target_layer="hospitals", reference_layer="rivers", distance_km=5.0)
            return Intent(operation="find_nearby", target_layer="hospitals", reference_layer="rivers", distance_km=5.0)

        return Intent(operation="unsupported", supported=False)

    def run(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        intent = self.parse_intent(query, context)

        if intent.operation == "rag":
            answer = answer_rag_query(query)
            geojson = {"type": "FeatureCollection", "features": []}
            return self._package(query, intent, answer["answer"], answer["source"], "rag", 0, geojson, [], supported=True)

        # Combined operations: GIS + RAG
        if intent.operation == "site_suitability_with_explanation":
            # Run spatial analysis first
            result = self.service.site_suitability()
            # Augment explanation with knowledge base info
            rag_answer = answer_rag_query("hospital site selection methodology")
            augmented_explanation = result["explanation"] + "\n\n" + rag_answer["answer"]
            result["explanation"] = augmented_explanation
            result["sources"] = list(set(result.get("sources", []) + [rag_answer["source"]]))
            return self._package(
                query, intent, result["explanation"], result["selected_tool"],
                result["spatial_operation"], result["result_count"],
                result["geojson"], result.get("recommended_locations", []),
                supported=True, summary=result.get("summary", {}),
                sources=result.get("sources", []), message=result.get("message"),
            )

        if intent.operation == "find_high_population_areas_explained":
            # Run spatial analysis first
            result = self.service.find_high_population_areas()
            # Augment with knowledge about population data and raster analysis
            rag_answer = answer_rag_query("worldpop dataset population")
            augmented_explanation = result["explanation"] + "\n\n" + rag_answer["answer"]
            result["explanation"] = augmented_explanation
            result["sources"] = list(set(result.get("sources", []) + [rag_answer["source"]]))
            return self._package(
                query, intent, result["explanation"], result["selected_tool"],
                result["spatial_operation"], result["result_count"],
                result["geojson"], result.get("recommended_locations", []),
                supported=True, summary=result.get("summary", {}),
                sources=result.get("sources", []), message=result.get("message"),
            )

        if intent.operation == "find_hospitals":
            result = self.service.find_hospitals(filters=intent.filters)
        elif intent.operation == "find_nearby":
            result = self.service.find_nearby(
                target_layer=intent.target_layer or "hospitals",
                reference_layer=intent.reference_layer or "roads",
                distance_km=float(intent.distance_km or 5.0),
                filters=intent.filters,
            )
        elif intent.operation == "find_high_population_areas":
            result = self.service.find_high_population_areas()
        elif intent.operation == "analyze_accessibility":
            result = self.service.analyze_accessibility()
        elif intent.operation == "site_suitability":
            result = self.service.site_suitability()
        elif intent.operation == "explain_recommendation":
            result = self.service.explain_recommendation(context or {})
        else:
            return self._package(
                query,
                intent,
                "This question is currently not supported. Try one of the demo GIS analyses, a knowledge-base question such as 'What is PostGIS?', or a combined question like 'Find the best hospital location and explain the methodology.'",
                "GeoAI Assistant",
                "unsupported",
                0,
                {"type": "FeatureCollection", "features": []},
                [],
                supported=False,
                message="Unsupported operation. The demo currently supports hospitals, nearby analysis, high population areas, accessibility, suitability, RAG-style explanations, and combined GIS+RAG queries.",
            )

        return self._package(
            query,
            intent,
            result["explanation"],
            result["selected_tool"],
            result["spatial_operation"],
            result["result_count"],
            result["geojson"],
            result.get("recommended_locations", []),
            supported=True,
            summary=result.get("summary", {}),
            sources=result.get("sources", []),
            message=result.get("message"),
        )

    def _package(
        self,
        query: str,
        intent: Intent,
        explanation: str,
        selected_tool: str,
        spatial_operation: str,
        result_count: int,
        geojson: dict[str, Any],
        recommended_locations: list[dict[str, Any]],
        *,
        supported: bool,
        summary: dict[str, Any] | None = None,
        sources: list[str] | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "mode": "demo" if self.service.demo_mode else "real",
            "intent": intent.__dict__,
            "explanation": explanation,
            "summary": summary or {},
            "selected_tool": selected_tool,
            "spatial_operation": spatial_operation,
            "result_count": result_count,
            "sources": sources or ["Demo study area: Pune, Maharashtra, India", "Demo OSM-inspired layers stored in-memory"],
            "recommended_locations": recommended_locations,
            "geojson": geojson,
            "supported": supported,
            "message": message,
        }
