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

    cur.execute(query, [token]*8)
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
        
        final_score = round(rapidfuzz_score/100, 2)
        
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

# Example
if __name__ == "__main__":
    print(hybrid_fuzzy_match("Bombay"))
    print(hybrid_fuzzy_match("Bangalore"))
    print(hybrid_fuzzy_match("Bengaluru"))