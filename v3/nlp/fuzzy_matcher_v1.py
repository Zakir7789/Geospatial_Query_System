# nlp/fuzzy_matcher_v1.py
from scripts.db_config import connect_db
from rapidfuzz import process, fuzz

# Configurable parameters
DB_LIMIT = 50          # number of candidates fetched from PostgreSQL
TOP_K_RESULTS = 5      # number of results returned after RapidFuzz re-ranking
TRGM_THRESHOLD = 0.3   # minimum trigram similarity to fetch from DB
FINAL_THRESHOLD = 0.7  # minimum final score for acceptance

def hybrid_fuzzy_match(token: str):
    """Performs hybrid fuzzy matching using PostgreSQL + RapidFuzz."""

    token = token.strip().lower()

    conn = connect_db()
    cur = conn.cursor()

    # Step 1: PostgreSQL — fetch top N candidates via trigram
    query = f"""
        SELECT name, source, score FROM (
            SELECT country_name AS name, 'countries' AS source,
                   similarity(country_name, %s) AS score
            FROM countries
            WHERE country_name %% %s
            UNION ALL
            SELECT state_name AS name, 'states' AS source,
                   similarity(state_name, %s) AS score
            FROM states
            WHERE state_name %% %s
            UNION ALL
            SELECT city_name AS name, 'cities' AS source,
                   similarity(city_name, %s) AS score
            FROM cities
            WHERE city_name %% %s
        ) AS combined
        WHERE score > {TRGM_THRESHOLD}
        ORDER BY score DESC
        LIMIT {DB_LIMIT};
    """

    cur.execute(query, [token]*6)
    candidates = cur.fetchall()
    cur.close()
    conn.close()

    if not candidates:
        return []

    # Step 2: RapidFuzz — re-rank by string similarity
    names = [row[0] for row in candidates]
    ranked = process.extract(token, names, scorer=fuzz.token_sort_ratio, limit=TOP_K_RESULTS)

    # Step 3: Combine DB source info + final score
    results = []
    for name, score, _ in ranked:
        sources = [src for n, src, _ in candidates if n == name]
        source = ','.join(set(sources))
        results.append({
            "name": name,
            "source": source,
            "final_score": round(score/100, 2)
        })

    # Step 4: Filter by threshold
    results = [r for r in results if r["final_score"] >= FINAL_THRESHOLD]
    return results

# Example
if __name__ == "__main__":
    print(hybrid_fuzzy_match("Bombay"))
