import psycopg2
#import psycopg2.extras

DB_CONFIG = {
    "dbname": "geoparser",
    "user": "postgres",
    "password": "admin123",
    "host": "localhost",
    "port": 5432
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)
'''
def get_all_entities():
    """Fetch countries, states, cities from DB into memory."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    universe = {"Country": [], "State": [], "City": []}

    cur.execute("SELECT name FROM countries;")
    universe["Country"] = [{"name": row["name"]} for row in cur.fetchall()]

    cur.execute("SELECT name FROM states;")
    universe["State"] = [{"name": row["name"]} for row in cur.fetchall()]

    cur.execute("SELECT name FROM cities;")
    universe["City"] = [{"name": row["name"]} for row in cur.fetchall()]

    cur.close()
    conn.close()

    return universe
'''
