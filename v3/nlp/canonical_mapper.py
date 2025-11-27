"""
canonical_mapper_v1.py
-------------------
Identifies and resolves place names from a natural language sentence
using fuzzy matching against canonical tables (countries, states, cities).
"""

import spacy
from nlp.fuzzy_matcher_v1 import hybrid_fuzzy_match

# Load SpaCy small English model (run "python -m spacy download en_core_web_sm" if not installed)
nlp = spacy.load("en_core_web_trf")

# Confidence thresholds
RESOLVE_THRESHOLD = 0.75
GAP_THRESHOLD = 0.10   # difference between top-2 scores to auto-resolve


def extract_location_tokens(sentence: str):
    """Extract potential place-name tokens using SpaCy NER and fallback heuristics."""
    doc = nlp(sentence)
    tokens = set()

    # Named Entity Recognition (NER)
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:  # Geopolitical entity or location
            tokens.add(ent.text)

    # Fallback: capitalized tokens not in common stopwords
    if not tokens:
        for token in doc:
            if token.is_title and not token.is_stop and token.is_alpha:
                tokens.add(token.text)

    return list(tokens)


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


def process_query(sentence: str):
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


# Example usage
if __name__ == "__main__":
    query = "Which of the following saw the highest average temperature in January, Georgia, Maharashtra, Ahmedabad, cote d ivore or entire New Zealand ?"
    output = process_query(query)
    print(output)
