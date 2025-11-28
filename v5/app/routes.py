from flask import Blueprint, render_template, request, jsonify
from app.services.nlp_service import NLPService
from app.services.geo_service import GeoService

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/api/resolve', methods=['POST'])
def resolve_query():
    data = request.json
    user_query = data.get('query', '')
    
    # 1. NLP LAYER (Autocorrect & Context)
    # Input: "compare banglore and austrailia"
    # Output: locations=['Bengaluru', 'Australia']
    analysis = NLPService.analyze_query(user_query)
    
    intent = analysis.get('intent', 'WEATHER')
    corrected_locations = analysis.get('locations', [])
    params = analysis.get('params', {})
    
    resolved_data = []
    
    # 2. DB LAYER (Verification)
    primary_city = None
    for place in corrected_locations:
        meta = GeoService.get_location_metadata(place)
        
        if meta:
            # Case A: Database confirmed the location
            resolved_data.append(meta)
            if not primary_city: primary_city = meta
        else:
            # Case B: NLP found a name, but DB doesn't have it.
            # We send the CORRECTED name to the frontend (Google Maps fallback)
            resolved_data.append({
                "city_name": place, 
                "lat": None,
                "lon": None,
                "source": "google_fallback"
            })

    # 3. SPATIAL DISCOVERY
    if intent == 'NEARBY' and primary_city:
        radius = params.get('radius_km', 50)
        neighbors = GeoService.find_nearby_cities(
            primary_city['lat'], 
            primary_city['lon'], 
            radius_km=radius
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

    return jsonify({
        "status": "success",
        "intent": intent,
        "results": resolved_data
    })