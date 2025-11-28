if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app import get_db_connection, release_db_connection
import psycopg2.extras

class GeoService:
    
    @staticmethod
    def get_location_metadata(search_query):
        """
        Unified Resolver.
        """
        term = search_query.strip()
        
        # --- CRITICAL CONTEXT CHECK ---
        # If the term contains a comma (e.g., "Paris, Texas"), 
        # return None immediately. 
        # This prevents the DB from fuzzy matching "Paris, Texas" -> "Paris" (France).
        # Returning None forces app/routes.py to use the Google Maps Fallback.
        if "," in term:
            return None

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute("SELECT set_limit(0.3);")

            query = """
                WITH all_matches AS (
                    -- 1. COUNTRIES
                    SELECT country_name as name, 
                           'country' as type, 
                           population, 
                           geom,
                           similarity(country_name, %s) as sim_score
                    FROM countries
                    WHERE similarity(country_name, %s) > 0.3 
                       OR iso_code ILIKE %s

                    UNION ALL

                    -- 2. STATES
                    SELECT state_name as name, 
                           'state' as type, 
                           0 as population, 
                           geom,
                           similarity(state_name, %s) as sim_score
                    FROM states
                    WHERE similarity(state_name, %s) > 0.3
                       OR state_code ILIKE %s

                    UNION ALL

                    -- 3. CITIES
                    SELECT city_name as name, 
                           'city' as type, 
                           population, 
                           geom,
                           CASE 
                               WHEN %s ILIKE ANY(alt_names) THEN 1.0 
                               ELSE similarity(city_name, %s) 
                           END as sim_score
                    FROM cities
                    WHERE similarity(city_name, %s) > 0.3 
                       OR %s ILIKE ANY(alt_names)
                )
                SELECT name as city_name, type, population, sim_score,
                       ST_Y(ST_Centroid(geom)) as lat, 
                       ST_X(ST_Centroid(geom)) as lon
                FROM all_matches
                ORDER BY 
                    sim_score DESC,
                    population DESC
                LIMIT 1;
            """
            
            params = (term, term, term,   # Country
                      term, term, term,   # State
                      term, term, term, term) # City
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result

        except Exception as e:
            print(f"[ERROR] Geo Lookup failed: {e}")
            return None
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def find_nearby_cities(lat, lon, radius_km=50):
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            query = """
                SELECT city_name, population, lat, lon,
                       ST_Distance(
                           geom::geography, 
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                       ) / 1000 as dist_km
                FROM cities
                WHERE ST_DWithin(
                    geom::geography, 
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                    %s * 1000
                )
                ORDER BY dist_km ASC
                LIMIT 10;
            """
            cursor.execute(query, (lon, lat, lon, lat, radius_km))
            return cursor.fetchall()
        except Exception as e:
            print(f"[ERROR] Spatial Query failed: {e}")
            return []
        finally:
            cursor.close()
            release_db_connection(conn)

if __name__ == "__main__":
    from app import create_app
    app = create_app()
    
    print("\n--- TESTING GEO SERVICE ---")
    # Test cases: "Paris, Texas" should now return NOT FOUND (correct behavior), 
    # forcing the app to use the full name in Google Maps.
    test_cases = ["Bengaluru", "Paris, Texas", "India"]
    
    with app.app_context():
        for query in test_cases:
            print(f"\nSearching: '{query}'")
            res = GeoService.get_location_metadata(query)
            if res:
                print(f"   FOUND: {res['city_name']} ({res['type']})")
                print(f"   Score: {res['sim_score']:.4f}")
            else:
                print("   NOT FOUND (Will fallback to Google Maps)")