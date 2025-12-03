
import sys
import os

# Add the current directory to sys.path to make app module importable
sys.path.append(os.getcwd())

from app.services.geo_service import GeoService
from app import create_app, get_db_connection, release_db_connection
import psycopg2.extras

def check_in_db(place: str):
    app = create_app()
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor.execute("SELECT * FROM cities WHERE city_name = %s", (place,))
            res = cursor.fetchone()
            if res:
                print(f"[FOUND] {place} is in the DB: {res['city_name']}, Lat: {res['lat']}, Lon: {res['lon']}")
            else:
                print(f"[NOT FOUND] {place} is NOT in the DB.")
        finally:
            cursor.close()
            release_db_connection(conn)

        print(f"\nTesting GeoService Lookup for {place}:")
        res = GeoService.get_location_metadata(place)
        if res:
            print(f"   FOUND: {res['city_name']} ({res['type']})")
            print(f"   Score: {res['sim_score']:.4f}")
        else:
            print("   NOT FOUND (Will fallback to Google Maps)")

if __name__ == "__main__":
    place = input("enter place name to check if it exists in database and its scores: ")
    check_in_db(place)
