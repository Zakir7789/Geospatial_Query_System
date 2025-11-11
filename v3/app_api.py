# app_api.py (Final LEAFLET Version)
import json
import os
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, send_from_directory
from nlp.canonical_mapper import process_query
from scripts.db_config import connect_db

load_dotenv() # Load .env file

# --- 1. Initialization (Runs once on startup) ---
print("Initializing backend...")
try:
    conn = connect_db()
    if conn:
        conn.close()
        print("✅ Database connection successful.")
    else:
        raise Exception("Initial connection check failed.")
except Exception as e:
    print(f"❌ CRITICAL: Database connection failed. {e}")
print("✅ Backend ready.")
# --- End of Initialization ---

app = Flask(__name__, static_folder='static', template_folder='.')

# --- Frontend Routes ---
@app.route('/')
def index():
    """Serves the main index.html page."""
    # We no longer pass the API key
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serves the static files (css, js)."""
    return send_from_directory('static', path)

# --- The Main API Endpoint ---
@app.route('/api/resolve', methods=['POST'])
def api_resolve_places():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400

    query_text = data['query']
    conn = None
    
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        # 1. Use canonical_mapper.py to get resolved places
        canonical_json = process_query(query_text)
        
        if 'results' not in canonical_json:
            return jsonify({
                "resolved_places": [],
            })

        # 2. Get the list of resolved places
        resolved_places = canonical_json.get('results', [])

        # --- THIS IS THE FIX ---
        # 3. Add lat/lon coordinates for map markers (for Leaflet)
        cur = conn.cursor()
        for place in resolved_places:
            if place.get('status') == 'resolved' and place.get('table') == 'cities':
                try:
                    cur.execute("SELECT lat, lon FROM cities WHERE city_name = %s", (place['canonical_name'],))
                    coords = cur.fetchone()
                    if coords:
                        place['lat'] = coords[0]
                        place['lon'] = coords[1]
                except Exception as e:
                    print(f"Error fetching lat/lon for {place['canonical_name']}: {e}")
        cur.close()
        # --- END OF FIX ---

        # 4. Return all data to the frontend
        return jsonify({
            "resolved_places": resolved_places
        })

    except Exception as e:
        print(f"Error during query processing: {e}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        if conn:
            conn.close()
            print("[INFO] Database connection closed.")

if __name__ == '__main__':
    app.run(debug=True, port=5000)