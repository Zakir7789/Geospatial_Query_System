import re
from rapidfuzz import fuzz, process
from db import get_all_entities


# -------------------------------
# Token Normalization
# -------------------------------
def normalize_token(token: str) -> str:
    """Normalize input token for better matching."""
    token = token.replace("-", " ")               # Replace hyphen with space
    token = re.sub(r"[^\w\s]", "", token)         # Remove punctuation
    return token.strip().title()                  # Standardize casing


# -------------------------------
# Candidate Finder
# -------------------------------
def find_candidates(token, universe, limit=5):
    candidates = []
    for table, entries in universe.items():
        names = [e['name'] for e in entries]
        matches = process.extract(token, names, scorer=fuzz.token_sort_ratio, limit=limit)

        for match, score, _ in matches:
            candidates.append({
                "token": token,
                "canonical": match,
                "table": table,
                "confidence": score
            })
    # Sort by confidence descending
    return sorted(candidates, key=lambda x: x['confidence'], reverse=True)


# -------------------------------
# Disambiguation Logic
# -------------------------------
def disambiguate(token, candidates, query, min_conf=85):
    if not candidates:
        return None

    query_lower = query.lower()

    # Rule 1: Explicit context keyword in query
    for cand in candidates:
        if cand['table'].lower() in query_lower:
            return cand

    # Rule 2: Prefer Country > State > City when scores are similar
    priority = {"Country": 3, "State": 2, "City": 1}
    candidates = sorted(
        candidates,
        key=lambda x: (x['confidence'], priority.get(x['table'], 0)),
        reverse=True
    )

    best = candidates[0]

    # Rule 3: Only return if confidence is strong enough
    if best['confidence'] >= min_conf:
        return best

    return None


# -------------------------------
# Entity Resolver Pipeline
# -------------------------------
def resolve_entities(query, tokens):
    universe = get_all_entities()
    resolved = []

    for token in tokens:
        normalized = normalize_token(token)
        candidates = find_candidates(normalized, universe)

        chosen = disambiguate(normalized, candidates, query)

        resolved.append({
            "token": token,
            "normalized": normalized,
            "candidates": candidates,
            "chosen": chosen
        })

    return resolved


# -------------------------------
# Example Run
# -------------------------------
if __name__ == "__main__":
    query1 = "Which of the following saw the highest average temperature in January, Maharashtra, Ahmedabad or entire New-Zealand?"
    query2 = "Show me the rainfall in Delhi state during October."
    query3 = "Give me the population of Washington."

    test_cases = {
        query1: ["Maharashtra", "Ahmedabad", "New-Zealand"],
        query2: ["Delhi"],
        query3: ["Washington"]
    }

    for q, toks in test_cases.items():
        print(f"\nInput Query: {q}\n")
        results = resolve_entities(q, toks)
        for r in results:
            print(f"Token: {r['token']}")
            print("Candidates:", r['candidates'][:3])  # show top 3
            print("Chosen:", r['chosen'])
            print("=" * 80)
