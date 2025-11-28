import psycopg2
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

def check_counts():
    try:
        conn = psycopg2.connect(
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASS", "password"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "geospatial_db")
        )
        cursor = conn.cursor()

        print("\n📊 DATABASE STATUS REPORT")
        print("=========================")
        print(f"{'TABLE':<15} | {'ACTUAL COUNT':<15} | {'EXPECTED (Approx)'}")
        print("-" * 55)

        # Check Countries
        cursor.execute("SELECT count(*) FROM countries;")
        c_count = cursor.fetchone()[0]
        print(f"{'Countries':<15} | {c_count:<15} | ~175 - 200")

        # Check States
        cursor.execute("SELECT count(*) FROM states;")
        s_count = cursor.fetchone()[0]
        print(f"{'States':<15} | {s_count:<15} | ~4,500")

        # Check Cities
        cursor.execute("SELECT count(*) FROM cities;")
        city_count = cursor.fetchone()[0]
        print(f"{'Cities':<15} | {city_count:<15} | ~7,300")
        
        print("-" * 55)
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error connecting to database: {e}")

if __name__ == "__main__":
    check_counts()