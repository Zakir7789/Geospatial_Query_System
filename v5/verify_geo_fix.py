import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.services.geo_service import GeoService
from app import create_app

app = create_app()

with app.app_context():
    print("--- Verifying GeoService Fix ---")
    # Test case 1: Known city
    query = "Bangalore"
    print(f"Searching for: {query}")
    result = GeoService.get_location_metadata(query)
    if result:
        print(f"Found: {result['city_name']} (Type: {result['type']})")
        if 'lat' in result and 'lon' in result:
             print("Coordinates present.")
        else:
             print("Coordinates MISSING.")
    else:
        print("Not found.")

    # Test case 2: Context check (should fail if comma present)
    query_comma = "Bangalore, India"
    print(f"Searching for: {query_comma}")
    result_comma = GeoService.get_location_metadata(query_comma)
    if result_comma is None:
        print("Correctly returned None for comma input.")
    else:
        print(f"Incorrectly returned result for comma input: {result_comma}")
