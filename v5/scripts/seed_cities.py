import requests
import psycopg2
import os
import io
import zipfile
from dotenv import load_dotenv

load_dotenv()

# DATA SOURCE: GeoNames (cities15000)
# All cities with a population > 15,000 (approx 25,000+ cities)
URL = "http://download.geonames.org/export/dump/cities500.zip"

def get_db_connection():
    return psycopg2.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "geospatial_db")
    )

def seed_cities_geonames():
    print(f"[INFO] Downloading GeoNames archive...")
    print(f"   Source: {URL}")
    
    try:
        response = requests.get(URL)
        response.raise_for_status()
        print(f"[OK] Download complete. Size: {len(response.content) / 1024 / 1024:.2f} MB")
    except Exception as e:
        print(f"[ERROR] Failed to download data: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    print("[INFO] Inserting cities into database...")
    
    # 1. WIPE OLD DATA
    cursor.execute("TRUNCATE TABLE cities RESTART IDENTITY;")
    conn.commit()

    count = 0
    skipped = 0
    
    # Query structure matching the table schema
    query = """
        INSERT INTO cities (city_name, country_code, population, lat, lon, geom, alt_names)
        VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
    """

    try:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with z.open('cities15000.txt') as f:
                for line in f:
                    try:
                        # Decode and split
                        row = line.decode('utf-8').strip().split('\t')
                        
                        # Mapping
                        # Index 1: Name
                        name = row[1]
                        
                        # Index 4: Latitude
                        lat = float(row[4])
                        
                        # Index 5: Longitude
                        lon = float(row[5])
                        
                        # Index 8: Country Code
                        country_code = row[8]
                        
                        # Index 14: Population
                        population = int(row[14]) if row[14] else 0
                        
                        # Handle Aliases (Index 2: Ascii Name, Index 3: Alternate Names)
                        alt_names = []
                        if row[2]: # Ascii Name
                            alt_names.append(row[2])
                        if row[3]: # Alternate Names (comma separated)
                            alt_names.extend(row[3].split(','))
                        
                        # Execute Insert
                        cursor.execute(query, (name, country_code, population, lat, lon, lon, lat, alt_names))
                        
                        count += 1
                        if count % 5000 == 0:
                            print(f"   Inserted {count} / 25,000+ cities")
                            conn.commit() # Commit periodically
                            
                    except Exception as row_err:
                        # print(f"Skipping row: {row_err}")
                        skipped += 1
                        continue

        conn.commit()
        print(f"[SUCCESS] Database populated with {count} cities. (Skipped {skipped})")

    except Exception as e:
        print(f"[ERROR] Error processing zip/file: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_cities_geonames()