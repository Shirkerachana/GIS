# Natural Language Interface for GeoAI Assistant

## Overview

The Enhanced GeoAI Assistant now supports **natural language queries** for geospatial analysis. Users can ask questions in plain English, and the system automatically:

1. **Parses** the query into structured GIS intents
2. **Validates** parameters against approved tools
3. **Prevents** arbitrary SQL generation and unsafe operations
4. **Executes** the appropriate spatial analysis
5. **Returns** results with full transparency

This document covers architecture, usage, examples, and security considerations.

---

## System Architecture

```
User Query (Natural Language)
    ↓
Intent Parser (intent_parser.py)
    ↓
Structured Intent with Parameters
    ↓
Tool Registry & Validator (tool_registry.py)
    ↓
Parameter Validation & Operation Approval
    ↓
Enhanced Agent (enhanced_agent.py)
    ↓
GIS Service Execution
    ↓
Structured Response (Interpretation + Results + GeoJSON)
```

### Key Components

#### 1. Intent Parser (`backend/app/intent_parser.py`)

Converts natural language queries to **StructuredIntent** objects containing:

```python
StructuredIntent {
    operation: str              # e.g., "find_healthcare_gaps"
    analysis_type: AnalysisType # VECTOR, RASTER, VECTOR_RASTER, RAG, UNSUPPORTED
    target_area: str            # e.g., "Pune"
    distance_km: float          # e.g., 5.0
    percentile: float           # e.g., 75.0
    population_threshold: float # e.g., 5000.0
    weights: dict               # Factor weights for multi-criteria analysis
    confidence: float           # 0.0-1.0 confidence score
    supported: bool             # Whether query is supported
}
```

**Pattern Matching Strategy:**
- Identifies query type through keyword detection
- Extracts numerical parameters (distance, percentile, thresholds)
- Determines analysis type needed (raster/vector/combined)
- Falls back to RAG for knowledge-base questions

#### 2. Tool Registry (`backend/app/tool_registry.py`)

Maintains list of **approved GIS tools** with:

```python
ToolDefinition {
    name: str                          # "Population Near Hospitals"
    description: str                   # What the tool does
    operation_id: str                  # "calculate_population_near_hospitals"
    requires_parameters: list[str]     # Required params
    optional_parameters: list[str]     # Optional params
    parameter_validators: dict         # Validation functions
}
```

**Approved Operations:**
- `get_population_statistics` - Raster statistics
- `find_high_population_areas` - Raster percentile analysis
- `calculate_population_near_hospitals` - Zonal statistics
- `analyze_hospital_accessibility` - Multi-factor scoring
- `find_healthcare_gaps` - Gap identification
- `calculate_site_suitability` - Site selection
- `find_nearby` - Vector proximity search
- `show_layer` - Layer display

#### 3. Operation Validator

Prevents execution of:
- ❌ `execute_sql`, `raw_query` - SQL injection
- ❌ `drop_table`, `delete_database` - Data destruction
- ❌ `execute_shell` - Shell injection
- ✅ Only approved operations allowed

#### 4. Enhanced Agent (`agent/enhanced_agent.py`)

Orchestrates end-to-end query processing:

1. Parse query → structured intent
2. Validate operation
3. Handle RAG vs spatial analysis
4. Extract and validate parameters
5. Execute GIS operation
6. Format response

---

## Usage Examples

### Example 1: High Population Areas

**Query:**
```
"Show high population areas in Pune"
```

**Parsing:**
```
Intent {
    operation: "find_high_population_areas"
    analysis_type: RASTER
    percentile: 75.0
    confidence: 0.85
}
```

**Response:**
```json
{
  "interpreted_request": "Find areas in top 75% population density",
  "analysis_type": "raster",
  "tools_selected": ["High-Population Areas"],
  "result_count": 25,
  "summary": {
    "high_population_count": 25,
    "area_percentage": 15.3
  },
  "geojson": { "type": "FeatureCollection", "features": [...] }
}
```

### Example 2: Healthcare Gaps

**Query:**
```
"Find areas with high population but poor hospital accessibility"
```

**Parsing:**
```
Intent {
    operation: "find_healthcare_gaps"
    analysis_type: VECTOR_RASTER
    population_threshold: 5000.0
    hospital_accessibility: "low"
    distance_km: 5.0
    confidence: 0.9
}
```

**Response:**
```json
{
  "interpreted_request": "Identify high-population areas with poor hospital accessibility",
  "analysis_type": "vector_raster",
  "tools_selected": ["Healthcare Gap Analysis"],
  "result_count": 8,
  "summary": {
    "gaps_identified": 8,
    "total_affected_population": 250000
  },
  "geojson": { "type": "FeatureCollection", "features": [...] }
}
```

### Example 3: Site Suitability

**Query:**
```
"Find the best location for a new hospital"
```

**Parsing:**
```
Intent {
    operation: "calculate_site_suitability"
    analysis_type: VECTOR_RASTER
    weights: {
        "population_proximity": 0.4,
        "road_accessibility": 0.25,
        "healthcare_coverage": 0.25,
        "environmental_factors": 0.1
    }
    confidence: 0.9
}
```

**Response:**
```json
{
  "interpreted_request": "Multi-factor site suitability analysis for new hospital location",
  "analysis_type": "vector_raster",
  "tools_selected": ["Site Suitability Analysis"],
  "result_count": 30,
  "recommended_locations": [
    {
      "name": "Candidate 1",
      "score": 83.5,
      "coordinates": [73.8567, 18.5204],
      "factors": {
        "population_proximity": 0.95,
        "road_accessibility": 0.78,
        "healthcare_coverage": 0.70,
        "environmental_factors": 0.60
      }
    }
  ]
}
```

### Example 4: Knowledge-Base Query

**Query:**
```
"What is WorldPop data?"
```

**Parsing:**
```
Intent {
    operation: "rag"
    analysis_type: RAG
    requires_rag: true
    confidence: 0.9
}
```

**Response:**
```json
{
  "interpreted_request": "Knowledge-base query (RAG)",
  "analysis_type": "knowledge_base",
  "tools_selected": ["RAG (Retrieval-Augmented Generation)"],
  "result_type": "text",
  "result": "WorldPop is a high-resolution gridded population dataset..."
}
```

---

## REST API Endpoints

### 1. Natural Language Query

**Endpoint:** `POST /api/query/natural-language`

**Request:**
```json
{
  "query": "Find high population areas in Pune",
  "context": {}
}
```

**Response:**
```json
{
  "query": "Find high population areas in Pune",
  "mode": "demo",
  "interpreted_request": "Find areas in top 75% population density",
  "intent": {
    "operation": "find_high_population_areas",
    "analysis_type": "raster",
    "target_area": "Pune",
    "confidence": 0.85
  },
  "analysis_type": "raster",
  "tools_selected": ["High-Population Areas"],
  "result_count": 25,
  "summary": {...},
  "geojson": {...},
  "supported": true
}
```

### 2. List Available Operations

**Endpoint:** `GET /api/query/operations`

**Response:**
```json
{
  "operations": {
    "get_population_statistics": "Extract population statistics from raster data",
    "find_high_population_areas": "Identify densely populated regions...",
    ...
  },
  "examples": [
    "Show high population areas in Pune",
    "Find hospitals in high population areas",
    ...
  ]
}
```

### 3. Get Example Queries

**Endpoint:** `GET /api/query/examples`

**Response:**
```json
{
  "examples": [
    "Show high population areas in Pune",
    "Find hospitals in high population areas",
    "Find areas with high population but poor hospital accessibility",
    "Find the best location for a new hospital",
    "Find hospitals within 5 km of major roads",
    "Show all hospitals in Pune",
    "What is WorldPop data?",
    "Explain how hospital accessibility is calculated"
  ],
  "description": "Example queries that demonstrate the natural language interface"
}
```

---

## Parameter Extraction & Validation

### Distance Extraction

The parser looks for patterns like:
```
"within 5 km"
"near X where distance < 3 km"
"within 10 kilometres of major roads"
→ distance_km: 5.0, 3.0, 10.0
```

### Percentile Extraction

```
"top 75% population density"
"densest areas (80th percentile)"
"high density (>80th percentile)"
→ percentile: 75.0, 80.0
```

### Population Threshold

```
"high population areas"
"areas with >5000 people"
"population exceeding 10,000"
→ population_threshold: 5000.0, 10000.0
```

### Validation Rules

| Parameter | Required | Type | Validation |
|-----------|----------|------|-----------|
| `target_area` | ✓ | string | Non-empty, <100 chars |
| `distance_km` | ✗ | float | > 0 |
| `percentile` | ✗ | float | 0-100 |
| `population_threshold` | ✗ | float | > 0 |
| `target_layer` | ✗ | string | hospitals, roads, rivers, population |
| `weights` | ✗ | dict | Values sum to 1.0 |

---

## Security: SQL Injection Prevention

The system blocks dangerous patterns:

```python
# BLOCKED PATTERNS
"DROP TABLE hospitals"
"DELETE FROM hospitals WHERE"
"UNION SELECT"
"EXEC(" or "EXECUTE("
"--" (SQL comments)
"/* */" (multi-line comments)

# HOW IT WORKS
1. Every query string checked for dangerous patterns
2. Only approved operations allowed
3. Parameters validated before execution
4. No raw SQL generation
5. Error messages don't expose schema
```

**Test Cases:**
```python
# These will be REJECTED
"Show hospitals; DROP TABLE hospitals;"
"Find areas WHERE 1=1; DELETE FROM hospitals;"
"hospitals /* */ OR 1=1"
"UNION SELECT * FROM"
```

---

## Confidence Scoring

Each intent receives a confidence score (0.0-1.0):

```
1.0  = Exact keyword match, clear parameters
0.9  = High confidence, minor ambiguity
0.85 = Good match, some assumptions
0.8  = Reasonable match, multiple interpretations
< 0.8 = Low confidence, may be unsupported
```

**Example:**
```
"Show high population areas"
→ 0.85 (assumes 75th percentile, default distance)

"Show areas in top 80% by population"
→ 0.95 (exact parameters specified)

"Find stuff"
→ 0.0 (unsupported - too ambiguous)
```

---

## Query Interpretation & Explanation

The system provides human-readable interpretation:

**Input:** "Find hospitals within 5 km of major roads"

**System Interpretation:**
```
"Find hospitals within 5 km of major roads"
→ Operation: find_nearby
→ Analysis Type: vector
→ Target: hospitals
→ Reference: roads
→ Distance: 5 km
```

**User-Friendly Explanation:**
```
"Searching for hospitals near major roads (within 5 km)"
```

This ensures **transparency** - users see exactly how their query was understood.

---

## Analysis Type Determination

The system automatically selects the appropriate analysis:

| Query Pattern | Analysis Type | Why |
|---------------|---------------|-----|
| "high population areas" | RASTER | Uses WorldPop gridded data |
| "hospitals within 5 km" | VECTOR | Proximity between features |
| "population near hospitals" | VECTOR_RASTER | Raster data within vector buffers |
| "healthcare gaps" | VECTOR_RASTER | Combines raster + vector analysis |
| "best hospital location" | VECTOR_RASTER | Multi-factor (raster + vector) |
| "What is WorldPop?" | RAG | Knowledge-base query |

---

## Supported Query Patterns

### Pattern 1: Population Analysis
```
✓ "Show high population areas"
✓ "Find densely populated regions"
✓ "Show areas with >50,000 people"
✓ "Find top 10% population density"
```

### Pattern 2: Facility Analysis
```
✓ "Show hospitals in Pune"
✓ "Find hospitals near major roads"
✓ "Find hospitals within 5 km of rivers"
✓ "Show all hospitals"
```

### Pattern 3: Service Coverage
```
✓ "Find population near hospitals"
✓ "Calculate hospital accessibility"
✓ "Find hospital service areas"
✓ "Show population served by hospitals"
```

### Pattern 4: Gap Analysis
```
✓ "Find healthcare gaps"
✓ "Find areas with poor hospital access"
✓ "Find underserved population"
✓ "Find high population with no hospitals"
```

### Pattern 5: Planning
```
✓ "Find best hospital location"
✓ "Recommend new hospital site"
✓ "Where should I build a hospital?"
✓ "Site suitability analysis"
```

### Pattern 6: Knowledge Base
```
✓ "What is WorldPop data?"
✓ "Explain how PostGIS works"
✓ "How is hospital accessibility calculated?"
✓ "Tell me about OpenStreetMap"
```

---

## Unsupported Queries

These queries will be rejected with helpful guidance:

```
✗ "Show me everything" (too vague)
✗ "Delete all hospitals" (dangerous)
✗ "Execute this SQL" (raw SQL not allowed)
✗ "Show tables" (no schema exposure)
✗ Random text with no spatial keywords
```

**Response:**
```json
{
  "supported": false,
  "error": "Query not supported",
  "explanation": "This question is currently not supported. Try one of these queries...",
  "supported_operations": [...],
  "examples": [...]
}
```

---

## Error Handling

### Validation Errors

```
Parameter Error:
- Missing required parameter → Error message with parameter name
- Invalid value format → Error message with valid range
- Invalid operation → List of approved operations

Example:
"Invalid value for percentile: 150 (must be 0-100)"
```

### Execution Errors

```
Processing Error:
- Data not available → "Population data not available in this mode"
- Analysis failed → "Unable to compute site suitability"
- Timeout → "Analysis took too long, try with smaller area"
```

### User Guidance

Always provides:
1. What went wrong
2. Why it went wrong
3. How to fix it
4. Alternative queries to try

---

## Implementation Details

### Intent Parser Implementation

```python
class IntentParser:
    def parse(self, query: str, context: dict) -> StructuredIntent:
        # 1. Detect query type (RAG, vector, raster, etc.)
        # 2. Extract parameters
        # 3. Validate parameters
        # 4. Calculate confidence score
        # 5. Return StructuredIntent
        
        # Pattern matching order matters:
        # 1. Healthcare gaps (most specific)
        # 2. High population (common raster query)
        # 3. Population near hospitals (common vector-raster)
        # 4. Hospital accessibility
        # 5. Site suitability
        # 6. Nearby features
        # 7. Single layer query (fallback)
```

### Tool Registry Implementation

```python
class ToolRegistry:
    def __init__(self):
        # Build registry of approved tools
        # Each tool has validators for its parameters
        
        "high_population_areas": ToolDefinition(
            name="High-Population Areas",
            operation_id="find_high_population_areas",
            requires=["target_area", "percentile"],
            validators={
                "target_area": is_valid_area,
                "percentile": is_percentile,  # 0-100
            }
        )
```

### Enhanced Agent Implementation

```python
class EnhancedGeoAIAgent:
    def process_query(self, query: str, context: dict):
        # Step 1: Parse intent
        intent = self.parser.parse(query, context)
        
        # Step 2: Validate operation
        OperationValidator.validate_operation(intent.operation)
        
        # Step 3: Extract parameters from intent
        parameters = self._extract_parameters(intent)
        
        # Step 4: Validate parameters with tool registry
        tool, validated = self.registry.validate_and_get_tool(
            intent.operation, 
            parameters
        )
        
        # Step 5: Execute operation
        result = self._execute_operation(intent, validated)
        
        # Step 6: Build response
        return self._build_response(query, intent, tool, result)
```

---

## Testing

Run the comprehensive test suite:

```bash
cd backend
python scripts/test_natural_language.py
```

**Tests Included:**
1. ✓ Intent parsing accuracy
2. ✓ Operation validation
3. ✓ Parameter validation
4. ✓ SQL injection prevention
5. ✓ Available operations listing
6. ✓ Intent-to-parameters conversion
7. ✓ End-to-end query processing

---

## Future Enhancements

### Phase 2: Advanced Features
- [ ] Dialogue context tracking
- [ ] Query refinement ("Show more", "Try 5 km")
- [ ] Custom weight specification
- [ ] Time-series analysis
- [ ] Hypothetical scenarios

### Phase 3: ML-Based Intent
- [ ] Fine-tuned language model for intent parsing
- [ ] Named entity recognition for locations
- [ ] Semantic similarity for query expansion
- [ ] User preference learning

### Phase 4: Multi-Language
- [ ] Support for Hindi, Marathi (for Pune)
- [ ] Automatic translation + parsing
- [ ] Localized result formatting

---

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/query/natural-language` | POST | Process natural language query |
| `/api/query/operations` | GET | List available operations |
| `/api/query/examples` | GET | Get example queries |
| `/api/analysis/population-statistics` | GET | Direct population stats endpoint |
| `/api/analysis/high-population-areas` | GET | Direct high-pop endpoint |
| `/api/analysis/population-near-hospitals` | POST | Direct hospital-pop endpoint |
| `/api/analysis/hospital-accessibility` | GET | Direct accessibility endpoint |
| `/api/analysis/healthcare-gaps` | GET | Direct gaps endpoint |
| `/api/analysis/site-suitability` | POST | Direct suitability endpoint |

---

## Example Integration (Frontend)

```javascript
// JavaScript example
async function queryGeoAI(userQuery) {
  const response = await fetch('/api/query/natural-language', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: userQuery })
  });
  
  const result = await response.json();
  
  // Display interpretation
  console.log('Interpreted as:', result.interpreted_request);
  
  // Display analysis type
  console.log('Analysis type:', result.analysis_type);
  
  // Display results
  if (result.supported) {
    // Render GeoJSON on map
    displayOnMap(result.geojson);
    
    // Show summary
    displaySummary(result.summary);
    
    // Show explanation
    displayExplanation(result.explanation);
  } else {
    showError(result.explanation);
    showExamples(result.examples);
  }
}
```

---

## Configuration

Environment variables:

```bash
# Enable/disable natural language interface
NL_INTERFACE_ENABLED=true

# Confidence threshold for accepting intent
NL_CONFIDENCE_MIN=0.75

# Maximum query length (chars)
NL_MAX_QUERY_LENGTH=500

# Debug mode (show parsing details)
NL_DEBUG=false
```

---

## Summary

The Enhanced GeoAI Assistant provides:

✅ **Natural Language Support** - Ask questions in plain English
✅ **Intent Parsing** - Automatic query understanding
✅ **Parameter Extraction** - Intelligent parameter detection
✅ **Operation Validation** - Only approved tools allowed
✅ **SQL Injection Prevention** - Security built-in
✅ **Transparent Interpretation** - Users see how query was understood
✅ **Comprehensive Results** - GeoJSON + explanation + summary
✅ **Error Guidance** - Helpful messages for unsupported queries

Users can now interact with spatial data using conversational language while the system ensures security and correctness at every step.
