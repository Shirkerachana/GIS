#!/usr/bin/env python3
"""Test RAG queries through the backend API."""

import requests
import json
import time
import subprocess
import sys
from pathlib import Path

# Start the server
print("Starting backend server...")
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
    cwd=Path(__file__).parent,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for server to start
time.sleep(5)

try:
    BASE_URL = "http://127.0.0.1:8000"
    
    test_queries = [
        # RAG-only queries
        {
            "query": "What is raster data?",
            "expected_source": "GIS Concepts",
            "description": "Test basic raster data knowledge query"
        },
        {
            "query": "What dataset provides population information?",
            "expected_source": "WorldPop Dataset Documentation",
            "description": "Test dataset knowledge query"
        },
        {
            "query": "What is OpenStreetMap?",
            "expected_source": "OpenStreetMap Foundation",
            "description": "Test OSM knowledge query"
        },
        {
            "query": "Tell me about the hospital site-selection methodology.",
            "expected_source": "Hospital Site Selection Methodology",
            "description": "Test methodology knowledge query"
        },
    ]
    
    print("\n" + "="*70)
    print("Testing RAG Queries via /api/query/natural-language")
    print("="*70 + "\n")
    
    passed = 0
    failed = 0
    
    for test in test_queries:
        print(f"Test: {test['description']}")
        print(f"Query: {test['query']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/query/natural-language",
                json={"query": test["query"], "context": {}},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response contains expected fields
                if "result" in data or "explanation" in data:
                    answer = data.get("result") or data.get("explanation", "")
                    source = data.get("source", "")
                    
                    print(f"✓ Success")
                    print(f"  Source: {source}")
                    print(f"  Answer: {answer[:100]}...")
                    
                    if test["expected_source"] in source:
                        print(f"  ✓ Source matches expected: {test['expected_source']}")
                        passed += 1
                    else:
                        print(f"  ⚠ Source mismatch. Expected: {test['expected_source']}")
                        print(f"    Got: {source}")
                        failed += 1
                else:
                    print(f"✗ Error: Unexpected response format")
                    print(f"  Response: {json.dumps(data, indent=2)}")
                    failed += 1
            else:
                print(f"✗ HTTP Error {response.status_code}")
                print(f"  Response: {response.text}")
                failed += 1
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Request failed: {e}")
            failed += 1
        
        print()
    
    print("="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
finally:
    # Stop the server
    print("\nStopping server...")
    server_process.terminate()
    server_process.wait(timeout=5)
