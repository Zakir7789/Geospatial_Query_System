"""
canonical_mapper.py
-------------------
Identifies and resolves place names from a natural language sentence
using fuzzy matching against canonical tables (countries, states, cities).
"""

import spacy
from nlp.entity_extractor import extract_location_tokens
from nlp.fuzzy_matcher_v1 import hybrid_fuzzy_match
from nlp.query_interpreter import run_query, interpret_query

# Confidence thresholds
RESOLVE_THRESHOLD = 0.75
GAP_THRESHOLD = 0.10   # difference between top-2 scores to auto-resolve


def resolve_token(token: str):
    """Resolve a single token to canonical geospatial entity."""
    candidates = hybrid_fuzzy_match(token)

    if not candidates:
        return {
            "token": token,
            "status": "unresolved",
            "message": "No match found in canonical tables."
        }

    # If only one strong match → resolved
    if len(candidates) == 1 and candidates[0]["final_score"] >= RESOLVE_THRESHOLD:
        return {
            "token": token,
            "status": "resolved",
            "canonical_name": candidates[0]["name"],
            "table": candidates[0]["source"],
            "confidence": candidates[0]["final_score"]
        }

    # If multiple candidates → check top two gap
    candidates = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    top1, top2 = candidates[0], candidates[1] if len(candidates) > 1 else None

    if top2 and (top1["final_score"] - top2["final_score"]) >= GAP_THRESHOLD:
        # Confidently pick top one
        return {
            "token": token,
            "status": "resolved",
            "canonical_name": top1["name"],
            "table": top1["source"],
            "confidence": top1["final_score"]
        }

    # Otherwise, ask for clarification
    return {
        "token": token,
        "status": "clarification_required",
        "candidates": candidates
    }


def generate_canonical_json(sentence: str):
    """Process full query and return structured mapping results."""
    tokens = extract_location_tokens(sentence)

    if not tokens:
        return {"message": "No location-like tokens found in query."}

    results = []
    for token in tokens:
        result = resolve_token(token)
        results.append(result)

    return {
        "query": sentence,
        "results": results
    }

def canonical_pipeline(query: str):
    """
    Full pipeline: query → canonical map → SQL → result
    """
    print("\n🧠 Step 1: Extracting and resolving entities...")
    canonical_json = generate_canonical_json(query)
    print("📜 Canonical JSON:")
    print(canonical_json)

    print("\n🧩 Step 2: Interpreting query to SQL...")
    sql_query = interpret_query(canonical_json)
    print("💾 Generated SQL:\n", sql_query)

    if not sql_query.lower().startswith("select"):
        print("⚠️ No valid SQL generated — skipping execution.")
        return canonical_json

    print("\n🧪 Step 3: Executing SQL query...")
    results = run_query(sql_query)
    print("✅ Query Results:")
    for row in results[:10]:  # show top 10 for readability
        print(row)

    return {"canonical_json": canonical_json, "sql_query": sql_query, "results": results}


if __name__ == "__main__":
    query = "Which of the following has the highest population — Maharashtra, Ahmedabad or India?"
    pipeline_output = canonical_pipeline(query)
