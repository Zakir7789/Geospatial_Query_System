if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app import get_db_connection, release_db_connection
import psycopg2.extras

class GeoService:
    
    @staticmethod
    def get_location_metadata(search_query, context_country=None):
        """
        Unified Resolver with Context Awareness.
        """
        term = search_query.strip()
        
        # --- CRITICAL CONTEXT CHECK ---
        if "," in term:
            return None

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cursor.execute("SELECT set_limit(0.4);")

            query = """
                WITH all_matches AS (
                    -- 1. COUNTRIES
                    SELECT country_name as name, 'country' as type, population, geom,
                           similarity(country_name, %s) as sim_score,
                           country_name as parent_country
                    FROM countries
                    WHERE similarity(country_name, %s) > 0.4 OR iso_code ILIKE %s

                    UNION ALL

                    -- 2. STATES
                    SELECT state_name as name, 'state' as type, 0 as population, geom,
                           similarity(state_name, %s) as sim_score,
                           (SELECT country_name FROM countries WHERE countries.iso_code = states.country_code LIMIT 1) as parent_country
                    FROM states
                    WHERE similarity(state_name, %s) > 0.4 OR state_code ILIKE %s

                    UNION ALL

                    -- 3. CITIES
                    SELECT city_name as name, 'city' as type, population, geom,
                           CASE WHEN %s ILIKE ANY(alt_names) THEN 1.0 ELSE similarity(city_name, %s) END as sim_score,
                           (SELECT country_name FROM countries WHERE countries.iso_code = cities.country_code LIMIT 1) as parent_country
                    FROM cities
                    WHERE similarity(city_name, %s) > 0.4 OR %s ILIKE ANY(alt_names)
                )
                SELECT name as city_name, type, population, sim_score,
                       ST_Y(ST_Centroid(geom)) as lat, ST_X(ST_Centroid(geom)) as lon,
                       parent_country
                FROM all_matches
                ORDER BY (CASE WHEN parent_country ILIKE %s THEN 1 ELSE 0 END) DESC, sim_score DESC, population DESC
                LIMIT 1;
            """
            
            query_params = [term] * 10
            context_val = context_country if context_country else "NON_EXISTENT_COUNTRY"
            query_params.append(context_val)
            
            cursor.execute(query, tuple(query_params))
            result = cursor.fetchone()
            
            # Fallback Logic
            if result and context_country:
                if result['parent_country'] and context_country.lower() not in result['parent_country'].lower():
                     if result['sim_score'] < 0.9:
                         return None

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