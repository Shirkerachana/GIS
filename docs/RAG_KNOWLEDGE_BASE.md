# RAG Knowledge Base Documentation

The GeoAI Assistant includes a Retrieval-Augmented Generation (RAG) knowledge layer that provides contextual information about GIS concepts, datasets, methodologies, and the system architecture.

## Overview

The RAG system helps the agent answer three types of queries:

1. **Knowledge Questions** → RAG only
   - Example: "What is raster data?"
   - Returns encyclopedia-style answers from the knowledge base

2. **Spatial Questions** → GIS Tools only
   - Example: "Find high population areas."
   - Executes spatial analysis and returns geographic results

3. **Combined Questions** → GIS Tools + RAG
   - Example: "Find the best hospital location and explain the methodology."
   - Executes spatial analysis, then augments results with knowledge base context

## Knowledge Base Categories

### GIS Concepts

The knowledge base covers fundamental geographic information system concepts:

- **What is GIS**: Geographic Information System definition and purpose
- **Raster data**: Grid-based representation using cells/pixels for continuous phenomena
- **Vector data**: Discrete geometric objects (points, lines, polygons) for specific features
- **Raster vs Vector**: Comparison, use cases, and when to choose each format
- **Spatial buffer**: Area surrounding a feature within a specified distance
- **Spatial intersection**: Geographic features that overlap or share common areas

### PostGIS Concepts

Knowledge about the PostGIS spatial database extension:

- **PostGIS overview**: PostgreSQL extension with geometry types and spatial functions
- **Geometric types**: Point, LineString, Polygon, and Multi* variants
- **Spatial indexing**: GIST and BRIN indexes for accelerating spatial queries
- **Key functions**: ST_DWithin, ST_Intersects, ST_Buffer, ST_Distance, ST_Within

### Dataset Descriptions

Detailed information about data sources used in the analysis:

- **WorldPop**: 1km resolution gridded population data for identifying high-population areas
  - Source: University of Southampton
  - Used for: Population coverage scoring in hospital site selection

- **OpenStreetMap**: Free, open-access geographic database with vector data
  - Source: OpenStreetMap Foundation
  - Includes: Hospitals, roads, rivers, buildings, administrative boundaries
  - Used for: Road accessibility and healthcare gap analysis

- **Hospital dataset**: Healthcare facility locations from OpenStreetMap
  - Attributes: Name, type, location geometry
  - Used for: Accessibility analysis and healthcare gap measurement

### Hospital Site-Selection Methodology

Comprehensive documentation of the hospital location analysis approach:

- **Overall methodology**: Transparent multi-factor scoring using real data
  - Population Coverage (40%): Proximity to high-population areas via WorldPop
  - Road Accessibility (30%): Distance to major roads from OSM
  - Healthcare Gap (30%): Distance from existing hospitals, identifying underserved areas

- **Population coverage scoring**:
  - 2km buffer around candidate location
  - Query WorldPop raster for mean population density
  - Score: min(100, 100 × mean_density / 15000)

- **Road accessibility scoring**:
  - Find nearest major road from OSM
  - Linear decay function: max(0, 100 × (1 - distance_km / 5.0))
  - Perfect score (100) at 0km, zero at 5km+

- **Healthcare gap scoring**:
  - Find nearest existing hospital
  - Score increases with distance: min(100, 100 × distance_km / 7.0)
  - Max score (100) at 7km+, zero at 0km

- **Final suitability score**: Weighted sum of normalized factors (0-100 scale)

### Project Architecture

System design and component relationships:

- **Layered architecture**:
  - Frontend (React/TypeScript): Interactive map and UI
  - Backend (FastAPI/Python): REST API with spatial analysis endpoints
  - GIS Layer (Shapely, Rasterio): Vector and raster operations
  - Data Layer: OSM vector data, WorldPop raster, PostGIS-ready schema
  - Agent Layer (LangGraph): Query routing to GIS tools or RAG

- **Backend components**:
  - FastAPI endpoints for spatial analysis
  - GISService: Coordinates vector/raster operations
  - SpatialAnalysisModule: Population statistics and hospital optimization
  - RasterDataManager: WorldPop raster querying

- **Frontend components**:
  - Leaflet map for GIS visualization
  - Sidebar with layer controls and search
  - Demo queries for quick exploration
  - Result panel for analysis output
  - Specialized components for site-selection results

### Spatial Analysis Methodology

General approach to combining vector and raster data:

- **Analysis workflow**:
  1. Vector queries extract discrete features (hospitals, roads)
  2. Raster queries analyze continuous phenomena (population density)
  3. Spatial relationships connect features across layers (proximity, intersection)
  4. Multi-factor scoring combines independent metrics
  5. Results validated and returned as GeoJSON

- **Multi-factor scoring**:
  - Each factor normalized to 0-100
  - Explicit weights sum to 100%
  - Transparent calculation: score = Σ(weight_i × normalized_factor_i)
  - Allows stakeholder understanding of factor influence

- **Suitability analysis**:
  - Demonstrates multi-factor scoring approach
  - Combines population, accessibility, and coverage factors
  - For demonstration purposes only, not professional planning advice

### Study Area

Geographic focus of the demonstration:

- **Location**: Pune, Maharashtra, India
- **Data sources**: 
  - In-memory vector layers (hospitals, roads, rivers, buildings) from OSM
  - WorldPop population raster clipped to Pune region
- **Use case**: Development and testing environment
- **Production readiness**: Architecture supports full OSM extracts in PostGIS

## Query Routing Logic

The agent uses the following logic to route queries:

```
if query contains both spatial and knowledge keywords:
    → Combine GIS analysis with RAG context
elif query contains knowledge keywords:
    → RAG only (answer from knowledge base)
elif query contains spatial keywords:
    → GIS tools only (execute spatial analysis)
else:
    → Unsupported (provide helpful error)
```

## Knowledge Base Integration

The RAG engine in `rag/rag_engine.py`:

1. **Document retrieval**: Matches query keywords against knowledge base entries
2. **Fuzzy matching**: Falls back to title similarity if no keyword matches
3. **Source attribution**: Every answer includes source metadata
4. **Augmentation**: Combined queries integrate RAG answers with GIS results

## Example Queries

### Knowledge Only
- "What is raster data?"
- "What dataset provides population?"
- "Tell me about OpenStreetMap."
- "Explain the hospital site-selection methodology."
- "What is PostGIS?"

### Spatial Only
- "Show hospitals in Pune."
- "Find hospitals within 5 km of major roads."
- "Show high population areas."
- "Find the best location for a new hospital."

### Combined (GIS + RAG)
- "Find the best hospital location and explain the methodology."
- "Show high population areas and describe the data source."
- "Find hospitals near roads and explain road accessibility scoring."

## Implementation Details

### Knowledge Base Structure

Each document entry contains:

```python
{
    "title": "Question topic",
    "keywords": ["keyword1", "keyword2", ...],
    "answer": "Encyclopedia-style answer text",
    "source": "Source attribution"
}
```

### Query Matching Algorithm

1. Normalize query to lowercase
2. Check for keyword matches (exact substring)
3. Collect all matching documents
4. If multiple matches, return first match
5. If no keyword matches, use fuzzy title matching
6. If still no match, return helpful fallback message

### Combined Query Execution

For queries with both spatial and knowledge intent:

1. Parse spatial intent (which GIS operation to run)
2. Execute spatial analysis (e.g., site_suitability)
3. Retrieve relevant knowledge (e.g., methodology)
4. Augment explanation with RAG answer
5. Merge sources from both components
6. Return combined result with both GIS and knowledge context

## Disclaimer

The hospital site-selection analysis is for demonstration purposes only and is NOT:
- A substitute for professional urban planning
- A medical facility planning recommendation
- An official government or urban-planning recommendation

Actual hospital site selection requires:
- Professional urban planners and consultants
- Medical facility experts
- Government planning authorities
- Environmental impact assessments
- Community engagement
- Detailed site-specific surveys

## Future Enhancements

Potential improvements to the RAG layer:

1. **Vector embedding**: Use semantic embeddings for better query matching
2. **Multi-document retrieval**: Return multiple relevant documents for complex queries
3. **Cross-references**: Link between knowledge entries
4. **Version control**: Track knowledge base updates over time
5. **User feedback**: Learn from relevance feedback to improve retrieval
6. **Dynamic knowledge**: Ingest documentation automatically from codebase
7. **Temporal information**: Track when knowledge was last verified

## References

- GIS Concepts: Standard GIS terminology and definitions
- PostGIS Documentation: Official PostGIS extension documentation
- WorldPop Dataset: https://www.worldpop.org/
- OpenStreetMap Foundation: https://www.openstreetmap.org/
- Project Architecture: See `docs/architecture.md`
- Spatial Analysis: See `docs/data-pipeline.md`
