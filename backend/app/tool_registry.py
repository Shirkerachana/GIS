"""
Tool registry and validator for GIS operations.

Maintains the list of approved tools, validates parameters, and prevents
arbitrary SQL generation or unsupported operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Protocol
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when parameter validation fails."""
    pass


@dataclass
class ToolDefinition:
    """Definition of an approved GIS tool."""
    
    name: str
    description: str
    operation_id: str
    requires_parameters: list[str]
    optional_parameters: list[str] = None
    parameter_validators: dict[str, Callable[[Any], bool]] = None
    
    def __post_init__(self):
        if self.optional_parameters is None:
            self.optional_parameters = []
        if self.parameter_validators is None:
            self.parameter_validators = {}
    
    def validate_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Validate parameters against tool definition.
        
        Args:
            params: Parameters to validate
            
        Returns:
            Validated parameters
            
        Raises:
            ValidationError: If validation fails
        """
        # Check required parameters
        for param in self.requires_parameters:
            if param not in params or params[param] is None:
                raise ValidationError(f"Missing required parameter: {param}")
        
        # Validate each parameter
        validated = {}
        for key, value in params.items():
            if key not in self.requires_parameters and key not in self.optional_parameters:
                logger.warning(f"Ignoring unknown parameter: {key}")
                continue
            
            if key in self.parameter_validators:
                validator = self.parameter_validators[key]
                if not validator(value):
                    raise ValidationError(f"Invalid value for parameter {key}: {value}")
            
            validated[key] = value
        
        return validated


class ToolRegistry:
    """Registry of approved GIS tools."""
    
    def __init__(self):
        """Initialize the tool registry with approved tools."""
        self.tools = self._build_tool_registry()
    
    def _build_tool_registry(self) -> dict[str, ToolDefinition]:
        """Build the registry of approved GIS tools."""
        
        def is_positive_float(v):
            try:
                return float(v) > 0
            except (TypeError, ValueError):
                return False
        
        def is_percentile(v):
            try:
                return 0 <= float(v) <= 100
            except (TypeError, ValueError):
                return False
        
        def is_valid_area(v):
            return isinstance(v, str) and len(v) > 0 and len(v) < 100
        
        def is_valid_operation(v):
            return isinstance(v, str) and v in ["healthcare_gap", "high_population", "population_hospitals", "accessibility", "suitability"]
        
        return {
            # Raster Analysis Tools
            "population_statistics": ToolDefinition(
                name="Population Statistics",
                description="Extract population statistics from raster data",
                operation_id="get_population_statistics",
                requires_parameters=["target_area"],
                optional_parameters=["filters"],
                parameter_validators={
                    "target_area": is_valid_area,
                }
            ),
            
            "high_population_areas": ToolDefinition(
                name="High-Population Areas",
                description="Identify densely populated regions using raster percentile analysis",
                operation_id="find_high_population_areas",
                requires_parameters=["target_area", "percentile"],
                optional_parameters=["filters"],
                parameter_validators={
                    "target_area": is_valid_area,
                    "percentile": is_percentile,
                }
            ),
            
            # Vector-Raster Analysis Tools
            "population_near_hospitals": ToolDefinition(
                name="Population Near Hospitals",
                description="Calculate population served by healthcare facilities within radius",
                operation_id="calculate_population_near_hospitals",
                requires_parameters=["target_area", "distance_km"],
                optional_parameters=["filters"],
                parameter_validators={
                    "target_area": is_valid_area,
                    "distance_km": is_positive_float,
                }
            ),
            
            "hospital_accessibility": ToolDefinition(
                name="Hospital Accessibility Analysis",
                description="Analyze hospital accessibility using multi-factor scoring (roads + population)",
                operation_id="analyze_hospital_accessibility",
                requires_parameters=["target_area", "distance_km"],
                optional_parameters=["population_threshold", "weights"],
                parameter_validators={
                    "target_area": is_valid_area,
                    "distance_km": is_positive_float,
                }
            ),
            
            "healthcare_gaps": ToolDefinition(
                name="Healthcare Gap Analysis",
                description="Identify high-population areas with poor hospital accessibility",
                operation_id="find_healthcare_gaps",
                requires_parameters=["target_area"],
                optional_parameters=["population_threshold", "distance_km"],
                parameter_validators={
                    "target_area": is_valid_area,
                }
            ),
            
            "site_suitability": ToolDefinition(
                name="Site Suitability Analysis",
                description="Multi-criteria analysis for optimal facility placement location",
                operation_id="calculate_site_suitability",
                requires_parameters=["target_area"],
                optional_parameters=["weights", "filters"],
                parameter_validators={
                    "target_area": is_valid_area,
                }
            ),
            
            # Vector Analysis Tools
            "nearby_features": ToolDefinition(
                name="Nearby Features Search",
                description="Find features within specified distance of reference layer",
                operation_id="find_nearby",
                requires_parameters=["target_area", "target_layer", "reference_layer", "distance_km"],
                optional_parameters=["filters"],
                parameter_validators={
                    "target_area": is_valid_area,
                    "target_layer": lambda v: isinstance(v, str) and v in ["hospitals", "roads", "rivers"],
                    "reference_layer": lambda v: isinstance(v, str) and v in ["hospitals", "roads", "rivers"],
                    "distance_km": is_positive_float,
                }
            ),
            
            # Single Layer Query
            "show_layer": ToolDefinition(
                name="Show Layer",
                description="Display features from a single layer",
                operation_id="show_layer",
                requires_parameters=["target_area", "target_layer"],
                optional_parameters=["filters"],
                parameter_validators={
                    "target_area": is_valid_area,
                    "target_layer": lambda v: isinstance(v, str) and v in ["hospitals", "roads", "rivers", "population"],
                }
            ),
        }
    
    def get_tool(self, operation_id: str) -> ToolDefinition | None:
        """Get tool definition by operation ID."""
        for tool in self.tools.values():
            if tool.operation_id == operation_id:
                return tool
        return None
    
    def get_available_tools(self) -> dict[str, ToolDefinition]:
        """Get all available tools."""
        return self.tools.copy()
    
    def validate_and_get_tool(self, operation_id: str, parameters: dict[str, Any]) -> tuple[ToolDefinition, dict[str, Any]]:
        """
        Validate parameters for an operation and return the tool.
        
        Args:
            operation_id: The operation to validate
            parameters: Parameters to validate
            
        Returns:
            Tuple of (ToolDefinition, validated_parameters)
            
        Raises:
            ValidationError: If validation fails
        """
        tool = self.get_tool(operation_id)
        if not tool:
            raise ValidationError(f"Unknown operation: {operation_id}")
        
        validated_params = tool.validate_parameters(parameters)
        return tool, validated_params


class OperationValidator:
    """Validates operations and prevents unsupported/dangerous operations."""
    
    APPROVED_OPERATIONS = {
        "rag",
        "find_healthcare_gaps",
        "find_high_population_areas",
        "calculate_population_near_hospitals",
        "analyze_hospital_accessibility",
        "calculate_site_suitability",
        "find_nearby",
        "show_layer",
        "get_population_statistics",
    }
    
    BLOCKED_OPERATIONS = {
        "execute_sql",
        "raw_query",
        "sql_injection",
        "drop_table",
        "delete_database",
        "execute_shell",
    }
    
    @classmethod
    def validate_operation(cls, operation: str) -> bool:
        """
        Validate that an operation is approved and not blocked.
        
        Args:
            operation: Operation name to validate
            
        Returns:
            True if operation is approved
            
        Raises:
            ValidationError: If operation is blocked or unknown
        """
        if operation in cls.BLOCKED_OPERATIONS:
            raise ValidationError(f"Operation '{operation}' is not allowed")
        
        if operation not in cls.APPROVED_OPERATIONS:
            raise ValidationError(f"Operation '{operation}' is not supported")
        
        return True
    
    @classmethod
    def validate_query_for_injection(cls, query: str) -> bool:
        """
        Check query string for potential SQL injection patterns.
        
        Args:
            query: Query string to check
            
        Returns:
            True if query appears safe
            
        Raises:
            ValidationError: If suspicious patterns detected
        """
        dangerous_patterns = [
            r";\s*drop",
            r";\s*delete",
            r";\s*insert",
            r";\s*update",
            r"--\s*",
            r"/\*.*\*/",
            r"union\s+select",
            r"exec\s*\(",
            r"execute\s*\(",
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, query.lower()):
                raise ValidationError(f"Query contains potentially dangerous pattern: {pattern}")
        
        return True


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if "_tool_registry" not in globals():
        _tool_registry = ToolRegistry()
    return _tool_registry


def validate_operation(operation: str) -> bool:
    """Validate that an operation is approved."""
    return OperationValidator.validate_operation(operation)


def validate_query(query: str) -> bool:
    """Validate a query for injection attacks."""
    return OperationValidator.validate_query_for_injection(query)
