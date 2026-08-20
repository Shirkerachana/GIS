#!/usr/bin/env python3
"""Debug show hospitals query with detailed tracing."""

from backend.app.intent_parser import IntentParser

parser = IntentParser()

query = "Show hospitals in Pune."
normalized = query.lower().strip()

print(f"Query: {query}")
print(f"Normalized: {normalized}\n")

# Test _match_single_layer directly
layer_intent = parser._match_single_layer(normalized)
print(f"_match_single_layer result: {layer_intent}")

if layer_intent:
    print(f"  Operation: {layer_intent.operation}")
    print(f"  Target Layer: {layer_intent.target_layer}")
else:
    print("  Returned None")

# Check the knowledge keywords logic
knowledge_keywords = ["explain", "methodology", "method", "what is", "how"]
has_knowledge = any(kw in normalized for kw in knowledge_keywords)
print(f"\nHas knowledge keywords: {has_knowledge}")

# Test hospital pattern
import re
hospital_pattern = r"hospital"
matches_hospital = re.search(hospital_pattern, normalized)
print(f"Matches hospital pattern: {matches_hospital}")
