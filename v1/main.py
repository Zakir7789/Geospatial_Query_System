from nlp import extract_place_entities
from matcher_phonetic import phonetic_match_tokens
from matcher_semantic_cached import SemanticMatcher
from db import Database

def load_all_canonical_tables(db: Database):
    """
    Dynamically fetch all tables from public schema and load names.
    Returns a dict: { table_name: [names...] }
    """
    canonical = {}
    try:
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='public' AND table_type='BASE TABLE';
            """)
            tables = [row[0] for row in cur.fetchall()]

        for t in tables:
            df = db.fetch_table(t)
            if not df.empty:
                canonical[t] = df['name'].tolist()

        print(f"📋 Canonical tables loaded: {list(canonical.keys())}")
    except Exception as e:
        print("❌ Error loading canonical tables:", e)

    return canonical


CONFIDENCE_THRESHOLD = 0.8  # adjust as needed

def resolve_places(places, canonical_tables, semantic_matcher, threshold=CONFIDENCE_THRESHOLD):
    """
    Resolve places:
    - Try phonetic matcher first
    - Fallback to semantic matcher
    - Adds 'source' and 'warning' fields to indicate matcher type and confidence
    """
    results = []
    fuzzy_results = phonetic_match_tokens(places, canonical_tables)

    for fr in fuzzy_results:
        if fr["canonical"] is None:
            sem_results = semantic_matcher.semantic_match_tokens([fr["token"]])
            if sem_results and sem_results[0]["canonical"] is not None:
                r = sem_results[0]
                r["source"] = "semantic"
            else:
                r = fr
                r["source"] = "unmatched"
                r["score"] = 0
        else:
            r = fr
            r["source"] = "phonetic"

        # Add warning if confidence below threshold
        r["warning"] = r["score"] < threshold
        results.append(r)

    return results


if __name__ == "__main__":
    # Use Database class
    db = Database()
    db.connect_db()

    canonical_tables = load_all_canonical_tables(db) if db.conn else {}

    # Initialize cached semantic matcher
    semantic_matcher = SemanticMatcher(canonical_tables)

    queries = [
        "Which of the following saw the highest average temperature in January, Maharastra, Ahmdabad or entire New-Zealand?",
        "Show me a graph of rainfall for Chennnai for the month of October",
        "What is the population of Mumabi and Gujaratt compared to New Zealand?",
        "Rainfall trends in Bombay vs Chennai",
        "Population of U.S.A and NZ"
    ]

    for q in queries:
        print(f"\n🔎 Query: {q}")
        places = extract_place_entities(q)
        resolved = resolve_places(places, canonical_tables, semantic_matcher)
        for r in resolved:
            print(r)

    db.close()
