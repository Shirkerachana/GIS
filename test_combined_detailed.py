#!/usr/bin/env python3
"""Detailed test of combined GIS+RAG queries."""

import requests
import json
import time

time.sleep(2)

BASE_URL = "http://127.0.0.1:8000"

print("\n" + "="*80)
print("Detailed Combined Query Test")
print("="*80 + "\n")

# Test a combined query in detail
query = "Find the best hospital location and explain the methodology."
print(f"Query: {query}\n")

try:
    response = requests.post(
        f"{BASE_URL}/api/query/natural-language",
        json={"query": query, "context": {}},
        timeout=10
    )
    
    data = response.json()
    
    print(f"Status: {response.status_code}\n")
    
    print("Full Response Structure:")
    print("-" * 80)
    
    # Print selected fields
    if "intent" in data:
        print(f"Operation: {data['intent'].get('operation')}")
        print(f"Analysis Type: {data['intent'].get('analysis_type')}")
        print(f"Requires RAG: {data['intent'].get('requires_rag')}")
    
    print(f"\nInterpretation: {data.get('interpreted_request')}")
    
    print(f"\nResult Type: {data.get('result_type')}")
    print(f"Result Count: {data.get('result_count')}")
    
    print(f"\nExplanation:\n{data.get('explanation', '')[:500]}...\n")
    
    print(f"Sources: {data.get('sources', [])}")
    
    print(f"\nGeoJSON Features: {len(data.get('geojson', {}).get('features', []))}")
    
    # Check if it has both spatial and RAG components
    has_methodology = "methodology" in (data.get('explanation') or '').lower()
    has_spatial = data.get('result_count', 0) > 0 or len(data.get('geojson', {}).get('features', [])) > 0
    
    print(f"\n✓ Has methodology explanation: {has_methodology}")
    print(f"✓ Has spatial results: {has_spatial}")
    print(f"✓ Combined query working: {has_methodology and has_spatial}")
    
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80 + "\n")
