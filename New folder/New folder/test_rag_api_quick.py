#!/usr/bin/env python3
"""Test RAG API endpoint."""

import requests
import json
import time

time.sleep(2)  # Wait for server to be ready

BASE_URL = "http://127.0.0.1:8000"

test_queries = [
    ("What is raster data?", "GIS Concepts"),
    ("What dataset provides population information?", "WorldPop Dataset Documentation"),
    ("What is OpenStreetMap?", "OpenStreetMap Foundation"),
    ("Explain the hospital site-selection methodology.", "Hospital Site Selection Methodology"),
]

print("\n" + "="*70)
print("Testing RAG Queries via /api/query/natural-language")
print("="*70)

passed = 0
failed = 0

for query, expected_source in test_queries:
    print(f"\nQuery: {query}")
    print(f"Expected source: {expected_source}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/query/natural-language",
            json={"query": query, "context": {}},
            timeout=10
        )
        
        data = response.json()
        
        if response.status_code == 200:
            # Check if it's a RAG response
            if "result" in data or "explanation" in data or "error" in data:
                answer = data.get("result") or data.get("explanation") or data.get("error", "")
                source = data.get("source", "")
                
                if "Operation 'rag' is not supported" in answer or "Operation 'rag' is not supported" in str(data):
                    print(f"✗ FAILED: {answer}")
                    failed += 1
                else:
                    print(f"✓ SUCCESS")
                    print(f"  Source: {source}")
                    print(f"  Answer preview: {answer[:100]}...")
                    
                    if expected_source in source:
                        print(f"  ✓ Source matches!")
                        passed += 1
                    else:
                        print(f"  ⚠ Source mismatch")
                        failed += 1
            else:
                print(f"✗ Unexpected response format")
                print(json.dumps(data, indent=2)[:200])
                failed += 1
        else:
            print(f"✗ HTTP {response.status_code}")
            print(f"  {data}")
            failed += 1
            
    except Exception as e:
        print(f"✗ Error: {e}")
        failed += 1

print(f"\n{'='*70}")
print(f"Results: {passed} passed, {failed} failed")
print("="*70 + "\n")
