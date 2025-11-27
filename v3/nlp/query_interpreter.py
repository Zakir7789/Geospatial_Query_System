import re
from scripts.db_config import connect_db

def interpret_query(canonical_json: dict):
    """
    Interprets canonical JSON into SQL based on existing database schema.
    Supports population, area, coordinates, and mapping queries.
    """
    query_text = canonical_json['query'].lower()
    results = canonical_json['results']

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
        entities[item["table"]].append(item["canonical_name"])

    sql = ""

    # Generate SQL based on metric
    if metric == "population":
        if entities["cities"]:
            sql = f"""
            SELECT city_name, population
            FROM cities
            WHERE city_name IN ({','.join([f"'{c}'" for c in entities['cities']])})
            """
            if order:
                sql += f" ORDER BY population {order} LIMIT 1;"
        elif entities["states"]:
            sql = f"""
            SELECT state_name, population
            FROM states
            WHERE state_name IN ({','.join([f"'{s}'" for s in entities['states']])})
            """
        elif entities["countries"]:
            sql = f"""
            SELECT country_name, population
            FROM countries
            WHERE country_name IN ({','.join([f"'{c}'" for c in entities['countries']])})
            """
            if order:
                sql += f" ORDER BY population {order} LIMIT 1;"

    elif metric == "area_sq_km":
        sql = f"""
        SELECT country_name, area_sq_km
        FROM countries
        WHERE country_name IN ({','.join([f"'{c}'" for c in entities['countries']])})
        """
        if order:
            sql += f" ORDER BY area_sq_km {order} LIMIT 1;"

    elif metric == "coordinates":
        sql = f"""
        SELECT city_name, lat, lon
        FROM cities
        WHERE city_name IN ({','.join([f"'{c}'" for c in entities['cities']])});
        """

    else:
        # Default to relationship lookup
        if "state" in query_text and entities["countries"]:
            sql = f"""
            SELECT state_name
            FROM states
            WHERE country_code IN (
                SELECT iso_code FROM countries
                WHERE country_name IN ({','.join([f"'{c}'" for c in entities['countries']])})
            );
            """
        elif "city" in query_text and entities["states"]:
            sql = f"""
            SELECT city_name
            FROM cities
            WHERE state_code IN (
                SELECT state_code FROM states
                WHERE state_name IN ({','.join([f"'{s}'" for s in entities['states']])})
            );
            """

    return sql.strip() if sql else "No valid SQL could be generated for this query."


def run_query(sql: str):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


if __name__ == "__main__":
    canonical_json = {
        "query": "Which of the following has the highest population — Maharashtra, Ahmedabad or India?",
        "results": [
            {"token": "Maharashtra", "status": "resolved", "canonical_name": "maharashtra", "table": "states", "confidence": 1.0},
            {"token": "Ahmedabad", "status": "resolved", "canonical_name": "ahmedabad", "table": "cities", "confidence": 1.0},
            {"token": "India", "status": "resolved", "canonical_name": "india", "table": "countries", "confidence": 1.0}
        ]
    }

    sql = interpret_query(canonical_json)
    print("🧠 Generated SQL:\n", sql)
