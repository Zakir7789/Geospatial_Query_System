import re
from difflib import SequenceMatcher
from db import get_connection

# -----------------------
# Stopword list
# -----------------------
STOPWORDS = {
    "give", "show", "list", "display", "tell", "get", "find",
    "fetch", "return", "population", "area", "capital", "country",
    "state", "city", "province", "information", "data"
}

# -----------------------
# Tokenizer
# -----------------------
def tokenize(text):
    tokens = re.findall(r'\b\w+\b', text)
    # filter out stopwords
    return [t for t in tokens if t.lower() not in STOPWORDS]

# -----------------------
# Similarity
# -----------------------
def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# -----------------------
# Candidate Generator
# -----------------------
def get_candidates(token, cursor):
    candidates = []

    # Search in City table
    cursor.execute("SELECT name FROM City")
    for (name,) in cursor.fetchall():
        sim = similarity(token, name)
        if sim > 0.6:
            candidates.append((name, "City", sim))

    # Search in State table
    cursor.execute("SELECT name FROM State")
    for (name,) in cursor.fetchall():
        sim = similarity(token, name)
        if sim > 0.6:
            candidates.append((name, "State", sim))

    # Search in Country table
    cursor.execute("SELECT name FROM Country")
    for (name,) in cursor.fetchall():
        sim = similarity(token, name)
        if sim > 0.6:
            candidates.append((name, "Country", sim))

    return candidates

# -----------------------
# Resolver
# -----------------------
def resolve_entities(query):
    tokens = tokenize(query)

    conn = get_connection()
    cursor = conn.cursor()

    resolved = []
    for token in tokens:
        candidates = get_candidates(token, cursor)

        ranked = sorted(candidates, key=lambda x: x[2], reverse=True)
        result = {
            "token": token,
            "normalized": token,
            "candidates": [
                {"token": token, "canonical": name, "table": table, "confidence": round(sim*100, 2)}
                for name, table, sim in ranked
            ],
            "chosen": None
        }

        if ranked and ranked[0][2] > 0.75:  # high-confidence match
            best = ranked[0]
            result["chosen"] = {
                "token": token,
                "chosen": best[0],
                "table": best[1],
                "confidence": round(best[2]*100, 2)
            }
        else:
            result["chosen"] = {
                "token": token,
                "chosen": None,
                "reason": f"No strong match (best={ranked[0][0] if ranked else 'None'}, score={round(ranked[0][2]*100, 2) if ranked else 0})"
            }

        resolved.append(result)

    conn.close()
    return resolved

# -----------------------
# Quick Test
# -----------------------
if __name__ == "__main__":
    query = "Give me the population of Washington"
    entities = resolve_entities(query)
    print("Input Query:", query)
    print("Resolved Entities:")
    for e in entities:
        print(e)
