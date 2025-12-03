import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app
from app.services.geo_service import GeoService

app = create_app()

def test_geolocation_context():
    print("\n--- TESTING GEOLOCATION CONTEXT ---")
    
    # Case 1: "Mangalkote" without context (might return Romania or India depending on DB state)
    print("\n1. Searching 'Mangalkote' (No Context)")
    res1 = GeoService.get_location_metadata("Mangalkote")
    if res1:
        print(f"   Found: {res1['city_name']}, Country: {res1.get('parent_country', 'Unknown')}")
    else:
        print("   Not Found")

    # Case 2: "Mangalkote" with context "India"
    print("\n2. Searching 'Mangalkote' (Context: India)")
    res2 = GeoService.get_location_metadata("Mangalkote", context_country="India")
    if res2:
        print(f"   Found: {res2['city_name']}, Country: {res2.get('parent_country', 'Unknown')}")
    else:
        print("   Not Found (Correct fallback behavior if not in DB)")

    # Case 3: "Mangalkote" with context "Romania"
    print("\n3. Searching 'Mangalkote' (Context: Romania)")
    res3 = GeoService.get_location_metadata("Mangalkote", context_country="Romania")
    if res3:
        print(f"   Found: {res3['city_name']}, Country: {res3.get('parent_country', 'Unknown')}")
    else:
        print("   Not Found")

if __name__ == "__main__":
    with app.app_context():
        test_geolocation_context()
