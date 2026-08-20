"""
Test suite for enhanced natural language interface.

Tests the intent parser, tool registry validation, and end-to-end query processing.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.intent_parser import (
    AnalysisType,
    IntentParser,
    extract_intent_from_query,
)
from backend.app.tool_registry import (
    OperationValidator,
    ToolRegistry,
    ValidationError,
    get_tool_registry,
)
from agent.enhanced_agent import EnhancedGeoAIAgent
from backend.app.gis_tools import GISService


def print_section(title: str):
    """Print a formatted section title."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def test_intent_parsing():
    """Test natural language query parsing."""
    print_section("TEST 1: Intent Parsing")
    
    parser = IntentParser()
    test_queries = [
        "Show high population areas in Pune",
        "Find hospitals in high population areas",
        "Find areas with high population but poor hospital accessibility",
        "Find the best location for a new hospital",
        "Find hospitals within 5 km of major roads",
        "Find hospitals near rivers",
        "Show all hospitals in Pune",
        "What is WorldPop data?",
        "How does hospital accessibility work?",
    ]
    
    for query in test_queries:
        intent = parser.parse(query)
        print(f"\n  Query: {query}")
        print(f"  → Operation: {intent.operation}")
        print(f"  → Analysis Type: {intent.analysis_type.value}")
        print(f"  → Confidence: {intent.confidence:.1%}")
        print(f"  → Explanation: {intent.explanation}")
        if intent.distance_km:
            print(f"  → Distance: {intent.distance_km} km")
        if intent.percentile:
            print(f"  → Percentile: {intent.percentile}%")
        print(f"  → Supported: {intent.supported}")


def test_operation_validation():
    """Test operation validation against approved tools."""
    print_section("TEST 2: Operation Validation")
    
    approved_ops = [
        "find_healthcare_gaps",
        "find_high_population_areas",
        "calculate_population_near_hospitals",
        "analyze_hospital_accessibility",
        "calculate_site_suitability",
        "find_nearby",
        "show_layer",
    ]
    
    blocked_ops = [
        "execute_sql",
        "drop_table",
        "delete_database",
    ]
    
    print("\n  Approved Operations:")
    for op in approved_ops:
        try:
            OperationValidator.validate_operation(op)
            print(f"    ✓ {op}")
        except ValidationError as e:
            print(f"    ✗ {op}: {e}")
    
    print("\n  Blocked Operations (should fail):")
    for op in blocked_ops:
        try:
            OperationValidator.validate_operation(op)
            print(f"    ✗ {op}: SHOULD HAVE FAILED!")
        except ValidationError:
            print(f"    ✓ {op}: Correctly blocked")


def test_parameter_validation():
    """Test parameter validation."""
    print_section("TEST 3: Parameter Validation")
    
    registry = get_tool_registry()
    
    # Test valid parameters
    print("\n  Valid Parameters:")
    valid_params = {
        "target_area": "Pune",
        "percentile": 75.0,
    }
    try:
        tool, validated = registry.validate_and_get_tool(
            "find_high_population_areas",
            valid_params
        )
        print(f"    ✓ Validated: {validated}")
        print(f"    ✓ Tool: {tool.name}")
    except ValidationError as e:
        print(f"    ✗ Error: {e}")
    
    # Test invalid percentile (>100)
    print("\n  Invalid Percentile (>100):")
    invalid_params = {
        "target_area": "Pune",
        "percentile": 150.0,  # Invalid: > 100
    }
    try:
        tool, validated = registry.validate_and_get_tool(
            "find_high_population_areas",
            invalid_params
        )
        print(f"    ✗ Should have failed but didn't")
    except ValidationError as e:
        print(f"    ✓ Correctly rejected: {e}")
    
    # Test missing required parameter
    print("\n  Missing Required Parameter:")
    missing_params = {
        "percentile": 75.0,
        # Missing: target_area
    }
    try:
        tool, validated = registry.validate_and_get_tool(
            "find_high_population_areas",
            missing_params
        )
        print(f"    ✗ Should have failed but didn't")
    except ValidationError as e:
        print(f"    ✓ Correctly rejected: {e}")


def test_sql_injection_prevention():
    """Test SQL injection attack prevention."""
    print_section("TEST 4: SQL Injection Prevention")
    
    dangerous_queries = [
        "Show hospitals; DROP TABLE hospitals;",
        "Find areas WHERE 1=1; DELETE FROM hospitals;",
        "Show hospitals /* */ OR 1=1",
        "SELECT * FROM hospitals UNION SELECT * FROM hospitals",
    ]
    
    for query in dangerous_queries:
        try:
            OperationValidator.validate_query_for_injection(query)
            print(f"  ✗ Should have blocked: {query[:50]}...")
        except ValidationError:
            print(f"  ✓ Blocked malicious query: {query[:50]}...")


def test_enhanced_agent():
    """Test end-to-end enhanced agent."""
    print_section("TEST 5: Enhanced Agent End-to-End")
    
    service = GISService(demo_mode=True)
    agent = EnhancedGeoAIAgent(service=service)
    
    test_queries = [
        "Show high population areas in Pune",
        "Find hospitals in high population areas",
        "Find the best location for a new hospital",
    ]
    
    for query in test_queries:
        print(f"\n  Processing: {query}")
        try:
            response = agent.process_query(query)
            print(f"  ✓ Query processed successfully")
            print(f"    - Status: Supported={response.get('supported')}")
            print(f"    - Operation: {response.get('intent', {}).get('operation')}")
            print(f"    - Analysis Type: {response.get('analysis_type')}")
            print(f"    - Tools: {response.get('tools_selected')}")
            print(f"    - Result Count: {response.get('result_count')}")
            if response.get('explanation'):
                explanation = response['explanation'][:100]
                print(f"    - Explanation: {explanation}...")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def test_available_operations():
    """Test listing available operations."""
    print_section("TEST 6: Available Operations")
    
    service = GISService(demo_mode=True)
    agent = EnhancedGeoAIAgent(service=service)
    
    operations = agent.get_available_operations()
    print(f"\n  Total Operations: {len(operations)}")
    
    for op_id, description in list(operations.items())[:5]:
        print(f"    - {op_id}: {description[:60]}...")
    
    examples = agent.get_example_queries()
    print(f"\n  Example Queries ({len(examples)} total):")
    for example in examples:
        print(f"    - {example}")


def test_intent_to_parameters():
    """Test conversion of intent to tool parameters."""
    print_section("TEST 7: Intent to Parameters")
    
    parser = IntentParser()
    queries = [
        ("Find high population areas at 80 percentile", "find_high_population_areas"),
        ("Find hospitals within 10 km of roads", "find_nearby"),
        ("Find healthcare gaps with 5000 min population", "find_healthcare_gaps"),
    ]
    
    for query, expected_op in queries:
        intent = parser.parse(query)
        print(f"\n  Query: {query}")
        print(f"  Operation: {intent.operation}")
        print(f"  Parameters:")
        if intent.distance_km:
            print(f"    - distance_km: {intent.distance_km}")
        if intent.percentile:
            print(f"    - percentile: {intent.percentile}")
        if intent.population_threshold:
            print(f"    - population_threshold: {intent.population_threshold}")
        if intent.target_area:
            print(f"    - target_area: {intent.target_area}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print(" ENHANCED NATURAL LANGUAGE INTERFACE - TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_intent_parsing,
        test_operation_validation,
        test_parameter_validation,
        test_sql_injection_prevention,
        test_available_operations,
        test_intent_to_parameters,
        test_enhanced_agent,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print_section(f"ERROR in {test.__name__}")
            print(f"\n  {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(" TEST SUITE COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
