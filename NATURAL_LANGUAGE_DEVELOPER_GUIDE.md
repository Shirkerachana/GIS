# Natural Language Interface - Developer Guide

## Overview

This guide helps developers understand, extend, and maintain the natural language interface for GeoAI Assistant.

---

## Architecture

### System Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    User Query (String)                        │
│              "Show high population areas"                     │
└────────────────────────────┬─────────────────────────────────┘
                             │
                ┌────────────▼────────────┐
                │   Intent Parser         │
                │ (intent_parser.py)      │
                │                         │
                │ Pattern Matching        │
                │ Parameter Extraction    │
                │ Confidence Scoring      │
                └────────────┬────────────┘
                             │
        ┌────────────────────▼─────────────────────┐
        │  StructuredIntent Object                 │
        │  {                                        │
        │    operation: "find_high_population...", │
        │    analysis_type: RASTER,                │
        │    percentile: 75.0,                     │
        │    confidence: 0.85,                     │
        │    supported: true                       │
        │  }                                        │
        └────────────────────┬─────────────────────┘
                             │
                ┌────────────▼──────────────────────┐
                │  Tool Registry & Validator         │
                │  (tool_registry.py)                │
                │                                    │
                │  - Approve/Reject Operation        │
                │  - Validate Parameters             │
                │  - Check SQL Injection             │
                └────────────┬───────────────────────┘
                             │
            ┌────────────────▼────────────────────┐
            │  Parameter Validation               │
            │  {                                  │
            │    target_area: "Pune" ✓            │
            │    percentile: 75.0 ✓               │
            │  }                                  │
            └────────────┬───────────────────────┘
                         │
        ┌────────────────▼──────────────────────┐
        │  Enhanced Agent Execution              │
        │  (enhanced_agent.py)                   │
        │                                        │
        │  - Execute Operation                   │
        │  - Call GISService Method              │
        │  - Format Response                     │
        └────────────┬───────────────────────────┘
                     │
        ┌────────────▼──────────────────────┐
        │  GISService Spatial Analysis       │
        │  (gis_tools.py)                    │
        │                                    │
        │  - Raster Processing               │
        │  - Vector Operations               │
        │  - Multi-factor Analysis           │
        └────────────┬───────────────────────┘
                     │
        ┌────────────▼────────────────────────┐
        │  Results                             │
        │  {                                   │
        │    explanation: "...",               │
        │    geojson: {...},                   │
        │    summary: {...},                   │
        │    sources: [...]                    │
        │  }                                   │
        └────────────┬────────────────────────┘
                     │
        ┌────────────▼──────────────────────┐
        │  API Response                      │
        │  (main.py endpoints)               │
        │                                    │
        │  JSON with:                        │
        │  - Interpretation                  │
        │  - Intent Details                  │
        │  - Results & GeoJSON               │
        │  - Confidence Score                │
        └──────────────────────────────────────┘
```

---

## Core Components

### 1. Intent Parser (`backend/app/intent_parser.py`)

**Class: `IntentParser`**

```python
class IntentParser:
    """Converts natural language to structured intents."""
    
    def parse(query: str, context: dict) -> StructuredIntent:
        """Main parsing method."""
        # Returns StructuredIntent with operation, parameters, confidence
```

**Pattern Matching Order** (most specific to least):
1. Healthcare gaps - "high population AND poor accessibility"
2. High population - "high population/dense/top%"
3. Population near hospitals - "population AND hospital"
4. Hospital accessibility - "accessibility/access/road"
5. Site suitability - "best location/site/recommend"
6. Nearby features - "within X km/near"
7. Single layer - "show/hospitals/roads"

**Data Classes:**
- `AnalysisType` enum: VECTOR, RASTER, VECTOR_RASTER, RAG, UNSUPPORTED
- `StructuredIntent` dataclass: operation, analysis_type, parameters

**Key Methods:**
```python
def _match_healthcare_gaps(normalized: str)     # Healthcare gap pattern
def _match_high_population(normalized: str)     # Population density pattern
def _match_population_near_hospitals(normalized: str)  # Coverage pattern
def _match_hospital_accessibility(normalized: str)    # Accessibility pattern
def _match_site_suitability(normalized: str)    # Site selection pattern
def _match_nearby(normalized: str)              # Proximity pattern
def _match_single_layer(normalized: str)        # Single layer pattern

def _extract_distance(text: str)                # Extract km value
def _extract_percentile(text: str)              # Extract percentage
def _extract_population_threshold(text: str)    # Extract population count
def _extract_weights(text: str)                 # Extract weighting factors
```

**Extending Intent Parser:**
To add a new query pattern:

1. Add pattern matching method:
```python
def _match_new_pattern(self, normalized: str) -> StructuredIntent | None:
    patterns = [r"pattern1", r"pattern2"]
    if not any(re.search(p, normalized) for p in patterns):
        return None
    
    # Extract parameters
    param1 = self._extract_something(normalized)
    
    return StructuredIntent(
        operation="new_operation",
        analysis_type=AnalysisType.VECTOR,
        # ... parameters
        supported=True,
        confidence=0.85,
        explanation="Human-readable explanation"
    )
```

2. Add to `_match_patterns()` method:
```python
def _match_patterns(self, normalized: str, context: dict):
    # ... existing patterns ...
    
    # Add new pattern
    new_intent = self._match_new_pattern(normalized)
    if new_intent:
        return new_intent
    
    # ... continue ...
```

### 2. Tool Registry (`backend/app/tool_registry.py`)

**Class: `ToolRegistry`**

```python
class ToolRegistry:
    """Maintains approved GIS tools and validates operations."""
    
    def __init__(self):
        """Builds registry of approved tools."""
    
    def get_tool(operation_id: str) -> ToolDefinition:
        """Get tool by operation ID."""
    
    def validate_and_get_tool(operation_id: str, parameters: dict):
        """Validate and get tool with validated parameters."""
```

**Approved Tools (8 total):**

| Tool | Operation ID | Required Params | Validators |
|------|--------|--------|----------|
| Population Stats | `get_population_statistics` | target_area | valid_area |
| High Pop Areas | `find_high_population_areas` | target_area, percentile | valid_area, is_percentile |
| Pop Near Hospitals | `calculate_population_near_hospitals` | target_area, distance_km | valid_area, positive_float |
| Accessibility | `analyze_hospital_accessibility` | target_area, distance_km | valid_area, positive_float |
| Gaps | `find_healthcare_gaps` | target_area | valid_area |
| Suitability | `calculate_site_suitability` | target_area | valid_area |
| Nearby | `find_nearby` | all 4 params | layer_enum, positive_float |
| Show Layer | `show_layer` | target_area, target_layer | valid_area, layer_enum |

**Class: `OperationValidator`**

```python
class OperationValidator:
    """Validates operations and prevents unsafe operations."""
    
    APPROVED_OPERATIONS = {
        "find_healthcare_gaps",
        "find_high_population_areas",
        # ... (8 total)
    }
    
    BLOCKED_OPERATIONS = {
        "execute_sql",
        "drop_table",
        "delete_database",
        # ...
    }
    
    @staticmethod
    def validate_operation(operation: str) -> bool:
        """Validate operation is approved."""
    
    @staticmethod
    def validate_query_for_injection(query: str) -> bool:
        """Detect SQL injection patterns."""
```

**Extending Tool Registry:**
To add a new tool:

1. Add ToolDefinition to `_build_tool_registry()`:
```python
"new_tool": ToolDefinition(
    name="New Tool Name",
    description="What it does",
    operation_id="new_operation",
    requires_parameters=["param1", "param2"],
    optional_parameters=["param3"],
    parameter_validators={
        "param1": is_valid_type,
        "param2": is_valid_range,
    }
)
```

2. Add to OperationValidator.APPROVED_OPERATIONS:
```python
APPROVED_OPERATIONS = {
    # ... existing ...
    "new_operation",  # Add here
}
```

### 3. Enhanced Agent (`agent/enhanced_agent.py`)

**Class: `EnhancedGeoAIAgent`**

```python
class EnhancedGeoAIAgent:
    """Orchestrates end-to-end natural language query processing."""
    
    def __init__(self, service: GISService | None = None):
        """Initialize with GIS service."""
        self.service = service or GISService()
        self.parser = IntentParser()
        self.registry = get_tool_registry()
    
    def process_query(query: str, context: dict | None = None) -> dict:
        """Main entry point for query processing."""
```

**Processing Pipeline:**

```python
def process_query(self, query: str, context: dict | None = None):
    # Step 1: Parse intent
    intent = self.parser.parse(query, context)
    
    # Step 2: Validate operation
    if not intent.supported:
        return self._build_unsupported_response(query, intent)
    
    OperationValidator.validate_operation(intent.operation)
    
    # Step 3: Handle RAG queries
    if intent.requires_rag or intent.analysis_type == AnalysisType.RAG:
        return self._handle_rag_query(query, intent)
    
    # Step 4: Extract & validate parameters
    parameters = self._extract_parameters(intent)
    tool, validated_params = self.registry.validate_and_get_tool(
        intent.operation, 
        parameters
    )
    
    # Step 5: Execute operation
    result = self._execute_operation(intent, validated_params)
    
    # Step 6: Build response
    return self._build_response(query, intent, tool, result, validated_params)
```

**Key Methods:**

```python
def _extract_parameters(intent: StructuredIntent) -> dict:
    """Convert intent to tool parameters."""

def _execute_operation(intent: StructuredIntent, parameters: dict) -> dict:
    """Execute GIS operation based on intent."""

def _handle_rag_query(query: str, intent: StructuredIntent) -> dict:
    """Handle knowledge-base queries."""

def _build_response(...) -> dict:
    """Format final API response."""

def _build_interpretation(intent: StructuredIntent, parameters: dict) -> str:
    """Create human-readable interpretation."""

def get_available_operations() -> dict:
    """List all available operations."""

def get_example_queries() -> list:
    """Get example queries system can handle."""
```

**Extending Agent:**
To add operation execution:

1. Add to `_execute_operation()`:
```python
elif operation == "new_operation":
    return self.service.new_method(
        param1=parameters.get("param1"),
        param2=parameters.get("param2")
    )
```

2. Ensure GISService has method:
```python
# In backend/app/gis_tools.py
class GISService:
    def new_method(self, param1, param2) -> dict:
        """Execute new operation."""
        # Implementation
        return {
            "explanation": "...",
            "result_count": N,
            "geojson": {...},
            "summary": {...},
            "sources": [...]
        }
```

---

## API Integration

### Endpoints

#### 1. `/api/query/natural-language` (POST)

**Request:**
```json
{
  "query": "Show high population areas",
  "context": {}
}
```

**Response:**
```json
{
  "query": "Show high population areas",
  "mode": "demo",
  "interpreted_request": "Find areas in top 75% population density",
  "intent": {
    "operation": "find_high_population_areas",
    "analysis_type": "raster",
    "confidence": 0.85
  },
  "analysis_type": "raster",
  "tools_selected": ["High-Population Areas"],
  "result_count": 25,
  "geojson": {...},
  "explanation": "...",
  "summary": {...},
  "supported": true
}
```

#### 2. `/api/query/operations` (GET)

**Response:**
```json
{
  "operations": {
    "operation_id": "description",
    ...
  },
  "examples": ["query1", "query2", ...]
}
```

#### 3. `/api/query/examples` (GET)

**Response:**
```json
{
  "examples": ["query1", "query2", ...],
  "description": "Example queries that demonstrate..."
}
```

### Integration in `backend/app/main.py`

```python
from agent.enhanced_agent import EnhancedGeoAIAgent

# Initialize enhanced agent
enhanced_agent = EnhancedGeoAIAgent(service=service)

# Define endpoints
@app.post("/api/query/natural-language")
def natural_language_query(request: ChatRequest) -> dict[str, Any]:
    return enhanced_agent.process_query(request.query, request.context)

@app.get("/api/query/operations")
def list_operations() -> dict[str, Any]:
    return {
        "operations": enhanced_agent.get_available_operations(),
        "examples": enhanced_agent.get_example_queries(),
    }

@app.get("/api/query/examples")
def get_examples() -> dict[str, Any]:
    return {
        "examples": enhanced_agent.get_example_queries(),
        "description": "Example queries that demonstrate..."
    }
```

---

## Testing & Debugging

### Running Tests

```bash
# Full test suite
python scripts/test_natural_language.py

# Test specific component
python -c "
from backend.app.intent_parser import IntentParser
parser = IntentParser()
intent = parser.parse('Show high population areas')
print(f'Operation: {intent.operation}')
print(f'Confidence: {intent.confidence}')
"
```

### Test Coverage

**Test File:** `scripts/test_natural_language.py`

**Tests:**
1. Intent Parsing (9 queries)
2. Operation Validation (7 approved + 3 blocked)
3. Parameter Validation (valid + invalid cases)
4. SQL Injection Prevention (4 dangerous queries)
5. Available Operations (8 operations)
6. Intent to Parameters (3 complex queries)
7. End-to-End Processing (3 full queries)

### Debugging

**Enable Debug Logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then process query
result = enhanced_agent.process_query("Show high population areas")
# Output will show detailed processing steps
```

**Inspect Intent:**
```python
from backend.app.intent_parser import IntentParser

parser = IntentParser()
intent = parser.parse("Your query here")

print(f"Operation: {intent.operation}")
print(f"Type: {intent.analysis_type}")
print(f"Confidence: {intent.confidence:.1%}")
print(f"Supported: {intent.supported}")
print(f"Parameters:")
print(f"  - distance_km: {intent.distance_km}")
print(f"  - percentile: {intent.percentile}")
print(f"  - population_threshold: {intent.population_threshold}")
```

**Inspect Validation:**
```python
from backend.app.tool_registry import get_tool_registry, OperationValidator

registry = get_tool_registry()
validator = OperationValidator()

# Check operation is approved
try:
    validator.validate_operation("find_high_population_areas")
    print("✓ Operation approved")
except ValidationError as e:
    print(f"✗ Operation rejected: {e}")

# Check parameters
try:
    tool, params = registry.validate_and_get_tool(
        "find_high_population_areas",
        {"target_area": "Pune", "percentile": 75.0}
    )
    print(f"✓ Parameters valid")
    print(f"  Tool: {tool.name}")
except ValidationError as e:
    print(f"✗ Validation failed: {e}")
```

---

## Security Considerations

### SQL Injection Prevention

The system blocks these patterns:
- `DROP TABLE`, `DELETE`, `INSERT`, `UPDATE`
- `EXEC()`, `EXECUTE()`
- `--` (SQL comments)
- `/* */` (block comments)
- `UNION SELECT`

**Testing:**
```python
from backend.app.tool_registry import OperationValidator

dangerous_queries = [
    "Show hospitals; DROP TABLE hospitals;",
    "Find areas WHERE 1=1; DELETE FROM hospitals;",
]

for query in dangerous_queries:
    try:
        OperationValidator.validate_query_for_injection(query)
        print("✗ Should have blocked!")
    except ValidationError:
        print("✓ Blocked malicious query")
```

### Operation Whitelisting

Only these operations are allowed:
```python
APPROVED_OPERATIONS = {
    "get_population_statistics",
    "find_high_population_areas",
    "calculate_population_near_hospitals",
    "analyze_hospital_accessibility",
    "find_healthcare_gaps",
    "calculate_site_suitability",
    "find_nearby",
    "show_layer",
}
```

Attempting any other operation raises `ValidationError`.

### Parameter Validation

All parameters checked before execution:
- Type: string, float, enum
- Range: 0-100 for percentiles
- Required: Must be present
- Format: Matches expected pattern

---

## Performance Optimization

### Caching

Current: No caching (queries are unique)

**Future Enhancement:**
```python
class CachedIntentParser(IntentParser):
    def __init__(self):
        super().__init__()
        self.cache = {}  # Query → Intent mapping
    
    def parse(self, query: str, context: dict):
        if query in self.cache:
            return self.cache[query]
        
        intent = super().parse(query, context)
        self.cache[query] = intent
        return intent
```

### Lazy Loading

Tool registry loaded on first use:
```python
_tool_registry = None

def get_tool_registry():
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
```

---

## Documentation Structure

```
NATURAL_LANGUAGE_INTERFACE.md
  ├─ System Architecture
  ├─ Component Overview
  ├─ Usage Examples
  ├─ REST API Reference
  ├─ Parameter Extraction
  ├─ Security Features
  ├─ Query Patterns
  └─ Future Enhancements

NATURAL_LANGUAGE_QUICK_REF.md
  ├─ Quick Start
  ├─ Query Examples
  ├─ Python/JavaScript Examples
  ├─ Common Scenarios
  ├─ Troubleshooting
  └─ API Reference

NATURAL_LANGUAGE_IMPLEMENTATION.md
  ├─ Project Completion
  ├─ Components Built
  ├─ Key Features
  ├─ Security Analysis
  ├─ Test Coverage
  └─ Deployment Instructions

This File (NATURAL_LANGUAGE_DEVELOPER_GUIDE.md)
  ├─ Architecture Overview
  ├─ Core Components
  ├─ API Integration
  ├─ Testing & Debugging
  ├─ Security Considerations
  ├─ Performance Optimization
  └─ Documentation Structure
```

---

## Common Development Tasks

### Add New Query Pattern

1. **Identify pattern** - What should the query sound like?
2. **Add parser method** - Implement `_match_xxx_pattern()`
3. **Add to pattern matching** - Call in `_match_patterns()`
4. **Add tool definition** - Register in ToolRegistry
5. **Add operation handler** - Implement in `_execute_operation()`
6. **Test** - Add test case to test suite

### Add New GIS Operation

1. **Implement GIS method** - Add to GISService
2. **Register tool** - Add ToolDefinition to registry
3. **Add operation handler** - Route in enhanced agent
4. **Add intent pattern** - Parser recognizes query type
5. **Add validation** - Parameter validators
6. **Test** - Full end-to-end test

### Add New Parameter Type

1. **Update IntentParser** - Add extraction method
2. **Update StructuredIntent** - Add field
3. **Update Tool Registry** - Add validator
4. **Update Agent** - Handle in `_extract_parameters()`
5. **Test** - Parameter validation test

---

## Troubleshooting Guide

### Query Not Recognized

**Symptom:** Query returns unsupported

**Debug:**
```python
parser = IntentParser()
intent = parser.parse("your query")
print(f"Operation: {intent.operation}")
print(f"Supported: {intent.supported}")
print(f"Confidence: {intent.confidence}")
```

**Solution:** Add pattern to IntentParser if query is valid

### Parameter Extraction Wrong

**Symptom:** Percentile parsed as 75 when user said 80

**Debug:**
```python
parser = IntentParser()
intent = parser.parse("Show areas at 80 percentile")
print(f"Percentile: {intent.percentile}")
```

**Solution:** Check extraction method, may need regex update

### Validation Failure

**Symptom:** Valid query rejected with validation error

**Debug:**
```python
registry = get_tool_registry()
tool, params = registry.validate_and_get_tool(
    "operation_id",
    {"param": "value"}
)  # Will raise ValidationError with details
```

**Solution:** Check parameter validators in ToolDefinition

---

## Contributing

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Keep methods <50 lines

### Adding Features
1. Create feature branch
2. Implement with tests
3. Run full test suite
4. Document changes
5. Submit PR

### Testing Requirements
- New code must have tests
- All tests must pass
- SQL injection tests for any input handling
- Performance tests for new operations

---

## Summary

The natural language interface provides:

✅ **Extensible Architecture** - Easy to add new patterns and operations
✅ **Secure by Default** - SQL injection prevention, operation whitelisting
✅ **Well Tested** - Comprehensive test suite with 30+ test cases
✅ **Well Documented** - Multiple documentation files for different audiences
✅ **Production Ready** - All code compiled and tested

Developers can:
1. Understand the system flow
2. Extend with new query patterns
3. Add new GIS operations
4. Maintain security & correctness
5. Optimize performance

For questions, refer to:
- Architecture: `NATURAL_LANGUAGE_INTERFACE.md`
- Quick ref: `NATURAL_LANGUAGE_QUICK_REF.md`
- Implementation: `NATURAL_LANGUAGE_IMPLEMENTATION.md`
- Code: Inline comments in source files
