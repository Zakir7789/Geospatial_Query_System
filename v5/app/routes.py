from flask import Blueprint, render_template, request, jsonify
import time
from app.services.nlp_service import NLPService
from app.services.geo_service import GeoService
from app.services.weather_service import WeatherService

main_bp = Blueprint('main', __name__)

# Query cache: {query_key: {"result": data, "timestamp": time}}
query_cache = {}
CACHE_TTL_SECONDS = 600  # 10 minutes

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/api/resolve', methods=['POST'])
def resolve_query():
    data = request.json
    user_query = data.get('query', '')
    
    # Check cache first
    cache_key = user_query.lower().strip()
    current_time = time.time()
    
    if cache_key in query_cache:
        cached_entry = query_cache[cache_key]
        if current_time - cached_entry["timestamp"] < CACHE_TTL_SECONDS:
            print(f"[CACHE HIT] Returning cached result for: {user_query}")
            return jsonify(cached_entry["result"])
        else:
            del query_cache[cache_key]
    
    # 1. NLP LAYER
    analysis = NLPService.analyze_query(user_query)
    
    intent = analysis.get('intent', 'INFO')
    corrected_locations = analysis.get('locations', [])
    location_details = analysis.get('location_details', {})
    params = analysis.get('params', {})
    
    resolved_data = []
    
    # 2. DB LAYER - Context Detection
    context_country = None
    for loc in corrected_locations:
        meta = GeoService.get_location_metadata(loc)
        if meta and meta['type'] == 'country':
            context_country = meta['city_name']
            break
            
    primary_city = None
    for place in corrected_locations:
        meta = GeoService.get_location_metadata(place, context_country=context_country)
        
        obj = {}
        if meta:
            obj = meta
            if not primary_city and meta['type'] == 'city': primary_city = meta
        else:
            obj = {
                "city_name": place, 
                "lat": None, "lon": None,
                "source": "google_fallback"
            }
        
        details = location_details.get(place, {})
        obj['ai_summary'] = details.get('summary', '')
        obj['ai_answer'] = details.get('answer', '')
        
        # WEATHER & RAINFALL INTEGRATION
        if obj.get('lat') and obj.get('lon'):
            # Current Weather
            if intent == 'WEATHER':
                weather = WeatherService.get_current_weather(obj['lat'], obj['lon'])
                if weather: obj['weather'] = weather
            
            # Rainfall History (Keyword check)
            if "rain" in user_query.lower() or "precipitation" in user_query.lower():
                rain_data = WeatherService.get_rainfall_history(obj['lat'], obj['lon'])
                if rain_data: obj['rainfall_history'] = rain_data
        
        resolved_data.append(obj)

    # 3. SPATIAL DISCOVERY
    if intent == 'NEARBY' and primary_city:
        radius = params.get('radius_km', 50)
        neighbors = GeoService.find_nearby_cities(
            primary_city['lat'], primary_city['lon'], radius_km=radius
        )
        resolved_data.extend(neighbors)
        
        # Deduplicate
        seen = set()
        unique_data = []
        for item in resolved_data:
            name = item.get('city_name')
            if name not in seen:
                unique_data.append(item)
                seen.add(name)
        resolved_data = unique_data

    # Prepare response (No multimodal_route)
    response_data = {
        "status": "success",
        "intent": intent,
        "results": resolved_data
    }
    
    query_cache[cache_key] = {
        "result": response_data,
        "timestamp": current_time
    }
    
    return jsonify(response_data)