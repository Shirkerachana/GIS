from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


LayerName = Literal["hospitals", "roads", "rivers", "buildings", "population", "administrative_boundaries"]


class ChatRequest(BaseModel):
    query: str
    context: dict[str, Any] = Field(default_factory=dict)


class SpatialRequest(BaseModel):
    target_layer: LayerName
    reference_layer: LayerName | None = None
    distance_km: float | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


class SuitabilityRequest(BaseModel):
    weights: dict[str, float] | None = None
    candidate_count: int = 10


class GeoFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: str | int | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    geometry: dict[str, Any]


class GeoFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoFeature] = Field(default_factory=list)


class GeoAnalysisResult(BaseModel):
    query: str
    mode: str
    intent: dict[str, Any]
    explanation: str
    summary: dict[str, Any]
    selected_tool: str
    spatial_operation: str
    result_count: int
    sources: list[str] = Field(default_factory=list)
    recommended_locations: list[dict[str, Any]] = Field(default_factory=list)
    geojson: GeoFeatureCollection
    supported: bool = True
    message: str | None = None

