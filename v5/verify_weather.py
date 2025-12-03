
import sys
import os
import json

# Add the current directory to sys.path to make app module importable
sys.path.append(os.getcwd())

from app.services.weather_service import WeatherService
from app.services.nlp_service import NLPService
from app.services.geo_service import GeoService
from app import create_app

def test_weather(place_name):
    print(f"\n--- Testing Weather Service for '{place_name}' ---")
    
    app = create_app()
    with app.app_context():
        # 1. Get Coordinates from DB
        loc = GeoService.get_location_metadata(place_name)
        
        if not loc:
            print(f"❌ Location '{place_name}' not found in local DB. Cannot fetch weather without coordinates.")
            return

        lat, lon = loc['lat'], loc['lon']
        print(f"Resolved '{place_name}' to ({lat}, {lon})")

        # 2. Fetch Weather
        weather = WeatherService.get_current_weather(lat, lon)
        print(f"Weather: {weather}")
        
        if weather and 'temperature' in weather:
            print("Weather Service working")
        else:
            print("Weather Service failed")

def test_nlp_weather_intent(place_name):
    print(f"\n--- Testing NLP Weather Intent for '{place_name}' ---")
    query = f"weather in {place_name}"
    result = NLPService.analyze_query(query)
    print(f"Query: '{query}'")
    print(f"Intent: {result.get('intent')}")
    print(f"Locations: {result.get('locations')}")
    
    if result.get('intent') == 'WEATHER':
         print("NLP Intent detection working")
    else:
         print("NLP Intent detection failed")

if __name__ == "__main__":
    place = input("Enter place name: ")
    if place:
        test_weather(place)
        test_nlp_weather_intent(place)
