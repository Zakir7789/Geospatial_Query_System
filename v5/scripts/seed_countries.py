import json
import requests
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Natural Earth Data (Low resolution for fast loading)
URL = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_110m_admin_0_countries.geojson"

def get_db_connection():
    return psycopg2.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "geospatial_db")
    )

def seed_countries():
    print(f"Downloading Country Data from {URL}...")
    try:
        response = requests.get(URL)
        data = response.json()
    except Exception as e:
        print(f"❌ Failed to download: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    print("⏳ Inserting Countries into PostGIS...")
    count = 0
    
    for feature in data['features']:
        props = feature['properties']
        geom = feature['geometry']
        
        # MAPPING: Match keys to your NEW database columns
        # DB Column: country_name | JSON: name
        country_name = props.get('name') or props.get('NAME')
        
        # DB Column: iso_code | JSON: iso_a3
        iso_code = props.get('iso_a3') or props.get('ISO_A3')
        
        # DB Column: continent | JSON: continent
        continent = props.get('continent') or props.get('CONTINENT')
        
        # DB Column: population | JSON: pop_est
        population = props.get('pop_est', 0)

        # SQL Query for your NEW Schema
        query = """
            INSERT INTO countries (country_name, iso_code, continent, population, geom)
            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            ON CONFLICT (country_name) DO NOTHING;
        """
        
        try:
            cursor.execute(query, (country_name, iso_code, continent, population, json.dumps(geom)))
            count += 1
        except Exception as e:
            print(f"Error inserting {country_name}: {e}")
            conn.rollback()

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Success! Loaded {count} countries.")

if __name__ == "__main__":
    seed_countries()