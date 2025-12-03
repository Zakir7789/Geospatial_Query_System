import requests
import psycopg2
import psycopg2.extras
import os
import io
import csv
from dotenv import load_dotenv

load_dotenv()

AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
ROUTES_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat"

def get_db_connection():
    return psycopg2.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "geospatial_db")
    )

def create_tables(cursor):
    print("[INFO] Creating aviation tables...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS airports (
            iata_code VARCHAR(3) PRIMARY KEY,
            name TEXT,
            city_name TEXT,
            geom GEOMETRY(Point, 4326)
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flight_routes (
            id SERIAL PRIMARY KEY,
            source_iata VARCHAR(3) REFERENCES airports(iata_code),
            dest_iata VARCHAR(3) REFERENCES airports(iata_code),
            airline_code VARCHAR(3)
        );
    """)
    
    # Create index on geom for airports
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_airports_geom ON airports USING GIST (geom);")

def seed_airports(cursor):
    print(f"[INFO] Downloading Airports data from {AIRPORTS_URL}...")
    response = requests.get(AIRPORTS_URL)
    response.raise_for_status()
    
    # Parse CSV
    f = io.StringIO(response.text)
    reader = csv.DictReader(f)
    
    valid_types = ['large_airport', 'medium_airport']
    airports_to_insert = []
    
    print("[INFO] Parsing airports...")
    for row in reader:
        iata = row.get('iata_code')
        airport_type = row.get('type')
        
        if airport_type in valid_types and iata:
            try:
                lat = float(row['latitude_deg'])
                lon = float(row['longitude_deg'])
                name = row['name']
                city = row['municipality']
                
                # Prepare tuple for execute_batch
                # Query: INSERT INTO airports (iata_code, name, city_name, geom) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                # We will pass (iata, name, city, lon, lat)
                airports_to_insert.append((iata, name, city, lon, lat))
            except ValueError:
                continue

    print(f"[INFO] Found {len(airports_to_insert)} valid airports. Inserting...")
    
    query = """
        INSERT INTO airports (iata_code, name, city_name, geom)
        VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        ON CONFLICT (iata_code) DO NOTHING;
    """
    
    psycopg2.extras.execute_batch(cursor, query, airports_to_insert)
    print(f"[SUCCESS] Inserted airports.")
    
    # Return set of valid IATA codes for route validation
    return set([a[0] for a in airports_to_insert])

def seed_routes(cursor, valid_iata_codes):
    print(f"[INFO] Downloading Routes data from {ROUTES_URL}...")
    response = requests.get(ROUTES_URL)
    response.raise_for_status()
    
    print("[INFO] Parsing routes...")
    # Routes data has no headers
    # Airline, AirlineID, Source, SourceID, Dest, DestID, Codeshare, Stops, Equipment
    
    f = io.StringIO(response.text)
    reader = csv.reader(f)
    
    routes_to_insert = []
    
    for row in reader:
        try:
            airline = row[0]
            source = row[2]
            dest = row[4]
            
            # Validation
            if source in valid_iata_codes and dest in valid_iata_codes:
                routes_to_insert.append((source, dest, airline))
        except IndexError:
            continue
            
    print(f"[INFO] Found {len(routes_to_insert)} valid routes. Inserting...")
    
    query = """
        INSERT INTO flight_routes (source_iata, dest_iata, airline_code)
        VALUES (%s, %s, %s)
    """
    
    # Batch insert
    # We might have duplicates in the source data, but we don't have a unique constraint on routes (multiple airlines fly same route)
    psycopg2.extras.execute_batch(cursor, query, routes_to_insert)
    print(f"[SUCCESS] Inserted {len(routes_to_insert)} routes.")

def main():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        create_tables(cursor)
        conn.commit()
        
        # Seed Airports
        # We need to fetch existing ones too if we want to support incremental runs, 
        # but for now we assume we might be re-seeding or ON CONFLICT DO NOTHING handles it.
        # However, to validate routes, we need ALL valid IATA codes currently in DB.
        
        seeded_iatas = seed_airports(cursor)
        conn.commit()
        
        # Fetch ALL IATA codes from DB to be sure (in case some existed before)
        cursor.execute("SELECT iata_code FROM airports")
        all_iatas = set([r[0] for r in cursor.fetchall()])
        
        seed_routes(cursor, all_iatas)
        conn.commit()
        
        print("\n[DONE] Aviation data seeding complete.")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
