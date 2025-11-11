# scripts/db_config.py
import psycopg2

def connect_db():
    """Establish connection to PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="geospatial_db",
            user="postgres",
            password="admin123",
            port=5432
        )
        print("[INFO] Database connection established.")
        return conn
    except Exception as e:
        print("[ERROR] Could not connect to database:", e)
        return None
