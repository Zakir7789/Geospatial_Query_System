# scripts/load_to_postgres.py
import pandas as pd
from scripts.db_config import connect_db
from psycopg2.extras import execute_values
import os
import ast

def convert_to_pg_array(value):
    """Convert Python-style list string to PostgreSQL array literal."""
    if pd.isna(value) or value == '[]':
        return None
    try:
        # Safely evaluate string to Python list
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            # Escape double quotes and wrap properly for Postgres
            return "{" + ",".join([f'"{str(x).replace("\"", "\'")}"' for x in parsed]) + "}"
        else:
            return "{" + str(parsed) + "}"
    except Exception:
        # If not list-like, just wrap as single element array
        return "{" + str(value) + "}"
def load_csv_to_db(csv_path, table_name, columns):
    print(f"📦 Loading {os.path.basename(csv_path)} into {table_name}...")

    df = pd.read_csv(csv_path)
    df = df[columns]

    # Special handling for cities.alt_names
    if "alt_names" in df.columns:
        print("🧩 Converting alt_names to PostgreSQL array format...")
        df["alt_names"] = df["alt_names"].apply(convert_to_pg_array)

    conn = connect_db()
    cur = conn.cursor()

    # Prepare INSERT statement
    placeholders = ', '.join(['%s'] * len(columns))
    col_names = ', '.join(columns)
    insert_query = f"INSERT INTO {table_name} ({col_names}) VALUES %s"

    # Convert DataFrame rows to list of tuples
    data = [tuple(row) for row in df.to_numpy()]

    execute_values(cur, insert_query, data)
    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Successfully inserted {len(df)} rows into {table_name}.")

if __name__ == "__main__":
    # Load datasets
    load_csv_to_db("../data/countries.csv", "countries",
                   ["iso_code", "country_name", "capital", "continent", "population", "area_sq_km", "currency"])

    load_csv_to_db("../data/states.csv", "states",
                   ["country_code", "state_code", "state_name", "geonameid"])

    load_csv_to_db("../data/cities.csv", "cities",
                   ["city_name", "alt_names", "country_code", "state_code", "lat", "lon", "population"])
