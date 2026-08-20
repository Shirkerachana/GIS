#!/usr/bin/env python
"""Test script for agent query routing logic."""

from agent.geoai_agent import GeoAIAgent

# Test query routing
test_cases = [
    # Knowledge queries
    ('What is raster data?', 'rag'),
    ('What dataset provides population?', 'rag'),
    ('Tell me about OpenStreetMap.', 'rag'),
    ('Explain hospital site selection.', 'rag'),
    
    # Spatial queries
    ('Show hospitals in Pune.', 'find_hospitals'),
    ('Find high population areas.', 'find_high_population_areas'),
    ('Find hospitals within 5 km of major roads.', 'find_nearby'),
    ('Find the best location for a new hospital.', 'site_suitability'),
    
    # Combined queries (GIS + RAG)
    ('Find the best hospital location and explain the methodology.', 'site_suitability_with_explanation'),
]

print('Testing Agent Query Routing:')
print('=' * 70)

agent = GeoAIAgent()
for query, expected_operation in test_cases:
    intent = agent.parse_intent(query)
    operation = intent.operation
    wants_rag = intent.wants_rag
    
    status = '✓' if operation == expected_operation else '✗'
    print(f'\n{status} Query: {query}')
    print(f'  Expected: {expected_operation} | Actual: {operation}')
    if wants_rag:
        print(f'  RAG: Yes')

print('\n' + '=' * 70)
print('Agent routing test completed!')
