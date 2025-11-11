from psycopg2 import sql
from scripts.db_config import connect_db
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util

# === CONFIG ===
RESOLVE_THRESHOLD = 0.70
TRGM_THRESHOLD = 0.30
TOP_K_RESULTS = 5
DEBUG_MODE = True

# === Load the semantic model ===
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def find_best_matches(token: str):
    """Find best matches using pg_trgm + RapidFuzz + Semantic Similarity."""
    conn = connect_db()
    cur = conn.cursor()

    query = sql.SQL("""
        SELECT country_name AS name, 'countries' AS source, similarity(country_name, %s) AS score
        FROM countries
        WHERE country_name %% %s
        UNION ALL
        SELECT state_name AS name, 'states' AS source, similarity(state_name, %s) AS score
        FROM states
        WHERE state_name %% %s
        UNION ALL
        SELECT city_name AS name, 'cities' AS source, similarity(city_name, %s) AS score
        FROM cities
        WHERE city_name %% %s
        ORDER BY score DESC
        LIMIT {limit};
    """).format(limit=sql.SQL(str(TOP_K_RESULTS)))

    cur.execute(query, [token]*6)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # If nothing retrieved, return empty
    if not rows:
        return []

    results = []
    token_emb = model.encode(token, convert_to_tensor=True)

    for name, source, pg_score in rows:
        rf_score = fuzz.token_sort_ratio(token, name) / 100.0
        name_emb = model.encode(name, convert_to_tensor=True)
        sem_score = util.cos_sim(token_emb, name_emb).item()

        # Combine all 3 with tuned weights
        final_score = round((0.4 * pg_score + 0.4 * rf_score + 0.2 * sem_score), 2)

        results.append({
            "name": name,
            "source": source,
            "pg_score": round(pg_score, 2),
            "rf_score": round(rf_score, 2),
            "sem_score": round(sem_score, 2),
            "final_score": final_score
        })

    # Sort by combined final score
    results = sorted(results, key=lambda x: x['final_score'], reverse=True)

    # Filter by threshold
    filtered = [r for r in results if r["final_score"] >= RESOLVE_THRESHOLD]

    return filtered or results[:1]  # fallback: return best match anyway


# === TEST ===
if __name__ == "__main__":
    print(find_best_matches("Bombay"))
