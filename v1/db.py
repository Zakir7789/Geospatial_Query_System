import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG


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
            print("❌ Error connecting to database:", e)

    def fetch_table(self, table_name):
        """Fetch canonical names from a table"""
        query = f"SELECT id, name FROM {table_name};"
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                rows = cur.fetchall()
                return pd.DataFrame(rows)  # return as DataFrame for easier processing
        except Exception as e:
            print(f"❌ Error fetching data from {table_name}:", e)
            return pd.DataFrame()

    def close(self):
        """Close DB connection"""
        if self.conn:
            self.conn.close()
            print("🔌 Database connection closed")
