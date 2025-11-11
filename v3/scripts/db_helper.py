import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor
from scripts.db_config import DB_CONFIG  # Imports from your v3 folder

class Database:
    def __init__(self):
        self.conn = None

    def connect_db(self):
        """Establish connection to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                dbname=DB_CONFIG["dbname"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"],
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"]
            )
            print("✅ Database connected successfully")
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")

    def fetch_table_names(self):
        """Dynamically fetch all tables from public schema."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='public' AND table_type='BASE TABLE'
                    AND table_name NOT LIKE 'pg_%' AND table_name NOT LIKE 'sql_%';
                """)
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"❌ Error fetching table names: {e}")
            return []

    def fetch_table(self, table_name):
        """Fetch canonical names from a table"""
        query = f"SELECT name FROM {table_name};"
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return pd.DataFrame(rows)
        except Exception as e:
            print(f"❌ Error fetching data from {table_name}:", e)
            return pd.DataFrame()

    def close(self):
        if self.conn:
            self.conn.close()
            print("🔌 Database connection closed")