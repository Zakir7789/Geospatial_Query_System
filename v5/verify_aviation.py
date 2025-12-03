import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from app import create_app, get_db_connection

app = create_app()

def verify_aviation_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n--- VERIFYING AVIATION DATA ---")
    
    cursor.execute("SELECT COUNT(*) FROM airports;")
    count_airports = cursor.fetchone()[0]
    print(f"Airports Count: {count_airports}")
    
    cursor.execute("SELECT COUNT(*) FROM flight_routes;")
    count_routes = cursor.fetchone()[0]
    print(f"Routes Count: {count_routes}")
    
    # Check a sample route
    cursor.execute("""
        SELECT a1.name, a2.name, r.airline_code 
        FROM flight_routes r
        JOIN airports a1 ON r.source_iata = a1.iata_code
        JOIN airports a2 ON r.dest_iata = a2.iata_code
        LIMIT 1;
    """)
    sample = cursor.fetchone()
    if sample:
        print(f"Sample Route: {sample[0]} -> {sample[1]} ({sample[2]})")
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    with app.app_context():
        verify_aviation_data()
