from app.services.weather_service import WeatherService

print("Testing Rainfall API...")

# Test coordinates for Mumbai
data = WeatherService.get_rainfall_history(19.0760, 72.8777)

if data:
    print("[SUCCESS] Rainfall data fetched!")
    print(f"Dates: {data['dates']}")
    print(f"Values: {data['values']}")
else:
    print("[FAILED] Could not fetch rainfall data.")
