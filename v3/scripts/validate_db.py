# scripts/validate_db.py
from scripts.db_config import connect_db
import pandas as pd

def validate_table(conn, table_name, sample_size=5):
    print(f"\n🔍 Validating table: {table_name}")
    cur = conn.cursor()

    # Check if table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        );
    """, (table_name,))
    exists = cur.fetchone()[0]

    if not exists:
        print(f"❌ Table '{table_name}' does not exist.")
        cur.close()
        return

    # Count total rows
    cur.execute(f"SELECT COUNT(*) FROM {table_name};")
    total_rows = cur.fetchone()[0]
    print(f"📊 Total rows: {total_rows}")

    # Get column names
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    columns = cur.fetchall()
    print("📋 Columns:")
    for col, dtype in columns:
        print(f"   - {col}: {dtype}")

    # Sample few rows
    cur.execute(f"SELECT * FROM {table_name} LIMIT {sample_size};")
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    df = pd.DataFrame(rows, columns=colnames)
    print("\n🧾 Sample data:")
    print(df)

    cur.close()


if __name__ == "__main__":
    print("🔗 Connecting to database...")
    conn = connect_db()

    # Validate tables
    for tbl in ["countries", "states", "cities"]:
        validate_table(conn, tbl)

    conn.close()
    print("\n✅ Validation complete.")
