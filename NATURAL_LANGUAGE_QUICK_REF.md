# Natural Language Interface - Quick Reference

## Quick Start

### 1. Basic Query

```bash
curl -X POST http://localhost:8000/api/query/natural-language \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show high population areas in Pune"
  }'
```

### 2. With Context

```bash
curl -X POST http://localhost:8000/api/query/natural-language \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find hospitals nearby",
    "context": {
      "selected_area": "Pune"
    }
  }'
```

### 3. List Examples

```bash
curl http://localhost:8000/api/query/examples
```

---

## Query Examples

| Goal | Query | Type |
|------|-------|------|
| **Population** | "Show high population areas" | Raster |
| | "Find densely populated regions" | Raster |
| | "Areas with >50K people" | Raster |
| **Facilities** | "Show hospitals in Pune" | Vector |
| | "Hospitals near major roads" | Vector |
| | "Hospitals within 5 km of rivers" | Vector |
| **Coverage** | "Population near hospitals" | Vector+Raster |
| | "Hospital accessibility" | Vector+Raster |
| **Gaps** | "Healthcare gaps" | Vector+Raster |
| | "Poor hospital access areas" | Vector+Raster |
| **Planning** | "Best hospital location" | Vector+Raster |
| | "Where to build a hospital?" | Vector+Raster |
| **Knowledge** | "What is WorldPop?" | RAG |
| | "How does PostGIS work?" | RAG |

---

## Parameter Extraction Patterns

### Distance
```
"within 5 km"              → 5.0 km
"3 kilometers of roads"    → 3.0 km
"between 1-10 km"          → 10.0 km (uses max)
```

### Percentile
```
"top 75% density"          → 75%
"above 80th percentile"    → 80%
"densest areas"            → 75% (default)
```

### Population
```
">50,000 people"           → 50,000
"high population areas"    → 5,000 (default)
"significant population"   → 10,000
```

---

## Response Structure

```json
{
  "query": "original query",
  "mode": "demo" or "real",
  
  "interpreted_request": "how system understood it",
  "intent": {
    "operation": "operation_name",
    "analysis_type": "raster|vector|vector_raster|rag",
    "confidence": 0.85,
    "target_area": "Pune"
  },
  
  "analysis_type": "raster|vector|vector_raster",
  "tools_selected": ["Tool Name 1", "Tool 2"],
  "result_type": "geospatial_analysis",
  
  "result_count": 25,
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  },
  
  "explanation": "User-friendly summary",
  "summary": {
    "key1": "value1",
    "key2": "value2"
  },
  "recommended_locations": [...],
  
  "sources": ["Real data", "WorldPop"],
  "supported": true,
  "parameters_used": {...}
}
```

---

## Python Client Example

```python
import requests
import json

API_URL = "http://localhost:8000/api/query/natural-language"

def query_geoai(query_text, context=None):
    """Query GeoAI Assistant with natural language."""
    payload = {
        "query": query_text,
        "context": context or {}
    }
    
    response = requests.post(
        API_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

# Example usage
if __name__ == "__main__":
    # Query 1: High population areas
    result = query_geoai("Show high population areas")
    print(f"Interpretation: {result['interpreted_request']}")
    print(f"Results: {result['result_count']} areas found")
    print(f"Analysis: {result['analysis_type']}")
    print()
    
    # Query 2: Healthcare gaps
    result = query_geoai("Find areas with high population but poor hospital access")
    print(f"Gaps identified: {result['summary']['gaps_identified']}")
    print(f"Affected population: {result['summary']['total_affected_population']:,}")
    print()
    
    # Query 3: Site suitability
    result = query_geoai("Where should we build a new hospital?")
    for loc in result.get('recommended_locations', [])[:3]:
        print(f"  {loc['name']}: Score {loc['score']:.1f}")
```

---

## JavaScript Client Example

```javascript
// Natural language query function
async function queryGeoAI(query, context = {}) {
  try {
    const response = await fetch('/api/query/natural-language', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, context })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Query failed:', error);
    throw error;
  }
}

// Example: Display on map
async function showHighPopulation() {
  const result = await queryGeoAI("Show high population areas");
  
  if (result.supported) {
    console.log('Interpretation:', result.interpreted_request);
    console.log('Found:', result.result_count, 'areas');
    
    // Add GeoJSON to map
    map.addSource('results', {
      type: 'geojson',
      data: result.geojson
    });
    
    map.addLayer({
      id: 'results-layer',
      type: 'circle',
      source: 'results',
      paint: {
        'circle-radius': 8,
        'circle-color': '#ff6b6b'
      }
    });
  }
}

// Example: Multi-step analysis
async function findHealthcareGaps() {
  const result = await queryGeoAI(
    "Find areas with high population but poor hospital access"
  );
  
  console.log('Gaps found:', result.summary.gaps_identified);
  console.log('Affected population:', result.summary.total_affected_population);
  
  // Show recommendations
  displayRecommendations(result.recommended_locations);
}
```

---

## Common Scenarios

### Scenario 1: Identify Priority Areas for New Hospitals

```python
# Step 1: Find healthcare gaps
gaps = query_geoai("Find areas with high population but poor hospital access")

# Step 2: Recommend sites
sites = query_geoai("Where should we build new hospitals?")

# Step 3: Analyze accessibility
access = query_geoai("Calculate hospital accessibility")
```

### Scenario 2: Assess Existing Coverage

```python
# Step 1: Get population stats
pop = query_geoai("Get population statistics")

# Step 2: Calculate served population
served = query_geoai("Calculate population near hospitals")

# Step 3: Identify gaps
coverage = pop['summary']['total_population']
served_count = served['summary']['total_population_nearby']
coverage_pct = (served_count / coverage) * 100

print(f"Coverage: {coverage_pct:.1f}%")
```

### Scenario 3: Evaluate Infrastructure

```python
# Find hospitals near roads
urban = query_geoai("Find hospitals within 2 km of major roads")

# Find hospitals near water
water = query_geoai("Find hospitals near rivers")

# Compare accessibility
accessibility = query_geoai("Analyze hospital accessibility")
```

---

## Error Handling

```python
result = query_geoai(query)

if not result.get('supported'):
    # Query not supported
    print("Error:", result.get('error'))
    print("Explanation:", result.get('explanation'))
    print("Try these instead:")
    for example in result.get('examples', []):
        print(f"  - {example}")
else:
    # Query successful
    print(f"Found {result['result_count']} results")
    print(f"Using tools: {', '.join(result['tools_selected'])}")
    print(f"Data mode: {result['mode']}")
```

---

## Operation Codes

```
Vector Analysis
- "find_nearby"           # Proximity search
- "show_layer"            # Display layer

Raster Analysis
- "get_population_statistics"    # Population stats
- "find_high_population_areas"   # High-density regions

Vector + Raster Analysis
- "calculate_population_near_hospitals"  # Zonal stats
- "analyze_hospital_accessibility"      # Multi-factor
- "find_healthcare_gaps"                # Gap analysis
- "calculate_site_suitability"          # Site selection

Knowledge Base
- "rag"                   # Retrieval-Augmented Generation
```

---

## Analysis Types

```
VECTOR
  - Single layer proximity
  - Feature attribute queries
  - Examples: Hospitals near roads

RASTER
  - Population statistics
  - Density analysis
  - Examples: High-density areas

VECTOR_RASTER
  - Raster data within vector buffers
  - Multi-factor analysis
  - Examples: Population near hospitals

RAG
  - Knowledge-base questions
  - Document retrieval
  - Examples: What is WorldPop?

UNSUPPORTED
  - Queries system can't handle
  - Returns suggestions
```

---

## Confidence Scores

```
1.0   Exact match           "Show high population at 75th percentile"
0.95  Very high confidence  "Show top 80% population areas"
0.9   High confidence       "Find hospitals near major roads"
0.85  Good confidence       "Show high population areas"
0.8   Reasonable            "Find population near hospitals (assumes 5km)"
< 0.8 Low confidence        "Query may be misinterpreted"
```

---

## Security Features

✅ **SQL Injection Prevention**
- Blocks: `DROP TABLE`, `DELETE`, `UNION SELECT`
- Blocks: SQL comments (`--`, `/* */`)
- Blocks: `EXEC()`, `EXECUTE()`

✅ **Operation Whitelist**
- Only approved operations allowed
- No raw SQL execution
- No shell commands

✅ **Parameter Validation**
- Type checking
- Range validation
- Enum validation
- Format validation

✅ **Error Handling**
- No schema exposure
- Helpful error messages
- Alternative suggestions

---

## Configuration

```bash
# Start server
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test
python ../scripts/test_natural_language.py

# With specific data mode
export DATA_MODE=real
python -m uvicorn app.main:app --reload
```

---

## Troubleshooting

### Query not understood
```
Problem: "Find stuff" returns unsupported
Reason: Vague query without spatial keywords
Solution: Use specific keywords like "hospitals", "population", "high"
```

### Wrong parameter extracted
```
Problem: "Find hospitals within 3-5 km" interprets as 5 km
Reason: System uses maximum of range
Solution: Specify exact distance "Find hospitals within 5 km"
```

### No results returned
```
Problem: "Find hospitals" returns 0 results in real mode
Reason: Real data may be sparse or not loaded
Solution: Check DATA_MODE environment variable, try demo mode
```

### Confidence score too low
```
Problem: Query accepted but confidence < 0.8
Reason: Ambiguous query with multiple interpretations
Solution: Rephrase with more specific keywords and parameters
```

---

## Performance Notes

| Query Type | Time | Notes |
|-----------|------|-------|
| High population | <500ms | Raster percentile |
| Nearby features | 1-2s | Vector proximity |
| Population nearby | 2-3s | Zonal statistics |
| Healthcare gaps | 2-3s | Complex analysis |
| Site suitability | 1-2s | Multi-factor scoring |
| Knowledge query | 1-3s | Retrieval + ranking |

---

## Next Steps

1. **Try the examples**: Run `curl http://localhost:8000/api/query/examples`
2. **Read the docs**: See `NATURAL_LANGUAGE_INTERFACE.md`
3. **Run tests**: `python scripts/test_natural_language.py`
4. **Integrate**: Use the Python/JavaScript examples
5. **Customize**: Add new query patterns to `IntentParser`

---

## Support

- **Technical Docs**: `NATURAL_LANGUAGE_INTERFACE.md`
- **API Reference**: `API_REFERENCE.md`
- **Test Suite**: `scripts/test_natural_language.py`
- **Architecture**: `docs/architecture.md`
