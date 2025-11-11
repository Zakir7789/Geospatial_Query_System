# fuzzy_matcher.py
from psycopg2 import sql
from scripts.db_config import connect_db
from rapidfuzz import fuzz

RESOLVE_THRESHOLD = 0.7
TOP_K_DB = 10  # fetch more candidates for refinement
FINAL_K = 3    # final top results

def find_best_matches(token: str):
    conn = connect_db()
    cur = conn.cursor()

    # Use pg_trgm to get top N approximate matches
    query = sql.SQL("""
        SELECT name, source, score FROM (
            SELECT country_name AS name, 'countries' AS source, similarity(country_name, %s) AS score FROM countries WHERE country_name %% %s
            UNION ALL
            SELECT state_name AS name, 'states' AS source, similarity(state_name, %s) AS score FROM states WHERE state_name %% %s
            UNION ALL
            SELECT city_name AS name, 'cities' AS source, similarity(city_name, %s) AS score FROM cities WHERE city_name %% %s
        ) AS combined
        ORDER BY score DESC
        LIMIT %s;
    """)

    cur.execute(query, [token]*6 + [TOP_K_DB])
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Re-rank using RapidFuzz
    refined = []
    for name, source, pg_score in rows:
        rf_score = fuzz.token_sort_ratio(token, name) / 100.0  # normalize to 0–1
        final_score = round((0.6 * pg_score + 0.4 * rf_score), 2)  # weighted average
        refined.append({
            "name": name,
            "source": source,
            "pg_score": round(pg_score, 2),
            "rf_score": round(rf_score, 2),
            "final_score": final_score
        })

    refined = sorted(refined, key=lambda x: x["final_score"], reverse=True)
    return refined[:FINAL_K]

if __name__ == "__main__":
    print(find_best_matches("Bombay"))
