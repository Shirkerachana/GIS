#!/usr/bin/env python3
"""Test combined GIS+RAG queries via API."""

import requests
import json
import time

time.sleep(2)

BASE_URL = "http://127.0.0.1:8000"

test_queries = [
    # Pure RAG queries
    ("What is raster data?", "rag", "GIS Concepts"),
    ("What dataset provides population information?", "rag", "WorldPop Dataset Documentation"),
    
    # Spatial queries
    ("Show hospitals in Pune.", "find_hospitals", None),
    ("Find high population areas.", "find_high_population_areas", None),
    
    # Combined GIS+RAG queries (these should route to spatial operations and include RAG explanation)
    ("Find the best hospital location and explain the methodology.", "site_suitability_with_explanation", "Hospital Site Selection Methodology"),
]

print("\n" + "="*80)
print("Testing Complete Query Routing: RAG, Spatial, and Combined Queries")
print("="*80)

passed = 0
failed = 0

for query, expected_operation, expected_source in test_queries:
    print(f"\nQuery: {query}")
    print(f"Expected: {expected_operation}")
    if expected_source:
        print(f"Expected source: {expected_source}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/query/natural-language",
            json={"query": query, "context": {}},
            timeout=10
        )
        
        data = response.json()
        
        if response.status_code == 200:
            # Get operation from response
            actual_operation = None
            if "intent" in data and "operation" in data["intent"]:
                actual_operation = data["intent"]["operation"]
            
            result_preview = (data.get("result") or data.get("explanation") or data.get("error") or "")
            if isinstance(result_preview, dict):
                result_preview = str(result_preview)[:100]
            else:
                result_preview = str(result_preview)[:100]
            
            source = data.get("source", "")
            
            # Check for errors
            if "error" in data and "not supported" in data["error"]:
                print(f"✗ FAILED: {data['error']}")
                failed += 1
            else:
                print(f"✓ SUCCESS")
                if actual_operation:
                    print(f"  Operation: {actual_operation}")
                    if actual_operation == expected_operation:
                        print(f"  ✓ Operation matches!")
                    else:
                        print(f"  ⚠ Operation mismatch (expected {expected_operation})")
                
                if source:
                    print(f"  Source: {source}")
                    if expected_source and expected_source in source:
                        print(f"  ✓ Source matches!")
                    elif expected_source:
                        print(f"  ⚠ Source mismatch (expected {expected_source})")
                
                print(f"  Result preview: {result_preview}...")
                passed += 1
                
        else:
            print(f"✗ HTTP {response.status_code}")
            print(f"  {data}")
            failed += 1
            
    except Exception as e:
        print(f"✗ Error: {e}")
        failed += 1

print(f"\n{'='*80}")
print(f"Results: {passed} passed, {failed} failed")
print("="*80 + "\n")
