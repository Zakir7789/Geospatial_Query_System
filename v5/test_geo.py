
import sys
import os

# Add the current directory to sys.path to make app module importable
sys.path.append(os.getcwd())

from app.services.geo_service import GeoService
from app import create_app

def test_geo_lookup(place: str):
    app = create_app()
    with app.app_context():
        query = place
        print(f"\nSearching GeoService for: '{query}'")
        res = GeoService.get_location_metadata(query)
        if res:
            print(f"   FOUND: {res['city_name']} ({res['type']})")
            print(f"   Score: {res['sim_score']:.4f}")
            print(f"   Lat/Lon: {res['lat']}, {res['lon']}")
        else:
            print("   NOT FOUND")

if __name__ == "__main__":
    place = input("enter place name to check if it exists and its scores: ")
    test_geo_lookup(place)
