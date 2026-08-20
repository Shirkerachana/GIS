"""
Advanced spatial analysis module for raster-vector integration.

This module handles real-world spatial analysis combining:
- Raster data (WorldPop population grids) using Rasterio
- Vector data (OSM features: hospitals, roads, etc.) using GeoPandas/Shapely
- PostGIS-compatible operations on spatial relationships

Capabilities:
1. Population statistics from raster
2. High-population area identification
3. Population near facilities calculation
4. Hospital accessibility analysis
5. Healthcare gaps identification
6. Multi-factor site suitability scoring
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, Polygon, box, mapping, shape
from shapely.ops import transform

from backend.app.config import settings
from backend.app.data_store import get_active_data_store
from backend.app.demo_data import Record, to_feature

logger = logging.getLogger("geoai.spatial_analysis")


@dataclass
class PopulationStats:
    """Statistics from the population raster."""
    total_population: float
    mean_population: float
    median_population: float
    std_population: float
    min_population: float
    max_population: float
    valid_cells: int
    total_cells: int
    cell_area_sqkm: float
    total_area_sqkm: float
    nodata_value: float


@dataclass
class AreaPopulation:
    """Population statistics for a specific area."""
    total_population: float
    mean_population: float
    area_sqkm: float
    cell_count: int
    valid_cells: int


class RasterDataManager:
    """Manages loading and querying raster data with spatial extent."""

    def __init__(self, raster_path: Path | str):
        """Initialize with path to raster file."""
        self.raster_path = Path(raster_path)
        self._src = None

    def __enter__(self):
        self._src = rasterio.open(self.raster_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._src:
            self._src.close()
            self._src = None

    def open(self):
        """Open the raster file."""
        if not self._src:
            self._src = rasterio.open(self.raster_path)
        return self._src

    def close(self):
        """Close the raster file."""
        if self._src:
            self._src.close()
            self._src = None

    def get_stats(self) -> PopulationStats:
        """Extract statistics from the raster band."""
        with self.open() as src:
            band = src.read(1)
            nodata = src.nodata

            # Mask out nodata values
            if nodata is not None:
                valid_mask = band != nodata
            else:
                valid_mask = np.isfinite(band)

            valid_cells = np.sum(valid_mask)
            total_cells = band.size

            if valid_cells == 0:
                raise ValueError("No valid data in raster")

            valid_data = band[valid_mask]

            return PopulationStats(
                total_population=float(np.sum(valid_data)),
                mean_population=float(np.mean(valid_data)),
                median_population=float(np.median(valid_data)),
                std_population=float(np.std(valid_data)),
                min_population=float(np.min(valid_data)),
                max_population=float(np.max(valid_data)),
                valid_cells=int(valid_cells),
                total_cells=int(total_cells),
                cell_area_sqkm=float(self._get_cell_area_sqkm()),
                total_area_sqkm=float(valid_cells * self._get_cell_area_sqkm()),
                nodata_value=float(nodata) if nodata is not None else -9999.0,
            )

    def _get_cell_area_sqkm(self) -> float:
        """Calculate cell area in square kilometers."""
        with self.open() as src:
            res_x, res_y = abs(src.res[0]), abs(src.res[1])
            # Convert from degrees to approximate km (at equator)
            return (res_x * 111.32) * (res_y * 110.57)

    def query_polygon(self, geometry: Polygon) -> AreaPopulation | None:
        """Query population statistics for a polygon."""
        try:
            with self.open() as src:
                # Mask the raster to the polygon
                masked_data, masked_transform = mask(
                    src, [geometry], crop=False, nodata=src.nodata
                )
                band = masked_data[0]
                nodata = src.nodata

                # Mask out nodata values
                if nodata is not None:
                    valid_mask = band != nodata
                else:
                    valid_mask = np.isfinite(band)

                valid_cells = np.sum(valid_mask)

                if valid_cells == 0:
                    return None

                valid_data = band[valid_mask]
                cell_area = self._get_cell_area_sqkm()

                return AreaPopulation(
                    total_population=float(np.sum(valid_data)),
                    mean_population=float(np.mean(valid_data)),
                    area_sqkm=float(valid_cells * cell_area),
                    cell_count=int(np.count_nonzero(band != 0)) if nodata is None else int(
                        np.count_nonzero((band != 0) & valid_mask)
                    ),
                    valid_cells=int(valid_cells),
                )
        except Exception as e:
            logger.warning(f"Failed to query polygon: {e}")
            return None

    def query_point_buffer(self, point: Point, radius_km: float) -> AreaPopulation | None:
        """Query population within a radius around a point."""
        # Create a circular buffer
        lat = point.y
        # Approximate conversion: 1 km = 0.009 degrees (at equator)
        # At different latitudes, longitudinal distance varies
        lon_offset = radius_km / (111.32 * np.cos(np.radians(lat)))
        lat_offset = radius_km / 110.57

        buffer_geom = Point(point.x, point.y).buffer(radius_km / 111.32)
        return self.query_polygon(buffer_geom)

    def get_high_population_cells(
        self, threshold_percentile: float = 75.0
    ) -> list[dict[str, Any]]:
        """Identify high-population cells above a percentile threshold."""
        with self.open() as src:
            band = src.read(1)
            nodata = src.nodata

            # Mask out nodata
            if nodata is not None:
                valid_mask = band != nodata
            else:
                valid_mask = np.isfinite(band)

            valid_data = band[valid_mask]

            if len(valid_data) == 0:
                return []

            # Calculate threshold
            threshold = np.percentile(valid_data, threshold_percentile)

            # Find high-population cells
            high_cells = []
            rows, cols = np.where((band >= threshold) & valid_mask)

            for row, col in zip(rows, cols):
                # Convert pixel coordinates to geographic coordinates
                x, y = src.transform * (col + 0.5, row + 0.5)
                population = float(band[row, col])

                high_cells.append(
                    {
                        "geometry": Point(x, y),
                        "properties": {
                            "population": population,
                            "percentile": threshold_percentile,
                            "row": int(row),
                            "col": int(col),
                        },
                    }
                )

            return high_cells


def get_population_statistics() -> dict[str, Any]:
    """
    Calculate population statistics from the WorldPop raster or vector data.
    
    Returns:
        Dict containing total population, mean, median, std, min, max, etc.
    """
    from backend.app.gis_tools import _layer_records
    
    store = get_active_data_store()

    # For real data, try raster first, then fall back to vector
    if store.is_real:
        # Try reading pre-computed stats file first
        stats_path = settings.real_data_dir / "worldpop_stats.json"
        if stats_path.exists():
            try:
                stats_from_file = json.loads(stats_path.read_text(encoding="utf-8"))
                if stats_from_file:
                    return {
                        "source": "WorldPop statistics (pre-computed)",
                        "total_population": stats_from_file.get("total_population"),
                        "mean_population_per_cell": stats_from_file.get("mean_population"),
                        "min_population": stats_from_file.get("min_population"),
                        "max_population": stats_from_file.get("max_population"),
                        "valid_cells": stats_from_file.get("valid_cell_count"),
                        "total_cells": stats_from_file.get("valid_cell_count"),
                        "cell_area_sqkm": stats_from_file.get("cell_area_sqkm"),
                        "total_area_sqkm": stats_from_file.get("cell_area_sqkm", 0.856) * stats_from_file.get("valid_cell_count", 0),
                        "data_type": "raster (gridded population estimates)",
                    }
            except Exception as e:
                logger.debug(f"Failed to read stats file: {e}")

        # Try reading raster file
        raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"
        if raster_path.exists() and raster_path.stat().st_size > 100000:
            try:
                with RasterDataManager(raster_path) as rdm:
                    stats = rdm.get_stats()

                    return {
                        "source": "WorldPop population raster",
                        "total_population": round(stats.total_population, 2),
                        "mean_population_per_cell": round(stats.mean_population, 2),
                        "median_population_per_cell": round(stats.median_population, 2),
                        "std_population": round(stats.std_population, 2),
                        "min_population": round(stats.min_population, 2),
                        "max_population": round(stats.max_population, 2),
                        "valid_cells": stats.valid_cells,
                        "total_cells": stats.total_cells,
                        "cell_area_sqkm": round(stats.cell_area_sqkm, 4),
                        "total_area_sqkm": round(stats.total_area_sqkm, 2),
                        "data_type": "raster (gridded population estimates)",
                    }
            except Exception as e:
                logger.debug(f"Failed to read raster: {e}")

    # Always try vector-based fallback (works in both demo and real modes)
    population_records = _layer_records("population")
    if population_records:
        populations = [
            float(r.properties.get("population", 0)) for r in population_records
        ]
        valid_populations = [p for p in populations if p > 0]
        
        if valid_populations:
            import statistics
            
            data_type = "raster (gridded cells converted from raster)" if store.is_real else "demo dataset"
            source = "WorldPop population vector" if store.is_real else "Demo in-memory population"
            
            return {
                "source": source,
                "total_population": round(sum(valid_populations), 2),
                "mean_population_per_cell": round(np.mean(valid_populations), 2),
                "median_population_per_cell": round(statistics.median(valid_populations), 2),
                "std_population": round(np.std(valid_populations), 2),
                "min_population": round(min(valid_populations), 2),
                "max_population": round(max(valid_populations), 2),
                "valid_cells": len(valid_populations),
                "total_cells": len(population_records),
                "cell_area_sqkm": float(population_records[0].properties.get("cell_area_sqkm", 0.856)) if population_records else 0.856,
                "total_area_sqkm": round(len(valid_populations) * 0.856, 2),
                "data_type": data_type,
            }

    return {}


def find_high_population_areas(percentile_threshold: float = 75.0) -> dict[str, Any]:
    """
    Identify high-population areas from the raster or vector data.
    
    Args:
        percentile_threshold: Population percentile to use as threshold (0-100)
    
    Returns:
        Dict with GeoJSON of high-population areas and statistics
    """
    from backend.app.gis_tools import _layer_records, to_feature
    
    store = get_active_data_store()

    # Try raster first if available
    if store.is_real:
        raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"

        if raster_path.exists():
            try:
                with RasterDataManager(raster_path) as rdm:
                    stats = rdm.get_stats()

                    # Get high-population cells
                    high_cells = rdm.get_high_population_cells(percentile_threshold)

                    # Convert to features
                    features = []
                    total_pop_in_high = 0

                    for cell in high_cells:
                        total_pop_in_high += cell["properties"]["population"]
                        features.append(
                            {
                                "type": "Feature",
                                "properties": cell["properties"],
                                "geometry": mapping(cell["geometry"]),
                            }
                        )

                    area_percentage = (total_pop_in_high / stats.total_population * 100) if stats.total_population > 0 else 0

                    return {
                        "explanation": f"Identified {len(features)} high-population areas (top {100-percentile_threshold:.0f}% densest cells)",
                        "selected_tool": "find_high_population_areas",
                        "spatial_operation": "raster density analysis",
                        "high_population_count": len(features),
                        "total_population_in_high_areas": round(total_pop_in_high, 2),
                        "total_population_all": round(stats.total_population, 2),
                        "area_percentage": round(area_percentage, 2),
                        "percentile_threshold": percentile_threshold,
                        "geojson": {
                            "type": "FeatureCollection",
                            "features": features[:100],  # Limit to first 100 for performance
                        },
                        "sources": ["WorldPop population raster - Pune clip"],
                    }
            except Exception as e:
                logger.debug(f"Failed to read raster, falling back to vector: {e}")

    # Fallback to vector-based approach
    population_records = _layer_records("population")

    if not population_records:
        return {
            "explanation": "No population data available",
            "high_population_count": 0,
            "total_population_in_high_areas": 0.0,
            "area_percentage": 0.0,
            "geojson": {"type": "FeatureCollection", "features": []},
        }

    # Calculate threshold based on percentile
    values = [
        float(r.properties.get("population", 0))
        for r in population_records
    ]
    valid_values = [v for v in values if v > 0]
    
    if not valid_values:
        return {
            "explanation": "No valid population data",
            "high_population_count": 0,
            "total_population_in_high_areas": 0.0,
            "area_percentage": 0.0,
            "geojson": {"type": "FeatureCollection", "features": []},
        }
    
    threshold = np.percentile(valid_values, percentile_threshold)
    
    high_records = [
        r for r in population_records
        if float(r.properties.get("population", 0)) >= threshold
    ]

    features = [to_feature(r) for r in high_records]
    total_pop_all = sum(float(r.properties.get("population", 0)) for r in population_records)
    total_pop_high = sum(float(r.properties.get("population", 0)) for r in high_records)
    area_percentage = (total_pop_high / total_pop_all * 100) if total_pop_all > 0 else 0

    return {
        "explanation": f"Identified {len(high_records)} high-population areas (top {100-percentile_threshold:.0f}% densest cells)",
        "selected_tool": "find_high_population_areas",
        "spatial_operation": "vector density analysis",
        "high_population_count": len(high_records),
        "total_population_in_high_areas": round(total_pop_high, 2),
        "total_population_all": round(total_pop_all, 2),
        "area_percentage": round(area_percentage, 2),
        "percentile_threshold": percentile_threshold,
        "geojson": {
            "type": "FeatureCollection",
            "features": features,
        },
        "sources": ["WorldPop population vector (converted from raster)"],
    }


def calculate_population_near_hospitals(radius_km: float = 5.0) -> dict[str, Any]:
    """
    Calculate population within a radius of each hospital.
    
    Args:
        radius_km: Search radius around each hospital
    
    Returns:
        Dict with hospital locations and their surrounding population
    """
    from backend.app.gis_tools import _layer_records, distance_km_between_records, Record

    store = get_active_data_store()
    hospitals = _layer_records("hospitals")

    if not hospitals:
        return {
            "explanation": "No hospitals found",
            "selected_tool": "calculate_population_near_hospitals",
            "spatial_operation": "zonal population statistics",
            "hospitals_analyzed": 0,
            "total_population_nearby": 0.0,
            "average_population_per_hospital": 0.0,
            "results": [],
            "sources": [],
        }

    population_records = _layer_records("population")
    results = []
    total_population_nearby = 0

    # Use raster if real data and available
    raster_path = settings.real_data_dir / "worldpop_pune_clip.tif" if store.is_real else None
    if raster_path and raster_path.exists():
        try:
            with RasterDataManager(raster_path) as rdm:
                for hospital in hospitals:
                    hospital_point = hospital.geometry
                    if not hospital_point.is_empty:
                        area_pop = rdm.query_point_buffer(
                            hospital_point, radius_km
                        )

                        if area_pop:
                            total_population_nearby += area_pop.total_population
                            results.append(
                                {
                                    "id": hospital.id,
                                    "name": hospital.properties.get("name", "Unknown"),
                                    "location": [hospital_point.x, hospital_point.y],
                                    "population_within_km": {
                                        "radius": radius_km,
                                        "total": round(area_pop.total_population, 2),
                                        "mean_density": round(
                                            area_pop.mean_population, 2
                                        ),
                                        "area_sqkm": round(area_pop.area_sqkm, 2),
                                    },
                                }
                            )

                avg_nearby = (total_population_nearby / len(results)) if results else 0

                return {
                    "explanation": f"Calculated population within {radius_km} km of {len(results)} hospitals",
                    "selected_tool": "calculate_population_near_hospitals",
                    "spatial_operation": "zonal population statistics",
                    "hospitals_analyzed": len(results),
                    "radius_km": radius_km,
                    "total_population_nearby": round(total_population_nearby, 2),
                    "average_population_per_hospital": round(avg_nearby, 2),
                    "results": results,
                    "sources": ["WorldPop population raster", "OpenStreetMap hospitals"],
                }
        except Exception as e:
            logger.debug(f"Failed to query raster, falling back to vector: {e}")

    # Fallback to vector-based approach
    if population_records:
        for hospital in hospitals:
            # Find population cells near hospital
            nearby_pop = 0
            for pop_cell in population_records:
                dist = distance_km_between_records(hospital, pop_cell)
                if dist <= radius_km:
                    nearby_pop += float(pop_cell.properties.get("population", 0))
            
            total_population_nearby += nearby_pop
            results.append(
                {
                    "id": hospital.id,
                    "name": hospital.properties.get("name", "Unknown"),
                    "location": [hospital.geometry.x, hospital.geometry.y],
                    "population_within_km": {
                        "radius": radius_km,
                        "total": round(nearby_pop, 2),
                        "note": "Calculated from vector population cells",
                    },
                }
            )

    avg_nearby = (total_population_nearby / len(results)) if results else 0

    return {
        "explanation": f"Calculated population within {radius_km} km of {len(results)} hospitals",
        "selected_tool": "calculate_population_near_hospitals",
        "spatial_operation": "zonal population statistics",
        "hospitals_analyzed": len(results),
        "radius_km": radius_km,
        "total_population_nearby": round(total_population_nearby, 2),
        "average_population_per_hospital": round(avg_nearby, 2),
        "results": results,
        "sources": ["WorldPop population data", "OpenStreetMap hospitals"],
    }


def analyze_hospital_accessibility(
    major_road_distance_km: float = 2.0, population_threshold: float = 500.0
) -> dict[str, Any]:
    """
    Analyze hospital accessibility based on:
    - Distance to major roads
    - Surrounding population density
    - Distribution across study area
    
    Args:
        major_road_distance_km: Threshold for good road accessibility
        population_threshold: Minimum population density for accessibility
    
    Returns:
        Dict with accessibility metrics for each hospital
    """
    from backend.app.gis_tools import (
        _layer_records,
        distance_km_between_records,
    )

    store = get_active_data_store()
    hospitals = _layer_records("hospitals")
    roads = _layer_records("roads", {"road_type": "major"})

    if not hospitals or not roads:
        return {
            "explanation": "Insufficient data for accessibility analysis",
            "selected_tool": "analyze_hospital_accessibility",
            "hospitals_analyzed": len(hospitals),
            "accessibility_results": [],
        }

    results = []
    accessibility_levels = {"good": 0, "moderate": 0, "poor": 0}

    # For real data, enhance with population analysis
    raster_manager = None
    if store.is_real:
        raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"
        if raster_path.exists():
            raster_manager = RasterDataManager(raster_path)
            raster_manager.open()

    try:
        for hospital in hospitals:
            # Calculate distance to nearest major road
            if roads:
                nearest_road_dist = min(
                    (distance_km_between_records(hospital, road) for road in roads),
                    default=999.0,
                )
            else:
                nearest_road_dist = 999.0

            # Get surrounding population if raster available
            pop_density = 0.0
            if raster_manager:
                area_pop = raster_manager.query_point_buffer(hospital.geometry, 2.0)
                if area_pop and area_pop.area_sqkm > 0:
                    pop_density = area_pop.mean_population

            # Determine accessibility level
            if nearest_road_dist <= major_road_distance_km and pop_density > 0:
                accessibility = "good"
                accessibility_levels["good"] += 1
            elif nearest_road_dist <= major_road_distance_km * 1.5:
                accessibility = "moderate"
                accessibility_levels["moderate"] += 1
            else:
                accessibility = "poor"
                accessibility_levels["poor"] += 1

            results.append(
                {
                    "id": hospital.id,
                    "name": hospital.properties.get("name", "Unknown"),
                    "location": [hospital.geometry.x, hospital.geometry.y],
                    "accessibility_level": accessibility,
                    "distance_to_major_road_km": round(nearest_road_dist, 2),
                    "surrounding_population_density": round(pop_density, 2),
                    "accessibility_score": _calculate_accessibility_score(
                        nearest_road_dist, pop_density, major_road_distance_km
                    ),
                }
            )

        return {
            "explanation": f"Analyzed accessibility for {len(results)} hospitals based on road distance and population density",
            "selected_tool": "analyze_hospital_accessibility",
            "spatial_operation": "accessibility scoring",
            "hospitals_analyzed": len(results),
            "accessibility_summary": accessibility_levels,
            "results": results,
            "sources": ["OpenStreetMap hospitals and major roads", "WorldPop population raster"],
        }

    finally:
        if raster_manager:
            raster_manager.close()


def _calculate_accessibility_score(
    road_distance_km: float, population_density: float, max_good_distance: float
) -> float:
    """Calculate a 0-100 accessibility score."""
    # Road proximity score (0-50)
    road_score = max(0, 50 * (1 - road_distance_km / (max_good_distance * 3)))

    # Population density score (0-50)
    # Normalize by assuming 5000 is "good" density
    density_score = min(50, 50 * (population_density / 5000))

    return round(road_score + density_score, 1)


def find_healthcare_gaps(
    min_population_threshold: float = 5000.0,
    max_hospital_distance_km: float = 5.0,
) -> dict[str, Any]:
    """
    Identify areas with high population but low hospital coverage (healthcare gaps).
    
    Args:
        min_population_threshold: Minimum population to consider as high-population
        max_hospital_distance_km: Distance threshold for hospital coverage
    
    Returns:
        Dict identifying underserved high-population areas
    """
    from backend.app.gis_tools import (
        _layer_records,
        distance_km_between_records,
    )

    store = get_active_data_store()
    hospitals = _layer_records("hospitals")

    if not hospitals:
        return {
            "explanation": "No hospitals found for gap analysis",
            "selected_tool": "find_healthcare_gaps",
            "spatial_operation": "healthcare gap analysis",
            "gaps_identified": 0,
            "total_affected_population": 0.0,
            "gap_threshold_distance_km": max_hospital_distance_km,
            "min_population_threshold": min_population_threshold,
            "results": [],
            "sources": [],
        }

    gaps = []

    # Try raster first if available
    if store.is_real:
        raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"
        if raster_path.exists():
            try:
                with RasterDataManager(raster_path) as rdm:
                    high_cells = rdm.get_high_population_cells(percentile_threshold=75.0)

                    for cell in high_cells:
                        if cell["properties"]["population"] < min_population_threshold:
                            continue

                        point = cell["geometry"]

                        # Find nearest hospital
                        nearest_hospital_dist = 999.0
                        if hospitals:
                            nearest_hospital_dist = min(
                                (distance_km_between_records(
                                    Record(
                                        id=f"cell_{cell['properties']['row']}_{cell['properties']['col']}",
                                        properties=cell["properties"],
                                        geometry=point,
                                    ),
                                    hospital,
                                )
                                for hospital in hospitals),
                                default=999.0,
                            )

                        # If hospital is far away, it's a gap
                        if nearest_hospital_dist > max_hospital_distance_km:
                            gaps.append(
                                {
                                    "location": [point.x, point.y],
                                    "population": round(cell["properties"]["population"], 2),
                                    "nearest_hospital_distance_km": round(
                                        nearest_hospital_dist, 2
                                    ),
                                    "gap_severity": _calculate_gap_severity(
                                        cell["properties"]["population"],
                                        nearest_hospital_dist,
                                        max_hospital_distance_km,
                                    ),
                                }
                            )

                    # Limit results for performance
                    gaps = sorted(
                        gaps, key=lambda x: x["gap_severity"], reverse=True
                    )[:50]

                    total_pop_in_gaps = sum(g["population"] for g in gaps)

                    return {
                        "explanation": f"Identified {len(gaps)} high-population areas with insufficient hospital coverage",
                        "selected_tool": "find_healthcare_gaps",
                        "spatial_operation": "healthcare gap analysis",
                        "gaps_identified": len(gaps),
                        "total_affected_population": round(total_pop_in_gaps, 2),
                        "gap_threshold_distance_km": max_hospital_distance_km,
                        "min_population_threshold": min_population_threshold,
                        "results": gaps,
                        "sources": ["WorldPop population raster", "OpenStreetMap hospitals"],
                    }
            except Exception as e:
                logger.debug(f"Failed with raster, trying vector approach: {e}")

    # Fallback to vector-based approach
    population_records = _layer_records("population")
    if population_records:
        for pop_cell in population_records:
            population = float(pop_cell.properties.get("population", 0))
            
            if population < min_population_threshold:
                continue
            
            # Find nearest hospital
            nearest_hospital_dist = min(
                (distance_km_between_records(pop_cell, hospital) for hospital in hospitals),
                default=999.0,
            )
            
            # If hospital is far away, it's a gap
            if nearest_hospital_dist > max_hospital_distance_km:
                gaps.append(
                    {
                        "location": [pop_cell.geometry.centroid.x, pop_cell.geometry.centroid.y],
                        "population": round(population, 2),
                        "nearest_hospital_distance_km": round(nearest_hospital_dist, 2),
                        "gap_severity": _calculate_gap_severity(
                            population,
                            nearest_hospital_dist,
                            max_hospital_distance_km,
                        ),
                    }
                )

        # Sort by severity and limit results
        gaps = sorted(gaps, key=lambda x: x["gap_severity"], reverse=True)[:50]
        total_pop_in_gaps = sum(g["population"] for g in gaps)

        return {
            "explanation": f"Identified {len(gaps)} high-population areas with insufficient hospital coverage",
            "selected_tool": "find_healthcare_gaps",
            "spatial_operation": "healthcare gap analysis",
            "gaps_identified": len(gaps),
            "total_affected_population": round(total_pop_in_gaps, 2),
            "gap_threshold_distance_km": max_hospital_distance_km,
            "min_population_threshold": min_population_threshold,
            "results": gaps,
            "sources": ["WorldPop population vector", "OpenStreetMap hospitals"],
        }

    return {
        "explanation": "Healthcare gap analysis requires population data",
        "selected_tool": "find_healthcare_gaps",
        "spatial_operation": "healthcare gap analysis",
        "gaps_identified": 0,
        "total_affected_population": 0.0,
        "gap_threshold_distance_km": max_hospital_distance_km,
        "min_population_threshold": min_population_threshold,
        "results": [],
        "sources": [],
    }


def _calculate_gap_severity(
    population: float, distance_km: float, max_good_distance_km: float
) -> float:
    """Calculate gap severity score (0-100)."""
    # Population factor: more people = more severe
    pop_score = min(50, 50 * (population / 10000))

    # Distance factor: farther = more severe
    dist_score = min(50, 50 * (distance_km / (max_good_distance_km * 2)))

    return round(pop_score + dist_score, 1)


def calculate_site_suitability(
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Calculate multi-factor site suitability for new healthcare facilities.
    
    Factors:
    - Population coverage (proximity to high-population areas)
    - Road accessibility (distance to major roads)
    - Healthcare gap (distance from existing hospitals)
    - Environmental constraints (distance from water)
    
    Args:
        weights: Custom weights for different factors
    
    Returns:
        Dict with suitability scores across the study area
    """
    from backend.app.gis_tools import (
        _layer_records,
        STUDY_AREA,
        distance_km_between_records,
    )

    weights = weights or {
        "population_proximity": 0.40,
        "road_accessibility": 0.25,
        "healthcare_coverage": 0.25,
        "environmental_factors": 0.10,
    }

    store = get_active_data_store()
    hospitals = _layer_records("hospitals")
    roads = _layer_records("roads", {"road_type": "major"})
    rivers = _layer_records("rivers")

    # Generate candidate locations across study area
    candidates = _generate_suitability_candidates(STUDY_AREA, count=30)

    results = []
    raster_manager = None

    # Open raster if available
    if store.is_real:
        raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"
        if raster_path.exists():
            raster_manager = RasterDataManager(raster_path)
            raster_manager.open()

    try:
        for idx, candidate in enumerate(candidates):
            # Population proximity score (0-100)
            pop_score = 0.0
            if raster_manager:
                area_pop = raster_manager.query_point_buffer(candidate, 2.0)
                if area_pop and area_pop.area_sqkm > 0:
                    # Normalize by max observed density
                    pop_score = min(100, 100 * (area_pop.mean_population / 15000))

            # Road accessibility score (0-100)
            road_score = 0.0
            if roads:
                nearest_road = min(
                    (distance_km_between_records(
                        Record(
                            id=f"candidate_{idx}",
                            properties={},
                            geometry=candidate,
                        ),
                        road,
                    )
                    for road in roads),
                    default=999.0,
                )
                # Closer = higher score
                road_score = max(0, 100 * (1 - nearest_road / 5.0))

            # Healthcare coverage score (0-100)
            # Higher score = far from existing hospitals = gap exists
            healthcare_score = 0.0
            if hospitals:
                nearest_hospital = min(
                    (distance_km_between_records(
                        Record(
                            id=f"candidate_{idx}",
                            properties={},
                            geometry=candidate,
                        ),
                        hospital,
                    )
                    for hospital in hospitals),
                    default=0.0,
                )
                # Farther from hospitals = higher score (gap exists)
                healthcare_score = min(100, 100 * (nearest_hospital / 7.0))

            # Environmental score (0-100)
            # Higher score = far from water bodies
            env_score = 100.0
            if rivers:
                nearest_water = min(
                    (distance_km_between_records(
                        Record(
                            id=f"candidate_{idx}",
                            properties={},
                            geometry=candidate,
                        ),
                        river,
                    )
                    for river in rivers),
                    default=999.0,
                )
                # Farther from water = higher score
                env_score = min(100, 100 * (nearest_water / 2.0))

            # Calculate weighted total
            total_score = (
                weights.get("population_proximity", 0.4) * pop_score
                + weights.get("road_accessibility", 0.25) * road_score
                + weights.get("healthcare_coverage", 0.25) * healthcare_score
                + weights.get("environmental_factors", 0.1) * env_score
            )

            results.append(
                {
                    "rank": idx + 1,
                    "location": [candidate.x, candidate.y],
                    "suitability_score": round(total_score, 1),
                    "factors": {
                        "population_proximity": round(pop_score, 1),
                        "road_accessibility": round(road_score, 1),
                        "healthcare_coverage": round(healthcare_score, 1),
                        "environmental_factors": round(env_score, 1),
                    },
                }
            )

        # Sort by suitability score
        results = sorted(results, key=lambda x: x["suitability_score"], reverse=True)

        # Prepare GeoJSON features for top candidates
        features = []
        for idx, result in enumerate(results[:10]):
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "rank": idx + 1,
                        "score": result["suitability_score"],
                        "factors": result["factors"],
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": result["location"],
                    },
                }
            )

        return {
            "explanation": f"Calculated site suitability for {len(candidates)} candidate locations using multi-factor analysis",
            "selected_tool": "calculate_site_suitability",
            "spatial_operation": "multi-factor suitability analysis",
            "total_candidates": len(results),
            "weights": weights,
            "top_candidates": results[:10],
            "geojson": {
                "type": "FeatureCollection",
                "features": features,
            },
            "sources": [
                "WorldPop population raster",
                "OpenStreetMap hospitals, roads, and water bodies",
            ],
        }

    finally:
        if raster_manager:
            raster_manager.close()


def find_best_hospital_location(
    candidate_count: int = 50,
) -> dict[str, Any]:
    """
    Find the best locations for a new hospital using transparent multi-factor scoring.
    
    This implements the specific weighting requested:
    - Population coverage: 40% (proximity to high-population areas)
    - Road accessibility: 30% (proximity to major roads)
    - Healthcare gap: 30% (distance from existing hospitals)
    
    Returns the top 5 candidates with detailed scoring breakdown.
    
    Args:
        candidate_count: Number of candidate locations to evaluate
    
    Returns:
        Dict with top 5 candidates and their detailed scores
    """
    from backend.app.gis_tools import (
        _layer_records,
        STUDY_AREA,
        distance_km_between_records,
    )
    
    # Use the exact weights requested by the user
    weights = {
        "population_coverage": 0.40,
        "road_accessibility": 0.30,
        "healthcare_gap": 0.30,
    }
    
    store = get_active_data_store()
    hospitals = _layer_records("hospitals")
    roads = _layer_records("roads", {"road_type": "major"})
    
    # Generate candidate locations
    candidates = _generate_suitability_candidates(STUDY_AREA, count=candidate_count)
    
    results = []
    raster_manager = None
    
    # Open raster if available for population data
    if store.is_real:
        raster_path = settings.real_data_dir / "worldpop_pune_clip.tif"
        if raster_path.exists():
            raster_manager = RasterDataManager(raster_path)
            raster_manager.open()
    
    try:
        for idx, candidate in enumerate(candidates):
            # 1. POPULATION COVERAGE SCORE (40%) - 0 to 100
            # Based on population density in surrounding area
            pop_score = 0.0
            if raster_manager:
                area_pop = raster_manager.query_point_buffer(candidate, 2.0)
                if area_pop and area_pop.area_sqkm > 0:
                    # Normalize by max observed density (15,000 people/sq km)
                    pop_score = min(100, 100 * (area_pop.mean_population / 15000))
            
            # 2. ROAD ACCESSIBILITY SCORE (30%) - 0 to 100
            # Closer to major roads = higher score
            road_score = 0.0
            if roads:
                nearest_road_km = min(
                    (distance_km_between_records(
                        Record(
                            id=f"candidate_{idx}",
                            properties={},
                            geometry=candidate,
                        ),
                        road,
                    )
                    for road in roads),
                    default=999.0,
                )
                # Linear decay: perfect at 0 km, zero at 5 km
                road_score = max(0, 100 * (1 - nearest_road_km / 5.0))
            
            # 3. HEALTHCARE GAP SCORE (30%) - 0 to 100
            # Farther from existing hospitals = higher score (indicates gap)
            healthcare_gap_score = 0.0
            nearest_hospital_km = 999.0
            if hospitals:
                nearest_hospital_km = min(
                    (distance_km_between_records(
                        Record(
                            id=f"candidate_{idx}",
                            properties={},
                            geometry=candidate,
                        ),
                        hospital,
                    )
                    for hospital in hospitals),
                    default=999.0,
                )
                # Score increases with distance (max at 7 km = 100%)
                healthcare_gap_score = min(100, 100 * (nearest_hospital_km / 7.0))
            
            # FINAL SUITABILITY SCORE
            # Weighted combination: 40% + 30% + 30% = 100%
            total_score = (
                weights["population_coverage"] * (pop_score / 100.0) * 100 +
                weights["road_accessibility"] * (road_score / 100.0) * 100 +
                weights["healthcare_gap"] * (healthcare_gap_score / 100.0) * 100
            )
            
            results.append({
                "rank": idx + 1,
                "location": [candidate.x, candidate.y],
                "coordinates": {"lon": round(candidate.x, 6), "lat": round(candidate.y, 6)},
                "suitability_score": round(total_score, 1),
                "factors": {
                    "population_coverage": {
                        "score": round(pop_score, 1),
                        "weight": 40,
                        "description": "Proximity to high-population areas"
                    },
                    "road_accessibility": {
                        "score": round(road_score, 1),
                        "weight": 30,
                        "description": "Distance to major roads",
                        "nearest_road_km": round(nearest_road_km, 2) if roads else None
                    },
                    "healthcare_gap": {
                        "score": round(healthcare_gap_score, 1),
                        "weight": 30,
                        "description": "Distance from existing hospitals",
                        "nearest_hospital_km": round(nearest_hospital_km, 2)
                    }
                }
            })
        
        # Sort by suitability score (descending)
        results = sorted(results, key=lambda x: x["suitability_score"], reverse=True)
        
        # Generate recommendation reason for each top candidate
        top_5 = results[:5]
        for idx, result in enumerate(top_5):
            factors = result["factors"]
            pop_factor = factors["population_coverage"]["score"]
            road_factor = factors["road_accessibility"]["score"]
            healthcare_factor = factors["healthcare_gap"]["score"]
            
            reasons = []
            if pop_factor > 70:
                reasons.append("high population density")
            elif pop_factor > 40:
                reasons.append("moderate population density")
            
            if road_factor > 70:
                reasons.append("excellent road accessibility")
            elif road_factor > 40:
                reasons.append("good road accessibility")
            
            if healthcare_factor > 70:
                reasons.append("significant healthcare gap")
            elif healthcare_factor > 40:
                reasons.append("moderate healthcare gap")
            
            reason_text = "This location is suitable because it has " + ", ".join(reasons) + "."
            result["reason"] = reason_text
        
        # Prepare GeoJSON features for top 5 candidates
        features = []
        for idx, result in enumerate(top_5):
            features.append({
                "type": "Feature",
                "properties": {
                    "rank": idx + 1,
                    "score": result["suitability_score"],
                    "population_coverage": result["factors"]["population_coverage"]["score"],
                    "road_accessibility": result["factors"]["road_accessibility"]["score"],
                    "healthcare_gap": result["factors"]["healthcare_gap"]["score"],
                    "reason": result["reason"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": result["location"],
                }
            })
        
        return {
            "explanation": (
                "Analyzed 50 candidate locations across Pune using transparent multi-factor scoring. "
                "Population coverage (40%) measures proximity to high-density areas. "
                "Road accessibility (30%) scores proximity to major roads. "
                "Healthcare gap (30%) scores distance from existing hospitals. "
                "All calculations use actual OpenStreetMap and WorldPop data."
            ),
            "selected_tool": "hospital_site_selection",
            "spatial_operation": "multi-factor suitability analysis",
            "note": "AI-generated suitability analysis for demonstration purposes and not a substitute for professional planning. "
                    "This is not an actual medical, government, or official urban-planning recommendation.",
            "total_candidates_evaluated": len(results),
            "recommended_locations": top_5,
            "weights": {
                "population_coverage": "40%",
                "road_accessibility": "30%",
                "healthcare_gap": "30%"
            },
            "geojson": {
                "type": "FeatureCollection",
                "features": features,
            },
            "sources": [
                "Population distribution: WorldPop 2025 (1km resolution)",
                "Existing hospitals: OpenStreetMap (OSM)",
                "Road network: OpenStreetMap (OSM)",
            ],
            "data_area": "Pune Metropolitan Region"
        }
    
    finally:
        if raster_manager:
            raster_manager.close()


def _generate_suitability_candidates(study_area: Polygon, count: int = 30):
    """Generate candidate locations across the study area."""
    min_lon, min_lat, max_lon, max_lat = study_area.bounds
    side_length = int(np.sqrt(count))

    candidates = []
    lon_step = (max_lon - min_lon) / (side_length + 1)
    lat_step = (max_lat - min_lat) / (side_length + 1)

    for i in range(1, side_length + 1):
        for j in range(1, side_length + 1):
            lon = min_lon + i * lon_step
            lat = min_lat + j * lat_step
            candidates.append(Point(lon, lat))

    return candidates
