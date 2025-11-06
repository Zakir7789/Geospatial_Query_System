# fuzzy_matcher.py
import psycopg2
from psycopg2.extras import RealDictCursor
from db_config import get_connection

# --- Core fuzzy match ---
def fuzzy_match_entity(entity_text, top_k=3, threshold=0.35):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = f"""
        SELECT alias, canonical_table, canonical_id,
               similarity(alias, %s) AS score
        FROM aliases
        WHERE alias %% %s   -- trigram similarity operator
        ORDER BY score DESC
        LIMIT {top_k};
    """
    cur.execute(query, (entity_text, entity_text))
    results = [r for r in cur.fetchall() if r["score"] >= threshold]
    cur.close()
    conn.close()
    return results

# --- Demo run ---
if __name__ == "__main__":
    examples = ["sao paulo", "cote d ivoire", "new york", "bombay", "maharastra"]
    for e in examples:
        matches = fuzzy_match_entity(e)
        print(f"\nEntity: {e}")
        for m in matches:
            print(f"  → Match: {m['alias']} | Table: {m['canonical_table']} | ID: {m['canonical_id']} | Score: {round(m['score'],3)}")
