import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from app import create_app
from app.services.route_service import RouteService
from app.services.geo_service import GeoService

app = create_app()

def test_multimodal_route():
    print("\n--- TESTING MULTIMODAL ROUTING ---")
    
    # 1. Resolve Coordinates for Bangalore and Delhi
    print("Resolving locations...")
    blr = GeoService.get_location_metadata("Bangalore")
    delhi = GeoService.get_location_metadata("Delhi")
    
    if not blr or not delhi:
        print("[ERROR] Could not resolve locations.")
        return

    print(f"Start: {blr['city_name']} ({blr['lat']}, {blr['lon']})")
    print(f"End:   {delhi['city_name']} ({delhi['lat']}, {delhi['lon']})")
    
    # 2. Calculate Route
    print("\nCalculating Multimodal Route...")
    route = RouteService.get_multimodal_route(blr['lat'], blr['lon'], delhi['lat'], delhi['lon'])
    
    if route:
        print(f"\n[SUCCESS] Route Found!")
        print(f"Total Distance: {route['total_distance_km']} km")
        print("Segments:")
        for seg in route['segments']:
            print(f" - {seg['type']}: {seg['label']}")
            if seg['type'] == 'FLIGHT':
                print(f"   Airline: {seg['airline']} ({seg['from_iata']} -> {seg['to_iata']})")
    else:
        print("\n[FAILURE] No route found (or distance too short).")

if __name__ == "__main__":
    with app.app_context():
        test_multimodal_route()
