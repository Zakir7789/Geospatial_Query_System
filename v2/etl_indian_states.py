import csv
from db_config import get_connection

def insert_indian_states():
    conn = get_connection()
    cur = conn.cursor()

    with open("data/indian_states.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur.execute("""
                INSERT INTO states (country_id, name, alt_names, geom)
                VALUES (
                    (SELECT id FROM countries WHERE iso_code='IN' LIMIT 1),
                    %s,
                    %s,
                    NULL
                )
                ON CONFLICT DO NOTHING;
            """, (row['name'], [a.strip() for a in row['alt_names'].split(",") if a.strip()]))

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Indian states & UTs inserted successfully.")

if __name__ == "__main__":
    insert_indian_states()
