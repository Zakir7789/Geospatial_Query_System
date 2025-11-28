import requests
import json
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# DATA SOURCE: Natural Earth (Global Admin 1 - States/Provinces)
# Using the 10m (high res) dataset for GLOBAL coverage
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson"

def get_db_connection():
    return psycopg2.connect(
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "geospatial_db")
    )

def seed_states():
    print(f"🌍 Downloading Global State Data (approx 25MB)...")
    try:
        response = requests.get(URL)
        data = response.json()
        print(f"✅ Downloaded {len(data['features'])} states/provinces.")
    except Exception as e:
        print(f"❌ Failed to download data: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    print("⏳ Inserting States into PostGIS...")
    # Clean slate
    cursor.execute("TRUNCATE TABLE states RESTART IDENTITY;")
    conn.commit() # Commit the truncate immediately
    
    count = 0
    skipped = 0
    
    query = """
        INSERT INTO states (state_name, state_code, country_code, geonameid, geom)
        VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
    """
    
    for feature in data['features']:
        props = feature['properties']
        geom = feature['geometry']
        
        state_name = props.get('name') or props.get('NAME')
        state_code = (props.get('code_hasc') or props.get('iso_3166_2') or props.get('postal') or '')
        country_code = (props.get('adm0_a3') or props.get('ADM0_A3') or props.get('sov_a3') or props.get('SOV_A3'))

        # Fallback for country code
        if not country_code and state_code and '.' in state_code:
            country_code = state_code.split('.')[0]
        
        geonameid = props.get('geonameid')

        if not country_code:
            skipped += 1
            continue

        try:
            # --- FIX STARTS HERE ---
            # Create a checkpoint before inserting
            cursor.execute("SAVEPOINT sp_state_insert")
            
            cursor.execute(query, (state_name, state_code, country_code, geonameid, json.dumps(geom)))
            
            # If successful, release the checkpoint (saves memory)
            cursor.execute("RELEASE SAVEPOINT sp_state_insert")
            # --- FIX ENDS HERE ---
            
            count += 1
            if count % 1000 == 0:
                print(f"   ... inserted {count} records")
                
        except Exception as e:
            # If error, ONLY undo the last insert, keep the previous valid ones!
            cursor.execute("ROLLBACK TO SAVEPOINT sp_state_insert")
            skipped += 1
            # print(f"Skipped {state_name} due to error.")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"🚀 Success! Loaded {count} global states. (Skipped {skipped})")

if __name__ == "__main__":
    seed_states()