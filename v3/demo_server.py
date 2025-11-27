import json
from flask import Flask, jsonify, request, render_template, send_from_directory

# --- This is your new "dummy" server ---
app = Flask(__name__, static_folder='static', template_folder='.')
print("✅ Dummy Server Initialized.")
print("This server will NOT connect to the database.")
print("It will only return a hardcoded response for 'Bangalore'.")

# --- Frontend Routes ---
@app.route('/')
def index():
    """Serves the main index.html page."""
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serves the static files (css, js)."""
    return send_from_directory('static', path)

# --- The "Dummy" API Endpoint ---
@app.route('/api/resolve', methods=['POST'])
def api_resolve_places():
    data = request.get_json()
    query_text = data.get('query', '').lower()

    # --- THIS IS THE "CHEAT" ---
    # It checks if the query contains "bangalore"
    if "bangalore" in query_text:
        
        print("-> Query for 'Bangalore' detected. Returning hardcoded response.")
        
        # --- START OF MAP FIX ---
        # This is a "Point" GeoJSON for Bangalore's approximate coordinates.
        faked_geojson = {
            "type": "Point",
            "coordinates": [
                77.5946,  # Longitude
                12.9716   # Latitude
            ]
        }
        # --- END OF MAP FIX ---
        
        # This is the "resolved_places" part of the response
        resolved_places = [
            {
                "token": "Bangalore",
                "status": "resolved",
                "canonical_name": "bangalore",
                "table": "cities",
                "confidence": 1.0,
                "geojson": faked_geojson  # <-- ADDED FAKE MAP DATA
            }
        ]
        
        # This is the "sql_query" part
        sql_query = "SELECT city_name, population\nFROM cities\nWHERE city_name IN ('bangalore')"
        
        # This is the "sql_results" part (a faked database response)
        sql_results = [
            ("bangalore", 8443675) # Faked population data
        ]
        
        # Return the complete, hardcoded JSON
        return jsonify({
            "resolved_places": resolved_places,
            "sql_query": sql_query,
            "sql_results": sql_results
        })

    # --- Fallback for any other query ---
    else:
        print(f"-> Query '{query_text}' received. Not 'Bangalore'.")
        return jsonify({
            "resolved_places": [],
            "sql_query": "No query generated.",
            "sql_results": ["This dummy server only responds to queries containing 'Bangalore'."]
        })

if __name__ == '__main__':
    # Run on port 5000, just like your real app
    app.run(debug=True, port=5000)