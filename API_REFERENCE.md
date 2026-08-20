# GeoAI Spatial Analysis - Quick Reference Guide

## REST API Endpoints

### 1. Get Population Statistics
```bash
GET /api/analysis/population-statistics
```

**Response**:
```json
{
  "source": "WorldPop population vector",
  "total_population": 106000,
  "mean_population_per_cell": 35333.33,
  "median_population_per_cell": 52000,
  "min_population": 0,
  "max_population": 106000,
  "valid_cells": 3,
  "total_cells": 3,
  "cell_area_sqkm": 0.856,
  "total_area_sqkm": 2.57
}
```

---

### 2. Find High-Population Areas
```bash
GET /api/analysis/high-population-areas?percentile=75
```

**Parameters**:
- `percentile` (float, default: 75.0): Population percentile threshold (0-100)

**Response**:
```json
{
  "explanation": "Identified 1 high-population areas (top 25% densest cells)",
  "selected_tool": "find_high_population_areas",
  "spatial_operation": "raster density analysis",
  "high_population_count": 1,
  "total_population_in_high_areas": 52000,
  "area_percentage": 49.1,
  "geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "population": 52000,
          "percentile": 75
        },
        "geometry": {...}
      }
    ]
  }
}
```

---

### 3. Calculate Population Near Hospitals
```bash
POST /api/analysis/population-near-hospitals

{
  "distance_km": 5.0
}
```

**Parameters**:
- `distance_km` (float, default: 5.0): Search radius around hospitals

**Response**:
```json
{
  "explanation": "Calculated population within 5.0 km of 5 hospitals",
  "hospitals_analyzed": 5,
  "radius_km": 5.0,
  "total_population_nearby": 457000,
  "average_population_per_hospital": 91400,
  "results": [
    {
      "id": "hosp_1",
      "name": "Sahyadri Hospital",
      "location": [73.8385, 18.5167],
      "population_within_km": {
        "radius": 5.0,
        "total": 106000,
        "mean_density": 35333.33
      }
    }
  ]
}
```

---

### 4. Analyze Hospital Accessibility
```bash
GET /api/analysis/hospital-accessibility?major_road_distance_km=2.0&population_threshold=500
```

**Parameters**:
- `major_road_distance_km` (float, default: 2.0): Threshold for good road access
- `population_threshold` (float, default: 500.0): Minimum population density

**Response**:
```json
{
  "explanation": "Analyzed accessibility for 5 hospitals...",
  "hospitals_analyzed": 5,
  "accessibility_summary": {
    "good": 0,
    "moderate": 5,
    "poor": 0
  },
  "results": [
    {
      "id": "hosp_1",
      "name": "Sahyadri Hospital",
      "location": [73.8385, 18.5167],
      "accessibility_level": "moderate",
      "distance_to_major_road_km": 1.48,
      "surrounding_population_density": 0.0,
      "accessibility_score": 37.7
    }
  ]
}
```

---

### 5. Find Healthcare Gaps
```bash
GET /api/analysis/healthcare-gaps?min_population_threshold=5000&max_hospital_distance_km=5
```

**Parameters**:
- `min_population_threshold` (float, default: 5000.0): Minimum population to flag as gap
- `max_hospital_distance_km` (float, default: 5.0): Distance threshold for coverage

**Response**:
```json
{
  "explanation": "Identified 0 high-population areas with insufficient hospital coverage",
  "gaps_identified": 0,
  "total_affected_population": 0,
  "gap_threshold_distance_km": 5.0,
  "min_population_threshold": 5000.0,
  "results": []
}
```

---

### 6. Calculate Site Suitability
```bash
POST /api/analysis/site-suitability

{
  "weights": {
    "population_proximity": 0.4,
    "road_accessibility": 0.25,
    "healthcare_coverage": 0.25,
    "environmental_factors": 0.1
  }
}
```

**Parameters**:
- `weights` (object, optional): Custom factor weights
  - Sum should equal 1.0
  - Defaults: population 0.4, roads 0.25, healthcare 0.25, environment 0.1

**Response**:
```json
{
  "explanation": "Calculated site suitability for 25 candidate locations...",
  "total_candidates": 25,
  "top_candidates": [
    {
      "rank": 1,
      "location": [73.908, 18.495],
      "suitability_score": 53.9,
      "factors": {
        "population_proximity": 0.0,
        "road_accessibility": 98.6,
        "healthcare_coverage": 76.9,
        "environmental_factors": 100
      }
    }
  ],
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  }
}
```

---

## Usage Examples

### Python (Direct Function Calls)
```python
from backend.app.gis_tools import GISService
from backend.app.data_store import get_active_data_store

store = get_active_data_store()
service = GISService(demo_mode=not store.is_real)

# Get population statistics
stats = service.get_population_statistics()
print(f"Total population: {stats['summary']['total_population']}")

# Find high-population areas
high_pop = service.find_high_population_areas_raster(percentile=75.0)
print(f"High-population count: {high_pop['result_count']}")

# Calculate population near hospitals
from backend.app.models import SpatialRequest
request = SpatialRequest(
    target_layer="hospitals",
    distance_km=5.0
)
result = service.calculate_population_near_hospitals(5.0)
print(f"Hospitals with population: {result['result_count']}")
```

### cURL (REST API)
```bash
# Get population statistics
curl -X GET "http://localhost:8000/api/analysis/population-statistics"

# Find high-population areas
curl -X GET "http://localhost:8000/api/analysis/high-population-areas?percentile=75"

# Calculate population near hospitals
curl -X POST "http://localhost:8000/api/analysis/population-near-hospitals" \
  -H "Content-Type: application/json" \
  -d '{"distance_km": 5.0}'

# Analyze hospital accessibility
curl -X GET "http://localhost:8000/api/analysis/hospital-accessibility?major_road_distance_km=2.0"

# Find healthcare gaps
curl -X GET "http://localhost:8000/api/analysis/healthcare-gaps?max_hospital_distance_km=5"

# Calculate site suitability
curl -X POST "http://localhost:8000/api/analysis/site-suitability" \
  -H "Content-Type: application/json" \
  -d '{
    "weights": {
      "population_proximity": 0.4,
      "road_accessibility": 0.25,
      "healthcare_coverage": 0.25,
      "environmental_factors": 0.1
    }
  }'
```

### JavaScript/Frontend
```javascript
// Get population statistics
const stats = await fetch('/api/analysis/population-statistics')
  .then(r => r.json());
console.log(`Total population: ${stats.summary.total_population}`);

// Find high-population areas
const highPop = await fetch('/api/analysis/high-population-areas?percentile=75')
  .then(r => r.json());
console.log(`High-population areas: ${highPop.result_count}`);

// Calculate site suitability with custom weights
const suitability = await fetch('/api/analysis/site-suitability', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    weights: {
      population_proximity: 0.5,
      road_accessibility: 0.25,
      healthcare_coverage: 0.2,
      environmental_factors: 0.05
    }
  })
}).then(r => r.json());

// Visualize results on map
const geoJson = suitability.geojson;
map.addLayer({
  id: 'suitability-candidates',
  type: 'circle',
  source: { type: 'geojson', data: geoJson },
  paint: {
    'circle-radius': 8,
    'circle-color': '#ff8c00',
    'circle-opacity': 0.7
  }
});
```

---

## Data Characteristics

### Demo Mode (Default)
- **Population Data**: 3 cells (52,000 total)
- **Study Area**: Small demonstration polygons
- **Hospitals**: 5 facilities with sample locations
- **Purpose**: Testing and development

### Real Mode
- **Population Data**: 896 cells (4,599,676 total)
- **Study Area**: Pune, Maharashtra, India (~768 km²)
- **Hospitals**: Real OSM hospital locations
- **Source**: WorldPop 2025 + OpenStreetMap

### Switching Data Modes
```bash
# Set environment variable before running
export DATA_MODE=real
python -m uvicorn backend.app.main:app

# Or in .env file
DATA_MODE=real
USE_DEMO_DATA=false
```

---

## Performance Tips

1. **High-Population Areas**: Use reasonable percentile thresholds (50-90%)
2. **Site Suitability**: 25-50 candidates provide good balance
3. **Healthcare Gaps**: High min_population_threshold reduces results
4. **Caching**: Results can be cached for repeated queries
5. **Visualization**: Limit GeoJSON features for web mapping (~500 features)

---

## Troubleshooting

### No data returned
- Verify data mode setting (demo vs. real)
- Check that data files exist in `data/processed/real/`
- Ensure population layer is available

### Slow performance
- Reduce candidate count in site suitability
- Use higher percentile threshold for high-population areas
- Limit results returned from GeoJSON features

### Empty results
- Check threshold parameters
- Verify reference layers have data (hospitals, roads, rivers)
- Try demo mode for immediate results

---

## References

- **WorldPop**: https://www.worldpop.org/
- **OpenStreetMap**: https://www.openstreetmap.org/
- **Rasterio Documentation**: https://rasterio.readthedocs.io/
- **Shapely Documentation**: https://shapely.readthedocs.io/
- **Technical Details**: See `SPATIAL_ANALYSIS_IMPLEMENTATION.md`

---

**Last Updated**: August 18, 2026
**Status**: Production Ready
