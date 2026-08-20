# GeoAI Assistant - Spatial Analysis Implementation

## Overview

This document describes the comprehensive spatial analysis capabilities implemented for the GeoAI Assistant, combining raster (WorldPop population) and vector (OpenStreetMap) data processing.

## Architecture

### Core Components

#### 1. **spatial_analysis.py** - Advanced Spatial Analysis Module
A new Python module providing real-world raster-vector integration using:
- **Rasterio**: For gridded population data processing
- **Shapely**: For vector geometry operations
- **NumPy**: For efficient numerical computations on raster bands

#### 2. **gis_tools.py** - Enhanced GIS Service
Updated with new methods wrapping spatial_analysis functions:
- Integration with existing GISService class
- Standardized result formatting (GeoJSON + summary statistics)
- Fallback strategies for demo mode

#### 3. **main.py** - New REST API Endpoints
Six new endpoints providing HTTP access to spatial analysis functions

## Implemented Capabilities

### 1. **Get Population Statistics** ✓
**Function**: `get_population_statistics()`
**Endpoint**: `GET /api/analysis/population-statistics`

Retrieves comprehensive statistics from the WorldPop raster:
- Total population across study area
- Mean, median, and standard deviation of population density
- Min/max population values
- Valid cell count and total area coverage
- Cell resolution and area calculations

**Real Data Source**: WorldPop 1km resolution gridded population estimates
**Actual Values** (Pune region):
- Total Population: **4,599,676** people
- Mean Density: **5,133.57** per cell
- Max Density: **14,857.85** per cell
- Study Area: ~768 km² (896 valid cells × 0.86 km²/cell)

### 2. **Find High-Population Areas** ✓
**Function**: `find_high_population_areas(percentile_threshold=75.0)`
**Endpoint**: `GET /api/analysis/high-population-areas?percentile=75`

Identifies densely populated grid cells using percentile-based thresholding:
- Parameterizable percentile threshold (default: top 25%)
- Returns cell-level population estimates
- Provides area percentage and total affected population
- GeoJSON output for spatial visualization

**Analysis Type**: Raster density analysis
**Use Case**: Urban planning, resource allocation prioritization

### 3. **Calculate Population Near Hospitals** ✓
**Function**: `calculate_population_near_hospitals(radius_km=5.0)`
**Endpoint**: `POST /api/analysis/population-near-hospitals`

Performs zonal statistics around each hospital:
- Uses raster masking to extract population within circular buffer
- Calculates total and mean population density per hospital
- Computes effective catchment area
- Returns structured results with hospital metadata

**Zonal Statistics Approach**:
1. Create circular buffer geometry around hospital point
2. Mask raster to buffer extent
3. Extract valid population cells
4. Aggregate statistics

**Example Output**:
```json
{
  "hospital": "City Hospital",
  "location": [73.87, 18.52],
  "population_within_5km": 125000,
  "mean_density": 6200
}
```

### 4. **Analyze Hospital Accessibility** ✓
**Function**: `analyze_hospital_accessibility(major_road_distance_km=2.0)`
**Endpoint**: `GET /api/analysis/hospital-accessibility`

Multi-factor accessibility scoring considering:
- **Road Access**: Distance to nearest major road (OSM data)
- **Population Density**: Surrounding population from raster
- **Accessibility Categories**:
  - **Good**: Within 2km of major road + population > 0
  - **Moderate**: Within 3km of major road
  - **Poor**: Farther than 3km from major road

**Scoring Formula**:
```
Accessibility Score = 
  50 × (1 - road_distance/max_distance) +    // Road proximity
  50 × (min(density/5000, 1.0))              // Population density
```

**Output Includes**:
- Per-hospital accessibility level
- Distance to nearest major road
- Surrounding population density (mean)
- Computed accessibility score (0-100)

### 5. **Find Healthcare Gaps** ✓
**Function**: `find_healthcare_gaps(min_population_threshold=5000.0, max_hospital_distance_km=5.0)`
**Endpoint**: `GET /api/analysis/healthcare-gaps`

Identifies underserved high-population areas:
1. Extracts high-density raster cells (75th percentile)
2. Filters by minimum population threshold
3. For each cell, finds nearest hospital
4. Flags cells where nearest hospital exceeds distance threshold

**Gap Severity Formula**:
```
Severity Score =
  50 × (population / 10000) +                // Population factor
  50 × (distance / (max_distance × 2))       // Distance factor
```

**Output**:
- Ranked list of healthcare gaps by severity
- Total affected population in gap areas
- Gap-to-hospital distance metrics
- Spatial coordinates for mapping

### 6. **Calculate Site Suitability** ✓
**Function**: `calculate_site_suitability(weights=None)`
**Endpoint**: `POST /api/analysis/site-suitability`

Multi-factor analysis for optimal facility placement:

**Factors** (weighted scoring):
1. **Population Proximity** (40%): Density within 2km buffer
   - Normalized: density / 15,000 (observed max)
2. **Road Accessibility** (25%): Distance to major roads
   - Score: 100 × (1 - distance/5km)
3. **Healthcare Coverage** (25%): Distance from existing hospitals
   - Score: 100 × (distance/7km) - rewards gaps
4. **Environmental Factors** (10%): Distance from water bodies
   - Score: 100 × (distance/2km)

**Scoring Process**:
- Generates 30 candidate locations across study area (grid-based)
- Evaluates each candidate against all factors
- Combines scores using provided weights
- Ranks top 10 candidates by total suitability score

**Output**:
- Top 10 ranked candidate locations
- Component scores for each factor
- Adjustable weights for scenario analysis

## Data Flow Architecture

```
OpenStreetMap Data (OSM PBF)
    ↓
[Osmium extraction: hospitals, roads, rivers]
    ↓
GeoJSON Format (Vector layers)

WorldPop Raster (GeoTIFF)
    ↓
[Rasterio: Clip to study area bounds]
    ↓
Clipped raster + statistics JSON

Vector + Raster
    ↓
[spatial_analysis module]
    ↓
API Service (GISService)
    ↓
REST Endpoints → Frontend/Analysis Tools
```

## Key Implementation Details

### Raster Processing Strategy
- **No Full Vectorization**: Raster kept in gridded format (896 cells)
- **Targeted Queries**: Polygon masking for specific areas
- **Efficient Calculations**: NumPy operations on valid data only
- **Cell-Level Resolution**: 1km × 1km grid cells (0.86 km²)

### Spatial Joins
- **Vector-to-Raster**: Point buffering + masking
- **Vector-to-Vector**: Shapely geometry operations
- **PostGIS Ready**: All operations compatible with PostGIS equivalents

### Fallback Mechanisms
- Real data mode → Demo mode transitions
- Raster unavailable → Vector approximations
- Graceful error handling with logging

## API Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/analysis/population-statistics` | Raster summary statistics |
| GET | `/api/analysis/high-population-areas` | Density-based area identification |
| POST | `/api/analysis/population-near-hospitals` | Zonal statistics by facility |
| GET | `/api/analysis/hospital-accessibility` | Multi-factor accessibility scoring |
| GET | `/api/analysis/healthcare-gaps` | Underserved area identification |
| POST | `/api/analysis/site-suitability` | Multi-criteria facility placement |

## Integration with Existing Systems

### GISService Class Enhancements
Added 6 new methods:
- `get_population_statistics()`: Calls `spatial_analysis.get_population_statistics()`
- `find_high_population_areas_raster()`: Enhanced vector version
- `calculate_population_near_hospitals()`: Zonal statistics
- `analyze_hospital_accessibility_advanced()`: Enhanced accessibility
- `find_healthcare_gaps_analysis()`: Healthcare gap detection
- `calculate_site_suitability_advanced()`: Multi-factor scoring

### Data Store Integration
- Real data mode uses actual raster file: `worldpop_pune_clip.tif`
- Falls back to statistics JSON: `worldpop_stats.json`
- Demo mode uses in-memory vector data
- Automatic mode detection based on file availability

## Performance Characteristics

### Computational Complexity
- **Population Statistics**: O(n) where n = cell count (896)
- **High Population Areas**: O(n log n) for percentile sorting
- **Zonal Statistics**: O(m × n) where m = hospitals, n = cells
- **Site Suitability**: O(c × f) where c = candidates (30), f = features

### Expected Runtimes (Pune Study Area)
- Population statistics: <100ms
- High-population areas: <500ms
- Population near hospitals: <1-2 seconds
- Healthcare gaps analysis: <2-3 seconds
- Site suitability: <1-2 seconds

## Data Accuracy & Limitations

### Strengths
- Uses actual WorldPop gridded population estimates (1km resolution)
- Real OSM vector data for facilities and infrastructure
- Transparent mathematical operations (no AI-generated data)
- Verifiable calculations against actual dataset values

### Limitations
1. **Population Raster Resolution**: 1km cells provide approximate density
2. **OSM Completeness**: Vector data quality varies by region
3. **Temporal**: Data represents 2025 baseline; doesn't account for growth
4. **Hydrology**: River layer simplification may miss small waterways
5. **Road Types**: Major road classification based on OSM tags

## Use Cases

### Healthcare Planning
- Identify priority areas for new hospital construction
- Assess existing hospital coverage adequacy
- Find high-population underserved regions
- Evaluate facility accessibility

### Resource Allocation
- Prioritize infrastructure investment
- Estimate population demand per facility
- Optimize ambulance placement
- Plan emergency response deployment

### Scenario Analysis
- Test different weight combinations for site suitability
- Vary distance thresholds for accessibility
- Model population served by potential new facilities

## Integration with LLM Agent

The spatial analysis functions are registered with the GeoAI Agent (`geoai_agent.py`), enabling:
- Natural language queries like "Find areas with high population but no hospitals"
- Automatic tool selection based on user intent
- Multi-step analysis workflows
- Explanation generation for results

## Future Enhancements

1. **Temporal Analysis**: Multi-year population trends
2. **Cost Factors**: Construction/operation cost integration
3. **Constraints**: Environmental protections, land-use restrictions
4. **Monte Carlo**: Uncertainty quantification for population estimates
5. **Real-time Data**: Streaming population updates
6. **Predictive Models**: Population growth projections

## File Structure

```
backend/app/
├── spatial_analysis.py          # New: Core spatial analysis module
├── gis_tools.py                 # Updated: Enhanced GISService
├── main.py                      # Updated: New API endpoints
├── config.py                    # Raster path configuration
├── data_store.py                # Real data loading
└── models.py                    # Request/response schemas

data/processed/real/
├── worldpop_pune_clip.tif       # Population raster (1km grid)
├── worldpop_stats.json          # Raster statistics
├── hospitals.geojson            # Hospital vector data
├── roads.geojson                # Road network
└── rivers.geojson               # Water bodies
```

## Testing Recommendations

1. **Unit Tests**: Individual spatial functions with mock data
2. **Integration Tests**: End-to-end analysis workflows
3. **Performance Tests**: Large-scale candidate evaluation
4. **Validation**: Results against known benchmarks
5. **API Tests**: All endpoints with various parameter combinations

## References

- **WorldPop Data**: https://www.worldpop.org/ (Disaggregated Density Grid)
- **OpenStreetMap**: https://www.openstreetmap.org/
- **Rasterio Documentation**: https://rasterio.readthedocs.io/
- **Shapely Documentation**: https://shapely.readthedocs.io/
- **PostGIS Equivalent Operations**: Spatial analysis operations are PostGIS-compatible

---

**Implementation Date**: 2025-08-18  
**Real Data Extent**: Pune, Maharashtra, India (73.735°E-73.995°E, 18.415°N-18.655°N)  
**Cell Resolution**: 1km × 1km (~0.86 km²)  
**Study Population**: ~4.6 million (2025 WorldPop estimate)
