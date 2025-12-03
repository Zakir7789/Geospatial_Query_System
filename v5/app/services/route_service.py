import math
from app import get_db_connection, release_db_connection
import psycopg2.extras

class RouteService:
    
    @staticmethod
    def get_multimodal_route(start_lat, start_lon, end_lat, end_lon):
        """
        Calculates a Drive-Fly-Drive route.
        Returns None if distance is too short (< 500km) or no flight exists.
        """
        # 1. Check Total Distance (Haversine or simple approximation)
        # We can use a quick PostGIS query or Python math. 
        # Let's use Python for speed without DB roundtrip just for this check? 
        # Actually, we need DB for airports anyway.
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Check distance first
            cursor.execute("""
                SELECT ST_Distance(
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                ) / 1000.0 as dist_km;
            """, (start_lon, start_lat, end_lon, end_lat))
            
            total_dist = cursor.fetchone()['dist_km']
            
            if total_dist < 500:
                print(f"[RouteService] Distance {total_dist:.1f}km < 500km. Skipping flight.")
                return None

            # 2. Find Origin Airport
            # Closest large_airport
            origin_airport = RouteService._find_nearest_airport(cursor, start_lat, start_lon)
            if not origin_airport:
                return None
                
            # 3. Find Destination Airport
            dest_airport = RouteService._find_nearest_airport(cursor, end_lat, end_lon)
            if not dest_airport:
                return None
                
            if origin_airport['iata_code'] == dest_airport['iata_code']:
                return None

            # 4. Find Flight
            flight = RouteService._find_flight(cursor, origin_airport['iata_code'], dest_airport['iata_code'])
            
            if not flight:
                print(f"[RouteService] No flight found between {origin_airport['iata_code']} and {dest_airport['iata_code']}")
                return None
                
            # 5. Construct Response
            return {
                "type": "multimodal",
                "total_distance_km": round(total_dist, 1),
                "segments": [
                    {
                        "type": "DRIVING",
                        "from_coords": [start_lat, start_lon],
                        "to_coords": [origin_airport['lat'], origin_airport['lon']],
                        "label": f"Drive to {origin_airport['name']} ({origin_airport['iata_code']})"
                    },
                    {
                        "type": "FLIGHT",
                        "from_iata": origin_airport['iata_code'],
                        "to_iata": dest_airport['iata_code'],
                        "from_coords": [origin_airport['lat'], origin_airport['lon']],
                        "to_coords": [dest_airport['lat'], dest_airport['lon']],
                        "airline": flight['airline_code'],
                        "label": f"Flight to {dest_airport['name']} ({dest_airport['iata_code']})"
                    },
                    {
                        "type": "DRIVING",
                        "from_coords": [dest_airport['lat'], dest_airport['lon']],
                        "to_coords": [end_lat, end_lon],
                        "label": "Drive to Destination"
                    }
                ]
            }

        except Exception as e:
            print(f"[RouteService] Error: {e}")
            return None
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def _find_nearest_airport(cursor, lat, lon):
        query = """
            SELECT iata_code, name, city_name, 
                   ST_Y(geom::geometry) as lat, 
                   ST_X(geom::geometry) as lon,
                   ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000.0 as dist_km
            FROM airports
            WHERE iata_code IS NOT NULL
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1;
        """
        cursor.execute(query, (lon, lat, lon, lat))
        return cursor.fetchone()

    @staticmethod
    def _find_flight(cursor, origin_iata, dest_iata):
        query = """
            SELECT airline_code 
            FROM flight_routes 
            WHERE source_iata = %s AND dest_iata = %s
            LIMIT 1;
        """
        cursor.execute(query, (origin_iata, dest_iata))
        return cursor.fetchone()
