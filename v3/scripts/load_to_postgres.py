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
            # Also handle internal single quotes by replacing with two
            return "{" + ",".join([f'"{str(x).replace("\"", "\"\"")}"' for x in parsed]) + "}"
        else:
            return "{" + str(parsed) + "}"
    except Exception:
        # If not list-like, just wrap as single element array
        return "{" + str(value) + "}"

def load_csv_to_db(csv_path, table_name, columns):
    print(f" Loading {os.path.basename(csv_path)} into {table_name}...")

    df = pd.read_csv(csv_path)
    
    # Ensure DataFrame columns are in the exact order as 'columns' list
    df = df[columns]

    # Special handling for cities.alt_names
    if "alt_names" in df.columns:
        print("  Converting alt_names to PostgreSQL array format...")
        df["alt_names"] = df["alt_names"].apply(convert_to_pg_array)

    conn = connect_db()
    cur = conn.cursor()

    # Prepare INSERT statement
    placeholders = ', '.join(['%s'] * len(columns))
    col_names = ', '.join(columns)
    insert_query = f"INSERT INTO {table_name} ({col_names}) VALUES %s"

    # Convert DataFrame rows to list of tuples
    # Use df.itertuples for efficiency and type safety
    data = [tuple(row) for row in df.itertuples(index=False, name=None)]

    execute_values(cur, insert_query, data)
    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Successfully inserted {len(df)} rows into {table_name}.")

if __name__ == "__main__":
    
    # --- THIS IS THE FIX ---
    # We must clear the old data first to avoid UniqueViolation errors
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        print("Clearing old data (TRUNCATING tables)...")
        # TRUNCATE empties the tables, RESTART IDENTITY resets the primary keys
        cur.execute("TRUNCATE TABLE countries, states, cities RESTART IDENTITY CASCADE;")
        conn.commit()
        print("✅ Old data cleared.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error while truncating tables: {e}")
        exit(1)
    # --- END OF FIX ---

    # Now, load all datasets into the clean tables
    try:
        load_csv_to_db("data/countries.csv", "countries",
                       ["iso_code", "country_name", "capital", "continent", "population", "area_sq_km", "currency"])

        load_csv_to_db("data/states.csv", "states",
                       ["country_code", "state_code", "state_name", "geonameid"])

        load_csv_to_db("data/cities.csv", "cities",
                       ["city_name", "alt_names", "country_code", "state_code", "lat", "lon", "population"])
        
        print("\n🎉 All data loaded successfully!")
        
    except Exception as e:
        print(f"\n❌ An error occurred during data loading: {e}")
        print("Please check your CSV files and database connection.")