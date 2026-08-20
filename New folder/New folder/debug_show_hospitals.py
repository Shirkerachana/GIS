#!/usr/bin/env python3
"""Debug show hospitals query."""

from backend.app.intent_parser import IntentParser

parser = IntentParser()

queries = [
    "Show hospitals in Pune.",
    "show hospitals",
    "display hospitals",
]

for q in queries:
    intent = parser.parse(q, {})
    print(f"Query: {q}")
    print(f"Operation: {intent.operation}")
    print(f"Analysis Type: {intent.analysis_type}")
    print(f"Supported: {intent.supported}")
    print(f"Explanation: {intent.explanation}")
    print()
