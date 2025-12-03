import requests
import json

def test_live_endpoint():
    url = "http://localhost:5000/api/resolve"
    payload = {"query": "Route from Bangalore to Delhi"}
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        print("\nResponse Status:", data.get("status"))
        print("Intent:", data.get("intent"))
        
        if "multimodal_route" in data and data["multimodal_route"]:
            print("\n[SUCCESS] Multimodal Route Received!")
            route = data["multimodal_route"]
            print(f"Total Distance: {route.get('total_distance_km')} km")
            print("Segments:")
            for seg in route.get("segments", []):
                print(f" - {seg['type']}: {seg['label']}")
        else:
            print("\n[WARNING] No multimodal route in response.")
            print("Results:", len(data.get("results", [])))
            
    except Exception as e:
        print(f"\n[ERROR] Request failed: {e}")

if __name__ == "__main__":
    test_live_endpoint()
