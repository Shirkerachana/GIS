#!/usr/bin/env python3
"""Debug which knowledge keyword is matching."""

query = "show hospitals in pune."
normalized = query.lower().strip()

knowledge_keywords = ["explain", "methodology", "method", "what is", "how"]

print(f"Query: {query}")
print(f"Normalized: {normalized}\n")

for kw in knowledge_keywords:
    if kw in normalized:
        print(f"✓ Found '{kw}' in query")
    else:
        print(f"✗ '{kw}' not found")

result = any(kw in normalized for kw in knowledge_keywords)
print(f"\nResult: {result}")
