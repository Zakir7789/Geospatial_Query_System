import requests
import json
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# DATA SOURCE: Natural Earth (High Res - 10m)
# ~7,300 cities worldwide
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_populated_places.geojson"

def get_db_connection():
    return psycopg2.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "geospatial_db")
    )

def seed_cities_automated():
    print(f"🌍 Downloading High-Res City Data (approx 15MB)...")
    print(f"   Source: {URL}")
    
    try:
        response = requests.get(URL)
        data = response.json()
        print(f"✅ Downloaded {len(data['features'])} cities.")
    except Exception as e:
        print(f"❌ Failed to download data: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    print("⏳ Inserting cities into database...")
    
    # 1. WIPE OLD DATA
    cursor.execute("TRUNCATE TABLE cities RESTART IDENTITY;")

    count = 0
    skipped = 0
    
    query = """
        INSERT INTO cities (city_name, country_code, population, lat, lon, geom, alt_names)
        VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
    """

    for feature in data['features']:
        props = feature['properties']
        geom = feature['geometry']
        
        # 1. Name
        name = props.get('NAME') or props.get('name')
        
        # 2. Country Code (Standardize on 3-letter ISO)
        country_code = props.get('ADM0_A3') or props.get('adm0_a3') or props.get('sov_a3')
        
        # 3. Population
        pop_raw = props.get('POP_MAX') or props.get('pop_max') or 0
        try:
            population = int(pop_raw)
        except:
            population = 0
        
        # 4. Lat/Lon
        try:
            lon = geom['coordinates'][0]
            lat = geom['coordinates'][1]
        except:
            skipped += 1
            continue

        # 5. Handle Aliases (Optional improvement)
        # Natural Earth doesn't have a clean list, but we can combine name variants
        # e.g. NAME_ALT, NAME_EN
        alt_names = []
        if props.get('NAME_ALT'):
            alt_names.append(props.get('NAME_ALT'))
            
        try:
            cursor.execute(query, (name, country_code, population, lat, lon, lon, lat, alt_names))
            count += 1
            if count % 1000 == 0:
                print(f"   ... inserted {count} cities")
        except Exception as e:
            # print(f"⚠️ Error inserting {name}: {e}")
            skipped += 1
            conn.rollback()

    conn.commit()
    cursor.close()
    conn.close()
    print(f"🚀 Success! Database populated with {count} cities. (Skipped {skipped})")

if __name__ == "__main__":
    seed_cities_automated()