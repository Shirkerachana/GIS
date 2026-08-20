#!/usr/bin/env python3
"""Debug RAG query matching."""

from rag.rag_engine import answer_rag_query

queries = [
    "Explain the hospital site-selection methodology.",
    "hospital site selection methodology",
    "hospital site-selection",
    "What is hospital site selection?",
]

print("Testing RAG query matching:")
print("=" * 70)

for q in queries:
    result = answer_rag_query(q)
    print(f"Query: {q}")
    print(f"Source: {result['source']}")
    print(f"Answer: {result['answer'][:100]}...\n")

print("=" * 70)
