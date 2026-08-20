#!/usr/bin/env python
"""Test script for RAG knowledge base retrieval."""

from rag.rag_engine import answer_rag_query

# Test knowledge base queries
test_queries = [
    'What is raster data?',
    'What dataset provides population?',
    'Tell me about OpenStreetMap.',
    'Explain hospital site selection.',
    'What is PostGIS?',
    'Spatial buffer',
]

print('Testing RAG Knowledge Base:')
print('=' * 70)
for query in test_queries:
    result = answer_rag_query(query)
    source = result['source']
    answer = result['answer'][:80] + '...' if len(result['answer']) > 80 else result['answer']
    print(f'\nQuery: {query}')
    print(f'Source: {source}')
    print(f'Answer: {answer}')
print('\n' + '=' * 70)
print('RAG Knowledge Base test completed successfully!')
