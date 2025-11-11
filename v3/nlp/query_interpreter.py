# nlp/query_interpreter.py (Fixed Version - FINAL)
import re
from scripts.db_config import connect_db

def interpret_query(canonical_json: dict):
    """
    Interprets canonical JSON into SQL based on existing database schema.
    (This version adds logic for simple "what is..." queries)
    """
    query_text = canonical_json['query'].lower()
    results = canonical_json.get('results', [])

    if not results:
        return "No valid SQL could be generated (no resolved entities)."

    # Detect metric intent
    if "population" in query_text:
        metric = "population"
    elif "area" in query_text:
        metric = "area_sq_km"
    elif any(word in query_text for word in ["latitude", "longitude", "coordinate", "location"]):
        metric = "coordinates"
    else:
        metric = None

    # Detect comparison intent
    if "highest" in query_text or "largest" in query_text:
        order = "DESC"
    elif "smallest" in query_text or "lowest" in query_text:
        order = "ASC"
    else:
        order = None

    # Prepare entity classification
    entities = {"countries": [], "states": [], "cities": []}
    for item in results:
        if item.get("status") == "resolved":
            table = item.get("table", "")
            if table in entities:
                entities[table].append(item["canonical_name"])

    # --- SQL GENERATION ---
    query_parts = []
    
    # Case 1: Comparison query (highest/lowest)
    if metric and order:
        if entities["cities"] and metric == "population":
            city_list = ','.join([f"'{c}'" for c in entities['cities']])
            query_parts.append(f"""
            SELECT city_name AS name, population AS value, 'City' AS type
            FROM cities
            WHERE city_name IN ({city_list}) AND population IS NOT NULL
            """)
        
        # --- FIX: Removed population logic for states (schema doesn't have it) ---
        
        if entities["countries"] and (metric == "population" or metric == "area_sq_km"):
            country_list = ','.join([f"'{c}'" for c in entities['countries']])
            query_parts.append(f"""
            SELECT country_name AS name, {metric} AS value, 'Country' AS type
            FROM countries
            WHERE country_name IN ({country_list}) AND {metric} IS NOT NULL
            """)

        if not query_parts:
            return "No valid SQL: The entities found do not support the requested metric (e.g., 'area' for cities or 'population' for states)."

        combined_query = " UNION ALL ".join(query_parts)
        sql = f"""
        SELECT name, value, type
        FROM (
        {combined_query}
        ) AS combined_results
        ORDER BY value {order}
        LIMIT 1;
        """
        return sql.strip()

    # --- FIX: Added logic for non-comparison "What is..." queries ---
    if metric and not order:
        if entities["cities"] and metric == "population":
            city_list = ','.join([f"'{c}'" for c in entities['cities']])
            query_parts.append(f"""
            SELECT city_name AS name, population AS value, 'City' AS type
            FROM cities
            WHERE city_name IN ({city_list})
            """)
        
        if entities["countries"] and (metric == "population" or metric == "area_sq_km"):
            country_list = ','.join([f"'{c}'" for c in entities['countries']])
            query_parts.append(f"""
            SELECT country_name AS name, {metric} AS value, 'Country' AS type
            FROM countries
            WHERE country_name IN ({country_list})
            """)
        
        if metric == "coordinates" and entities["cities"]:
            city_list = ','.join([f"'{c}'" for c in entities['cities']])
            sql = f"""
            SELECT city_name, lat, lon
            FROM cities
            WHERE city_name IN ({city_list});
            """
            return sql.strip()
        
        if query_parts:
            sql = " UNION ALL ".join(query_parts)
            return sql.strip() + ";"
    # --- END OF FIX ---

    # Case 3: Relational queries (fallback)
    sql = ""
    if "state" in query_text and entities["countries"]:
        country_list = ','.join([f"'{c}'" for c in entities['countries']])
        sql = f"""
        SELECT state_name
        FROM states
        WHERE country_code IN (
            SELECT iso_code FROM countries
            WHERE country_name IN ({country_list})
        );
        """
    elif "city" in query_text and entities["states"]:
        state_list = ','.join([f"'{s}'" for s in entities['states']])
        sql = f"""
        SELECT city_name
        FROM cities
        WHERE state_code IN (
            SELECT state_code FROM states
            WHERE state_name IN ({state_list})
        );
        """

    return sql.strip() if sql else "No valid SQL could be generated for this query."


def run_query(sql: str, conn): # <-- PERFORMANCE FIX: Accept connection
    """Runs the SQL query using the provided database connection."""
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    return rows


if __name__ == "__main__":
    # Test Case 1: Comparison Query
    canonical_json_compare = {
        "query": "Which has the highest population — Ahmedabad or India?",
        "results": [
            {"token": "Ahmedabad", "status": "resolved", "canonical_name": "ahmedabad", "table": "cities", "confidence": 1.0},
            {"token": "India", "status": "resolved", "canonical_name": "india", "table": "countries", "confidence": 1.0}
        ]
    }
    sql_compare = interpret_query(canonical_json_compare)
    print("🧠 Generated SQL (Comparison):\n", sql_compare)
    
    # Test Case 2: Simple Population Query (This is the one you need)
    canonical_json_simple = {
        "query": "what is the population of Bangalore?",
        "results": [
            {"token": "Bangalore", "status": "resolved", "canonical_name": "bangalore", "table": "cities", "confidence": 1.0}
        ]
    }
    sql_simple = interpret_query(canonical_json_simple)
    print("\n🧠 Generated SQL (Simple Query Fix):\n", sql_simple)
    
    # Test Case 3: Coordinate Query
    canonical_json_coords = {
        "query": "what are the coordinates of ahmedabad?",
        "results": [
            {"token": "Ahmedabad", "status": "resolved", "canonical_name": "ahmedabad", "table": "cities", "confidence": 1.0}
        ]
    }
    sql_coords = interpret_query(canonical_json_coords)
    print("\n🧠 Generated SQL (Coordinates):\n", sql_coords)