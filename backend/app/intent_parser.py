"""
Natural language intent parser for geospatial queries.

Converts user queries into structured GIS intents with parameter extraction and validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

import logging

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Types of spatial analysis supported."""
    VECTOR = "vector"
    RASTER = "raster"
    VECTOR_RASTER = "vector_raster"
    RAG = "rag"
    UNSUPPORTED = "unsupported"


@dataclass
class StructuredIntent:
    """Structured representation of a geospatial query."""
    
    # Core intent
    operation: str
    analysis_type: AnalysisType
    
    # Parameters
    target_area: str | None = None
    population_threshold: float | None = None
    distance_km: float | None = None
    percentile: float | None = None
    
    # Analysis factors
    hospital_accessibility: str | None = None  # 'good', 'moderate', 'poor', 'low'
    healthcare_coverage: str | None = None  # 'high', 'low', 'gap'
    
    # Weighting (for multi-factor analysis)
    weights: dict[str, float] = field(default_factory=dict)
    
    # Configuration
    target_layer: str | None = None
    reference_layer: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    supported: bool = True
    confidence: float = 1.0  # Confidence score (0-1)
    requires_rag: bool = False
    explanation: str = ""  # Human-readable explanation of parsed intent


class IntentParser:
    """Parses natural language queries into structured geospatial intents."""

    def __init__(self):
        """Initialize the intent parser."""
        self.operation_patterns = self._build_patterns()

    def parse(self, query: str, context: dict[str, Any] | None = None) -> StructuredIntent:
        """
        Parse a natural language query into a structured intent.
        
        Args:
            query: Natural language query from user
            context: Additional context from conversation
            
        Returns:
            StructuredIntent with extracted parameters
        """
        context = context or {}
        normalized = query.lower().strip()
        
        # Step 1: Try to match spatial patterns first (including combined queries)
        intent = self._match_patterns(normalized, context)
        if intent:
            logger.debug(f"Parsed intent: {intent.operation} with confidence {intent.confidence}")
            return intent
        
        # Step 2: If no spatial pattern matches, check for pure RAG questions
        if self._is_rag_question(normalized):
            return StructuredIntent(
                operation="rag",
                analysis_type=AnalysisType.RAG,
                target_area="Global",
                requires_rag=True,
                explanation="Knowledge-base query (RAG)",
                confidence=0.9
            )
        
        # Step 3: If no match, return unsupported
        return StructuredIntent(
            operation="unsupported",
            analysis_type=AnalysisType.UNSUPPORTED,
            supported=False,
            confidence=0.0,
            explanation="Could not parse query into supported operations"
        )

    def _is_rag_question(self, normalized: str) -> bool:
        """Check if query is asking for knowledge-base information."""
        rag_patterns = [
            r"what\s",  # Matches "what " followed by anything
            r"why\s(is|are|was|were)",
            r"how\s(does|do|is|are|was|were)",
            r"explain",
            r"tell me about",
            r"describe",
            r"what.*dataset",
            r"dataset.*provides",
            r"postgis",
            r"worldpop",
            r"openstreetmap",
            r"raster",
            r"vector",
            r"spatial",
            r"geographic",
            r"gis",
        ]
        return any(re.search(pattern, normalized) for pattern in rag_patterns)

    def _match_patterns(self, normalized: str, context: dict[str, Any]) -> StructuredIntent | None:
        """Try to match against known patterns."""
        
        # 1. Healthcare Gap Detection
        gap_intent = self._match_healthcare_gaps(normalized)
        if gap_intent:
            return gap_intent
        
        # 2. High Population Areas
        high_pop_intent = self._match_high_population(normalized)
        if high_pop_intent:
            return high_pop_intent
        
        # 3. Population Near Hospitals
        pop_hosp_intent = self._match_population_near_hospitals(normalized)
        if pop_hosp_intent:
            return pop_hosp_intent
        
        # 4. Hospital Accessibility
        accessibility_intent = self._match_hospital_accessibility(normalized)
        if accessibility_intent:
            return accessibility_intent
        
        # 5. Site Suitability
        suitability_intent = self._match_site_suitability(normalized)
        if suitability_intent:
            return suitability_intent
        
        # 6. Nearby Features
        nearby_intent = self._match_nearby(normalized)
        if nearby_intent:
            return nearby_intent
        
        # 7. Single Layer Query
        layer_intent = self._match_single_layer(normalized)
        if layer_intent:
            return layer_intent
        
        return None

    def _match_healthcare_gaps(self, normalized: str) -> StructuredIntent | None:
        """Match healthcare gap queries."""
        patterns = [
            r"high population.*poor.*hospital",
            r"poor.*hospital.*high population",
            r"high population.*low.*hospital",
            r"no hospital.*high population",
            r"underserved.*population",
            r"healthcare gap",
            r"hospital.*access.*poor",
        ]
        
        if not any(re.search(p, normalized) for p in patterns):
            return None
        
        # Extract parameters
        pop_threshold = self._extract_population_threshold(normalized)
        distance = self._extract_distance(normalized)
        
        weights = {
            "population_proximity": 0.4,
            "healthcare_coverage": 0.4,
            "road_accessibility": 0.2,
        }
        
        return StructuredIntent(
            operation="find_healthcare_gaps",
            analysis_type=AnalysisType.VECTOR_RASTER,
            target_area="Pune",
            population_threshold=pop_threshold or 5000.0,
            distance_km=distance or 5.0,
            hospital_accessibility="low",
            healthcare_coverage="gap",
            weights=weights,
            target_layer="population",
            reference_layer="hospitals",
            supported=True,
            confidence=0.9,
            explanation="Identify high-population areas with poor hospital accessibility"
        )

    def _match_high_population(self, normalized: str) -> StructuredIntent | None:
        """Match high population area queries."""
        patterns = [
            r"high population",
            r"densely populated",
            r"population.*area",
            r"area.*high population",
            r"dense population",
        ]
        
        if not any(re.search(p, normalized) for p in patterns):
            return None
        
        # Check if it's combined with other analyses
        if any(keyword in normalized for keyword in ["hospital", "accessibility", "gap"]):
            return None  # Let more specific patterns handle it
        
        percentile = self._extract_percentile(normalized)
        
        return StructuredIntent(
            operation="find_high_population_areas",
            analysis_type=AnalysisType.RASTER,
            target_area="Pune",
            percentile=percentile or 75.0,
            target_layer="population",
            supported=True,
            confidence=0.85,
            explanation=f"Find areas in top {percentile or 75}% population density"
        )

    def _match_population_near_hospitals(self, normalized: str) -> StructuredIntent | None:
        """Match population near hospitals queries."""
        patterns = [
            r"population.*hospital",
            r"hospital.*population",
            r"served.*hospital",
            r"population.*served",
        ]
        
        if not any(re.search(p, normalized) for p in patterns):
            return None
        
        # Make sure it's not a gap query
        if any(keyword in normalized for keyword in ["gap", "no hospital", "poor", "low"]):
            return None
        
        distance = self._extract_distance(normalized)
        
        return StructuredIntent(
            operation="calculate_population_near_hospitals",
            analysis_type=AnalysisType.VECTOR_RASTER,
            target_area="Pune",
            distance_km=distance or 5.0,
            target_layer="hospitals",
            supported=True,
            confidence=0.85,
            explanation=f"Calculate population within {distance or 5.0} km of hospitals"
        )

    def _match_hospital_accessibility(self, normalized: str) -> StructuredIntent | None:
        """Match hospital accessibility queries."""
        patterns = [
            r"hospital.*accessibility",
            r"accessibility.*hospital",
            r"hospital.*access",
            r"access.*hospital",
            r"hospital.*road",
            r"road.*hospital",
        ]
        
        if not any(re.search(p, normalized) for p in patterns):
            return None
        
        # Make sure it's not a gap query
        if "gap" in normalized or "poor" in normalized or "low" in normalized:
            return None
        
        road_distance = self._extract_distance(normalized) or 2.0
        
        weights = {
            "road_accessibility": 0.5,
            "population_proximity": 0.3,
            "healthcare_coverage": 0.2,
        }
        
        return StructuredIntent(
            operation="analyze_hospital_accessibility",
            analysis_type=AnalysisType.VECTOR_RASTER,
            target_area="Pune",
            distance_km=road_distance,
            target_layer="hospitals",
            reference_layer="roads",
            weights=weights,
            supported=True,
            confidence=0.85,
            explanation=f"Analyze hospital accessibility (road distance: {road_distance} km)"
        )

    def _match_site_suitability(self, normalized: str) -> StructuredIntent | None:
        """Match site suitability / facility location queries."""
        patterns = [
            r"best.*location.*hospital",
            r"best.*hospital.*location",
            r"site suitability",
            r"where.*build.*hospital",
            r"new hospital.*location",
            r"hospital.*recommend",
            r"location.*new.*hospital",
            r"optimal.*hospital",
            r"suitable.*location.*hospital",
        ]
        
        if not any(re.search(p, normalized) for p in patterns):
            return None
        
        # Check if this is a combined query (spatial + knowledge)
        knowledge_keywords = ["explain", "methodology", "method", "how.*select", "how.*choose"]
        has_knowledge_intent = any(re.search(kw, normalized) for kw in knowledge_keywords)
        
        # Extract weights if specified
        weights = self._extract_weights(normalized)
        if not weights:
            weights = {
                "population_proximity": 0.4,
                "road_accessibility": 0.25,
                "healthcare_coverage": 0.25,
                "environmental_factors": 0.1,
            }
        
        # For combined queries, we still return calculate_site_suitability but with requires_rag=True
        # The enhanced_agent will need to augment the result with RAG knowledge
        return StructuredIntent(
            operation="calculate_site_suitability",
            analysis_type=AnalysisType.VECTOR_RASTER,
            target_area="Pune",
            weights=weights,
            target_layer="hospitals",
            requires_rag=has_knowledge_intent,  # Set to True for combined queries
            supported=True,
            confidence=0.9,
            explanation="Multi-factor site suitability analysis for new hospital location"
        )

    def _match_nearby(self, normalized: str) -> StructuredIntent | None:
        """Match nearby feature queries."""
        patterns = [
            (r"hospital.*near.*road", "hospitals", "roads"),
            (r"hospital.*near.*river", "hospitals", "rivers"),
            (r"near.*road.*hospital", "hospitals", "roads"),
            (r"near.*river.*hospital", "hospitals", "rivers"),
            (r"within\s+(\d+(?:\.\d+)?)\s*km\s+of\s+(roads?|rivers?)", None, None),
        ]
        
        for pattern, target, reference in patterns:
            match = re.search(pattern, normalized)
            if match:
                if not target:  # Extract from pattern
                    distance = float(match.group(1))
                    reference = "roads" if "road" in match.group(2) else "rivers"
                    target = "hospitals"
                else:
                    distance = self._extract_distance(normalized) or 5.0
                
                return StructuredIntent(
                    operation="find_nearby",
                    analysis_type=AnalysisType.VECTOR,
                    target_area="Pune",
                    distance_km=distance,
                    target_layer=target,
                    reference_layer=reference,
                    supported=True,
                    confidence=0.85,
                    explanation=f"Find {target} within {distance} km of {reference}"
                )
        
        return None

    def _match_single_layer(self, normalized: str) -> StructuredIntent | None:
        """Match single layer queries (show hospitals, show roads, etc)."""
        import re
        
        # If query has knowledge keywords (as complete words), it's not a simple layer display
        knowledge_keywords = [r"\bexplain\b", r"\bmethodology\b", r"\bmethod\b", r"\bwhat\s+is\b", r"\bhow\b"]
        if any(re.search(kw, normalized) for kw in knowledge_keywords):
            return None
        
        layers = {
            "hospitals": r"hospital",
            "roads": r"road",
            "rivers": r"river|water",
        }
        
        for layer, pattern in layers.items():
            if re.search(pattern, normalized):
                return StructuredIntent(
                    operation="show_layer",
                    analysis_type=AnalysisType.VECTOR,
                    target_area="Pune",
                    target_layer=layer,
                    supported=True,
                    confidence=0.8,
                    explanation=f"Display {layer} layer"
                )
        
        return None

    def _build_patterns(self) -> dict[str, list[str]]:
        """Build pattern dictionary for future extensibility."""
        return {}

    def _extract_distance(self, text: str) -> float | None:
        """Extract distance parameter from text."""
        match = re.search(r"(\d+(?:\.\d+)?)\s*km", text)
        if match:
            return float(match.group(1))
        return None

    def _extract_percentile(self, text: str) -> float | None:
        """Extract percentile parameter from text."""
        match = re.search(r"top\s+(\d+)%|(\d+)(?:st|nd|rd|th)\s+percentile", text)
        if match:
            return float(match.group(1) or match.group(2))
        
        # Default thresholds
        if "high" in text or "densest" in text:
            return 75.0
        
        return None

    def _extract_population_threshold(self, text: str) -> float | None:
        """Extract population threshold from text."""
        match = re.search(r"(\d+(?:,\d+)*)\s*(?:population|people)", text)
        if match:
            return float(match.group(1).replace(",", ""))
        
        # Keywords
        if "large population" in text or "significant population" in text:
            return 10000.0
        if "small population" in text:
            return 1000.0
        
        return None

    def _extract_weights(self, text: str) -> dict[str, float] | None:
        """Extract factor weights from text."""
        # TODO: Implement advanced weight extraction if needed
        return None


def extract_intent_from_query(query: str, context: dict[str, Any] | None = None) -> StructuredIntent:
    """
    Convenience function to parse a query into a structured intent.
    
    Args:
        query: Natural language query
        context: Optional conversation context
        
    Returns:
        StructuredIntent with parsed parameters
    """
    parser = IntentParser()
    return parser.parse(query, context)
