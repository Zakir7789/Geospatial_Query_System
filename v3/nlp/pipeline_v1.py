
import spacy
from scripts.db_config import connect_db
from rapidfuzz import process, fuzz

# Configurable parameters
DB_LIMIT = 50          # number of candidates fetched from PostgreSQL
TOP_K_RESULTS = 5      # number of results returned after RapidFuzz re-ranking
TRGM_THRESHOLD = 0.3   # minimum trigram similarity to fetch from DB
FINAL_THRESHOLD = 0.7  # minimum final score for acceptance
# Confidence thresholds
RESOLVE_THRESHOLD = 0.75
GAP_THRESHOLD = 0.10

# Load SpaCy small English model (run "python -m spacy download en_core_web_sm" if not installed)
nlp = spacy.load("en_core_web_trf")

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


def hybrid_fuzzy_match(token: str):
    """Performs hybrid fuzzy matching using PostgreSQL + RapidFuzz."""

    token = token.strip().lower()

    conn = connect_db()
    cur = conn.cursor()

    # --- THIS IS THE FIX ---
    # The SQL query was incorrect. This version correctly queries primary names
    # and alternate names using the pg_trgm extension.
    # NOTE: You must run `CREATE EXTENSION IF NOT EXISTS pg_trgm;` in your PostgreSQL database.
    query = f"""
    WITH candidates AS (
        -- Match against primary names
        SELECT country_name AS name, 'countries' AS source, similarity(country_name, %s) AS score
        FROM countries WHERE country_name %% %s
        UNION ALL
        SELECT state_name AS name, 'states' AS source, similarity(state_name, %s) AS score
        FROM states WHERE state_name %% %s
        UNION ALL
        SELECT city_name AS name, 'cities' AS source, similarity(city_name, %s) AS score
        FROM cities WHERE city_name %% %s
        UNION ALL
        -- Match against alternate city names
        SELECT
            c.city_name AS name,
            'cities' AS source,
            similarity(alt_name, %s) AS score
        FROM cities c, unnest(c.alt_names) AS alt_name
        WHERE alt_name %% %s
    )
    SELECT name, source, score
    FROM candidates
    WHERE score >= {TRGM_THRESHOLD}
    ORDER BY score DESC, name
    LIMIT {DB_LIMIT};
    """

    cur.execute(query, [token] * 8)
    db_candidates = cur.fetchall()
    cur.close()
    conn.close()

    if not db_candidates:
        return []

    # --- START OF NEW FIX ---
    # Step 2: Store candidates AND their best DB score
    candidate_lookup = {}
    for name, source, db_score in db_candidates:
        if name not in candidate_lookup:
            # Store the sources AND the best score found in the DB
            candidate_lookup[name] = {'sources': set(), 'best_db_score': 0.0}

        candidate_lookup[name]['sources'].add(source)
        if db_score > candidate_lookup[name]['best_db_score']:
            candidate_lookup[name]['best_db_score'] = db_score

    names = list(candidate_lookup.keys())

    # Re-rank using the more advanced token_sort_ratio
    ranked = process.extract(token, names, scorer=fuzz.token_sort_ratio, limit=TOP_K_RESULTS)

    # Step 3: Combine results, but HONOR perfect DB matches
    results = []
    for name, rapidfuzz_score, _ in ranked:

        final_score = round(rapidfuzz_score / 100, 2)

        # Get the best score we found in the DB (PostgreSQL similarity)
        best_db_score = candidate_lookup[name]['best_db_score']

        # If the DB found a perfect 1.0 match (from alt_names or city_name),
        # use that score, overriding the rapidfuzz score.
        if best_db_score == 1.0:
            final_score = 1.0

        if final_score < FINAL_THRESHOLD:
            continue

        sources = candidate_lookup[name]['sources']

        results.append({
            "name": name,
            "source": ','.join(sources),
            "final_score": final_score
        })
    # --- END OF NEW FIX ---

    return results


def resolve_token(token: str):
    """Resolve a single token to canonical geospatial entity."""
    candidates = hybrid_fuzzy_match(token)

    if not candidates:
        return {
            "token": token,
            "status": "unresolved",
            "message": "No match found in canonical tables."
        }

    # Sort candidates by score
    candidates = sorted(candidates, key=lambda x: x["final_score"], reverse=True)
    top1 = candidates[0]

    # 1️⃣ Perfect match → resolved
    if top1["final_score"] == 1.0 and top1["source"] in ["countries", "states", "cities"]:
        return {
            "token": token,
            "status": "resolved",
            "canonical_name": top1["name"],
            "table": top1["source"],
            "confidence": top1["final_score"]
        }

    # 2️⃣ Only one strong match → resolved
    if len(candidates) == 1 and top1["final_score"] >= RESOLVE_THRESHOLD:
        return {
            "token": token,
            "status": "resolved",
            "canonical_name": top1["name"],
            "table": top1["source"],
            "confidence": top1["final_score"]
        }

    # 3️⃣ Large enough gap → resolved
    top2 = candidates[1] if len(candidates) > 1 else None
    if top2 and (top1["final_score"] - top2["final_score"]) >= GAP_THRESHOLD:
        return {
            "token": token,
            "status": "resolved",
            "canonical_name": top1["name"],
            "table": top1["source"],
            "confidence": top1["final_score"]
        }

    # 4️⃣ NEW FIX — pick only top if it's the absolute best candidate
    if len(candidates) > 1:
        max_score = top1["final_score"]
        if all(max_score >= c["final_score"] for c in candidates[1:]):
            return {
                "token": token,
                "status": "resolved",
                "canonical_name": top1["name"],
                "table": top1["source"],
                "confidence": top1["final_score"]
            }

    # 5️⃣ Otherwise → need clarification
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
    query = "Which of the following saw the highest average temperature in January, Georgia, Paris, chennaii or entire New Zealand ?"
    output = process_query(query)
    print(output)
