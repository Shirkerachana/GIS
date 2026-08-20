from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians
from typing import Any, Callable

from shapely.geometry import Point, mapping, shape
from shapely.ops import transform

from backend.app.data_store import get_active_data_store
from backend.app.demo_data import STUDY_AREA, Record, ORIGIN_LAT, ORIGIN_LON, KM_PER_DEG_LAT, KM_PER_DEG_LON, to_feature
from backend.app import spatial_analysis


def _to_local(x: float, y: float, z: float | None = None) -> tuple[float, float]:
    return ((x - ORIGIN_LON) * KM_PER_DEG_LON, (y - ORIGIN_LAT) * KM_PER_DEG_LAT)


def _to_geo(x: float, y: float, z: float | None = None) -> tuple[float, float]:
    return (x / KM_PER_DEG_LON + ORIGIN_LON, y / KM_PER_DEG_LAT + ORIGIN_LAT)


def project_geom(geometry):
    return transform(_to_local, geometry)


def unproject_geom(geometry):
    return transform(_to_geo, geometry)


def distance_km(a, b) -> float:
    return project_geom(a).distance(project_geom(b))


def buffer_km(geometry, distance_km_value: float):
    return unproject_geom(project_geom(geometry).buffer(distance_km_value))


def _feature_matches(record: Record, filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        value = record.properties.get(key)
        if value is None:
            return False
        if str(expected).lower() not in str(value).lower():
            return False
    return True


def _layer_records(layer: str, filters: dict[str, Any] | None = None) -> list[Record]:
    records = list(get_active_data_store().layer_records(layer))
    if not filters:
        return records
    return [record for record in records if _feature_matches(record, filters)]


def _source_label(real_label: str, demo_label: str) -> str:
    return real_label if get_active_data_store().is_real else demo_label


def _collection(layer: str, records: list[Record]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": layer,
        "features": [to_feature(record) for record in records],
    }


def _result_payload(
    explanation: str,
    selected_tool: str,
    spatial_operation: str,
    records: list[Record],
    *,
    geojson: dict[str, Any] | None = None,
    recommended_locations: list[dict[str, Any]] | None = None,
    summary: dict[str, Any] | None = None,
    sources: list[str] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "explanation": explanation,
        "selected_tool": selected_tool,
        "spatial_operation": spatial_operation,
        "result_count": len(records),
        "geojson": geojson or _collection("result", records),
        "recommended_locations": recommended_locations or [],
        "summary": summary or {},
        "sources": sources or [],
        "message": message,
    }


@dataclass
class GISService:
    demo_mode: bool = True

    def find_hospitals(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        effective_filters = {k: v for k, v in (filters or {}).items() if k != "place"}
        records = _layer_records("hospitals", effective_filters)
        explanation = f"Found {len(records)} hospitals in the current study area."
        return _result_payload(
            explanation,
            "find_hospitals",
            "attribute filter",
            records,
            geojson=_collection("hospitals", records),
            summary={"layer": "hospitals", "filters": effective_filters},
            sources=[_source_label("Pune OSM hospital layer", "Demo in-memory hospital layer")],
        )

    def find_roads(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        records = _layer_records("roads", filters)
        return _result_payload(
            f"Retrieved {len(records)} roads.",
            "find_roads",
            "attribute filter",
            records,
            geojson=_collection("roads", records),
            summary={"layer": "roads", "filters": filters or {}},
            sources=[_source_label("Pune OSM road layer", "Demo in-memory road layer")],
        )

    def find_rivers(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        records = _layer_records("rivers", filters)
        return _result_payload(
            f"Retrieved {len(records)} rivers.",
            "find_rivers",
            "attribute filter",
            records,
            geojson=_collection("rivers", records),
            summary={"layer": "rivers", "filters": filters or {}},
            sources=[_source_label("Pune OSM river layer", "Demo in-memory river layer")],
        )

    def find_nearby(
        self,
        target_layer: str,
        reference_layer: str,
        distance_km: float,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        targets = _layer_records(target_layer, filters)
        references = _layer_records(reference_layer)
        selected: list[Record] = []
        matches: list[dict[str, Any]] = []

        for record in targets:
            nearest = min((distance_km_between_records(record, ref) for ref in references), default=None)
            if nearest is not None and nearest <= distance_km:
                selected.append(record)
                matches.append({"id": record.id, "distance_km": round(nearest, 2)})

        explanation = (
            f"Identified {len(selected)} {target_layer} features within {distance_km:g} km of {reference_layer}."
        )
        return _result_payload(
            explanation,
            "find_nearby",
            "proximity analysis",
            selected,
            geojson=_collection(target_layer, selected),
            recommended_locations=[],
            summary={
                "target_layer": target_layer,
                "reference_layer": reference_layer,
                "distance_km": distance_km,
                "matches": matches,
            },
            sources=[_source_label(f"Pune OSM {target_layer} and {reference_layer} layers", f"Demo in-memory {target_layer} and {reference_layer} layers")],
        )

    def find_within_distance(
        self,
        target_layer: str,
        reference_layer: str,
        distance_km: float,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.find_nearby(target_layer, reference_layer, distance_km, filters)

    def calculate_distance(self, from_layer: str, to_layer: str) -> dict[str, Any]:
        left = _layer_records(from_layer)
        right = _layer_records(to_layer)
        distances = []
        for record in left:
            nearest = min((distance_km_between_records(record, other) for other in right), default=None)
            if nearest is not None:
                distances.append({"id": record.id, "distance_km": round(nearest, 2)})

        explanation = f"Calculated minimum distances from {from_layer} to {to_layer}."
        return {
            "explanation": explanation,
            "selected_tool": "calculate_distance",
            "spatial_operation": "distance measurement",
            "result_count": len(distances),
            "geojson": _collection(from_layer, left),
            "recommended_locations": [],
            "summary": {"distances": distances},
            "sources": [_source_label(f"Pune OSM {from_layer} and {to_layer} layers", f"Demo in-memory {from_layer} and {to_layer} layers")],
        }

    def create_buffer(self, layer: str, distance_km: float) -> dict[str, Any]:
        records = _layer_records(layer)
        buffered = []
        for record in records:
            buffered_geom = buffer_km(record.geometry, distance_km)
            buffered.append(
                Record(
                    id=f"{record.id}_buffer",
                    properties={**record.properties, "buffer_km": distance_km},
                    geometry=buffered_geom,
                )
            )
        explanation = f"Created a {distance_km:g} km buffer around {len(records)} {layer} features."
        return _result_payload(
            explanation,
            "create_buffer",
            "buffer analysis",
            buffered,
            geojson=_collection(f"{layer}_buffer", buffered),
            summary={"layer": layer, "distance_km": distance_km},
            sources=[_source_label(f"Pune OSM {layer} layer", f"Demo in-memory {layer} layer")],
        )

    def spatial_intersection(self, layer_a: str, layer_b: str) -> dict[str, Any]:
        a = _layer_records(layer_a)
        b = _layer_records(layer_b)
        intersections = [record for record in a if any(record.geometry.intersects(other.geometry) for other in b)]
        explanation = f"Found {len(intersections)} intersecting features between {layer_a} and {layer_b}."
        return _result_payload(
            explanation,
            "spatial_intersection",
            "intersection analysis",
            intersections,
            geojson=_collection(layer_a, intersections),
            summary={"layer_a": layer_a, "layer_b": layer_b},
            sources=[_source_label(f"Pune OSM {layer_a} and {layer_b} layers", f"Demo in-memory {layer_a} and {layer_b} layers")],
        )

    def find_high_population_areas(self) -> dict[str, Any]:
        population_records = _layer_records("population")
        if not population_records:
            records = []
            threshold = 0.0
        else:
            values = [float(record.properties.get("density") or record.properties.get("population") or 0) for record in population_records]
            if get_active_data_store().is_real:
                ranked = sorted(values, reverse=True)
                cutoff_index = max(0, min(len(ranked) - 1, len(ranked) // 4))
                threshold = ranked[cutoff_index]
            else:
                threshold = 8000.0
            records = [
                record
                for record in population_records
                if float(record.properties.get("density") or record.properties.get("population") or 0) >= threshold
            ]
        explanation = f"Identified {len(records)} high-density population polygons."
        return _result_payload(
            explanation,
            "find_high_population_areas",
            "density analysis",
            records,
            geojson=_collection("population", records),
            summary={"threshold_density": round(threshold, 3)},
            sources=[_source_label("WorldPop Pune raster clip", "Demo in-memory population layer")],
        )

    def find_existing_facilities(self) -> dict[str, Any]:
        return self.find_hospitals()

    def analyze_accessibility(self) -> dict[str, Any]:
        roads = _layer_records("roads", {"road_type": "major"})
        hospitals = _layer_records("hospitals")
        underserved = []
        for hospital in hospitals:
            nearest_major_road = min((distance_km_between_records(hospital, road) for road in roads), default=999.0)
            if nearest_major_road > 1.5:
                underserved.append(
                    {
                        "id": hospital.id,
                        "name": hospital.properties.get("name"),
                        "distance_to_major_road_km": round(nearest_major_road, 2),
                    }
                )
        explanation = f"Found {len(underserved)} hospitals with weaker major-road accessibility."
        return {
            "explanation": explanation,
            "selected_tool": "analyze_accessibility",
            "spatial_operation": "accessibility analysis",
            "result_count": len(underserved),
            "geojson": _collection("hospitals", hospitals),
            "recommended_locations": [],
            "summary": {"underserved_hospitals": underserved},
            "sources": [_source_label("Pune OSM hospitals and major roads", "Demo in-memory hospitals and major roads")],
        }

    def site_suitability(self, weights: dict[str, float] | None = None, candidate_count: int = 10) -> dict[str, Any]:
        weights = weights or {
            "population_coverage": 0.35,
            "road_accessibility": 0.25,
            "healthcare_gap": 0.20,
            "environmental_suitability": 0.20,
        }
        candidates = _generate_candidate_points(candidate_count)
        scored = []
        hospitals = _layer_records("hospitals")
        major_roads = _layer_records("roads", {"road_type": "major"})
        rivers = _layer_records("rivers")
        population = _layer_records("population")

        for index, candidate in enumerate(candidates):
            population_score = _normalized_population_score(candidate, population)
            road_score = _normalized_distance_score(candidate, major_roads, reverse=False, max_distance_km=3.0)
            gap_score = _normalized_distance_score(candidate, hospitals, reverse=True, max_distance_km=4.0)
            environmental_score = _normalized_distance_score(candidate, rivers, reverse=True, max_distance_km=2.5)
            score = (
                weights.get("population_coverage", 0.35) * population_score
                + weights.get("road_accessibility", 0.25) * road_score
                + weights.get("healthcare_gap", 0.20) * gap_score
                + weights.get("environmental_suitability", 0.20) * environmental_score
            ) * 100.0
            scored.append(
                {
                    "rank_seed": index + 1,
                    "name": f"Candidate {index + 1}",
                    "score": round(score, 1),
                    "reason": _candidate_reason(population_score, road_score, gap_score, environmental_score),
                    "geometry": candidate,
                }
            )

        ranked = sorted(scored, key=lambda item: item["score"], reverse=True)[:3]
        recommendation_features = []
        for item in ranked:
            recommendation_features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "name": item["name"],
                        "score": item["score"],
                        "reason": item["reason"],
                        "rank": ranked.index(item) + 1,
                        "analysis_type": "AI-generated suitability analysis for demonstration purposes",
                    },
                    "geometry": mapping(item["geometry"]),
                }
            )

        explanation = "Generated a transparent, demonstration-only hospital suitability ranking using population, roads, hospital coverage, and river proximity."
        return {
            "explanation": explanation,
            "selected_tool": "site_suitability",
            "spatial_operation": "multi-factor scoring",
            "result_count": len(ranked),
            "geojson": {"type": "FeatureCollection", "features": recommendation_features},
            "recommended_locations": [
                {
                    "name": item["name"],
                    "score": item["score"],
                    "reason": item["reason"],
                    "coordinates": [round(item["geometry"].x, 6), round(item["geometry"].y, 6)],
                    "analysis_type": "AI-generated suitability analysis for demonstration purposes",
                }
                for item in ranked
            ],
            "summary": {
                "weights": weights,
                "candidate_count": candidate_count,
                "note": "AI-generated suitability analysis for demonstration purposes",
            },
            "sources": [_source_label("Pune OSM + WorldPop layers", "Demo in-memory layers"), "Transparent heuristic scoring model"],
        }

    def explain_recommendation(self, context: dict[str, Any]) -> dict[str, Any]:
        selected = context.get("selected_location") or context.get("recommended_locations", [{}])[0]
        score = selected.get("score")
        reason = selected.get("reason", "No recommendation context was supplied.")
        explanation = f"This location was recommended because {reason}"
        if score is not None:
            explanation += f" and received a score of {score}."
        return {
            "explanation": explanation,
            "selected_tool": "explain_recommendation",
            "spatial_operation": "explanation",
            "result_count": 1 if selected else 0,
            "geojson": {"type": "FeatureCollection", "features": []},
            "recommended_locations": [selected] if selected else [],
            "summary": {"context": context},
            "sources": ["Derived from the previously returned suitability analysis"],
        }

    def get_population_statistics(self) -> dict[str, Any]:
        """Get comprehensive population statistics from raster data."""
        stats = spatial_analysis.get_population_statistics()
        if not stats:
            stats = {"source": "Not available"}
        
        explanation = "Retrieved comprehensive population statistics from the WorldPop dataset."
        return {
            "explanation": explanation,
            "selected_tool": "get_population_statistics",
            "spatial_operation": "raster statistics",
            "result_count": 1,
            "geojson": {"type": "FeatureCollection", "features": []},
            "recommended_locations": [],
            "summary": stats,
            "sources": ["WorldPop population raster"],
        }

    def find_high_population_areas_raster(self, percentile: float = 75.0) -> dict[str, Any]:
        """Find high-population areas using raster analysis."""
        result = spatial_analysis.find_high_population_areas(percentile)
        return {
            **result,
            "result_count": result.get("high_population_count", 0),
            "geojson": result.get("geojson", {"type": "FeatureCollection", "features": []}),
            "recommended_locations": [],
            "summary": {
                "threshold_percentile": percentile,
                "high_population_count": result.get("high_population_count", 0),
                "total_population_in_high_areas": result.get("total_population_in_high_areas", 0),
                "area_percentage": result.get("area_percentage", 0),
            },
        }

    def calculate_population_near_hospitals(self, radius_km: float = 5.0) -> dict[str, Any]:
        """Calculate population within radius of each hospital."""
        result = spatial_analysis.calculate_population_near_hospitals(radius_km)
        return {
            **result,
            "result_count": result.get("hospitals_analyzed", 0),
            "geojson": result.get("geojson", {"type": "FeatureCollection", "features": []}),
            "recommended_locations": [],
            "summary": {
                "hospitals_analyzed": result.get("hospitals_analyzed", 0),
                "radius_km": radius_km,
                "total_population_nearby": result.get("total_population_nearby", 0),
                "average_population_per_hospital": result.get("average_population_per_hospital", 0),
            },
        }

    def analyze_hospital_accessibility_advanced(
        self,
        major_road_distance_km: float = 2.0,
        population_threshold: float = 500.0,
    ) -> dict[str, Any]:
        """Analyze hospital accessibility using population and road data."""
        result = spatial_analysis.analyze_hospital_accessibility(
            major_road_distance_km, population_threshold
        )
        
        hospitals = _layer_records("hospitals")
        return {
            **result,
            "result_count": result.get("hospitals_analyzed", 0),
            "geojson": _collection("hospitals", hospitals),
            "recommended_locations": [],
            "summary": {
                "hospitals_analyzed": result.get("hospitals_analyzed", 0),
                "accessibility_summary": result.get("accessibility_summary", {}),
                "major_road_distance_km": major_road_distance_km,
            },
        }

    def find_healthcare_gaps_analysis(
        self,
        min_population_threshold: float = 5000.0,
        max_hospital_distance_km: float = 5.0,
    ) -> dict[str, Any]:
        """Identify healthcare gaps in high-population areas."""
        result = spatial_analysis.find_healthcare_gaps(
            min_population_threshold, max_hospital_distance_km
        )
        
        # Convert results to GeoJSON features
        features = []
        for gap in result.get("results", [])[:100]:
            features.append({
                "type": "Feature",
                "properties": {
                    "population": gap.get("population"),
                    "nearest_hospital_distance_km": gap.get("nearest_hospital_distance_km"),
                    "gap_severity": gap.get("gap_severity"),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": gap.get("location", [0, 0]),
                },
            })
        
        return {
            **result,
            "result_count": result.get("gaps_identified", 0),
            "geojson": {
                "type": "FeatureCollection",
                "features": features,
            },
            "recommended_locations": [],
            "summary": {
                "gaps_identified": result.get("gaps_identified", 0),
                "total_affected_population": result.get("total_affected_population", 0),
                "gap_threshold_distance_km": max_hospital_distance_km,
                "min_population_threshold": min_population_threshold,
            },
        }

    def calculate_site_suitability_advanced(
        self, weights: dict[str, float] | None = None
    ) -> dict[str, Any]:
        """Calculate multi-factor site suitability for new facilities."""
        result = spatial_analysis.calculate_site_suitability(weights)
        
        return {
            **result,
            "result_count": result.get("total_candidates", 0),
            "geojson": result.get("geojson", {"type": "FeatureCollection", "features": []}),
            "recommended_locations": [
                {
                    "name": f"Candidate {idx + 1}",
                    "score": c.get("suitability_score"),
                    "coordinates": c.get("location", [0, 0]),
                    "factors": c.get("factors", {}),
                }
                for idx, c in enumerate(result.get("top_candidates", [])[:5])
            ],
            "summary": {
                "total_candidates": result.get("total_candidates", 0),
                "weights": result.get("weights", {}),
                "top_candidates": result.get("top_candidates", [])[:5],
            },
        }

    def get_layer_geojson(self, layer_name: str) -> dict[str, Any]:
        """Get GeoJSON for a specific layer."""
        records = _layer_records(layer_name)
        return _collection(layer_name, records)

    def explain_recommendation(self, context: dict[str, Any]) -> dict[str, Any]:
        selected = context.get("selected_location") or context.get("recommended_locations", [{}])[0]
        score = selected.get("score")
        reason = selected.get("reason", "No recommendation context was supplied.")
        explanation = f"This location was recommended because {reason}"
        if score is not None:
            explanation += f" and received a score of {score}."
        return {
            "explanation": explanation,
            "selected_tool": "explain_recommendation",
            "spatial_operation": "explanation",
            "result_count": 1 if selected else 0,
            "geojson": {"type": "FeatureCollection", "features": []},
            "recommended_locations": [selected] if selected else [],
            "summary": {"context": context},
            "sources": ["Derived from the previously returned suitability analysis"],
        }


def distance_km_between_records(left: Record, right: Record) -> float:
    return project_geom(left.geometry).distance(project_geom(right.geometry))


def _generate_candidate_points(count: int):
    points = []
    min_lon, min_lat, max_lon, max_lat = STUDY_AREA.bounds
    rows = max(2, int(round(count ** 0.5)) + 1)
    cols = max(2, rows)
    lon_step = (max_lon - min_lon) / (cols + 1)
    lat_step = (max_lat - min_lat) / (rows + 1)

    for row in range(1, rows + 1):
        for col in range(1, cols + 1):
            lon = min_lon + lon_step * col
            lat = min_lat + lat_step * row
            candidate = Point(lon, lat)
            if STUDY_AREA.contains(candidate):
                points.append(candidate)
    return points[:count]


def _normalized_distance_score(candidate, features: list[Record], *, reverse: bool, max_distance_km: float) -> float:
    if not features:
        return 0.0
    nearest = min((distance_km_between_records(Record("candidate", {}, candidate), feature) for feature in features), default=max_distance_km)
    clamped = max(0.0, min(1.0, nearest / max_distance_km))
    return clamped if reverse else 1.0 - clamped


def _normalized_population_score(candidate, population: list[Record]) -> float:
    if not population:
        return 0.0
    weighted = 0.0
    for feature in population:
        distance = distance_km_between_records(Record("candidate", {}, candidate), feature)
        density = float(feature.properties.get("density", 0))
        weighted += density / (1.0 + distance)
    max_weight = 18000.0
    return max(0.0, min(1.0, weighted / max_weight))


def _candidate_reason(population_score: float, road_score: float, gap_score: float, environmental_score: float) -> str:
    reasons = []
    if population_score >= 0.6:
        reasons.append("strong population coverage")
    if road_score >= 0.6:
        reasons.append("good road access")
    if gap_score >= 0.5:
        reasons.append("underserved healthcare area")
    if environmental_score >= 0.5:
        reasons.append("lower environmental conflict")
    return ", ".join(reasons) if reasons else "balanced multi-factor score"
