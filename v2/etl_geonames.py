import os
import csv
import psycopg2
from psycopg2.extras import execute_values

DATA_FILE = "data/allCountries.txt"

def connect_db():
    return psycopg2.connect(
        dbname="geoparser",
        user="postgres",
        password="admin123",
        host="localhost",
        port="5432"
    )

def load_data():
    conn = connect_db()
    cur = conn.cursor()

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 15:
                continue

            geoname_id = int(row[0])
            name = row[1]
            asciiname = row[2]
            alt_names = row[3].split(",") if row[3] else []
            latitude = float(row[4])
            longitude = float(row[5])
            feature_class = row[6]
            feature_code = row[7]
            country_code = row[8]
            admin1_code = row[10]
            population = int(row[14]) if row[14].isdigit() else 0

            # Geometry (PostGIS point)
            geom = f"SRID=4326;POINT({longitude} {latitude})"

            # Countries
            if feature_class == "A" and feature_code == "PCLI":
                cur.execute("""
                    INSERT INTO countries (name, iso_code, alt_names, geom)
                    VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))
                    ON CONFLICT DO NOTHING
                """, (name, country_code, alt_names, f"POINT({longitude} {latitude})"))

                # Aliases
                for alias in alt_names:
                    cur.execute("""
                        INSERT INTO aliases (alias, canonical_table, canonical_id, source)
                        VALUES (%s, 'countries', 
                               (SELECT id FROM countries WHERE name=%s LIMIT 1),
                               'geonames')
                        ON CONFLICT DO NOTHING
                    """, (alias.strip().lower(), name))

            # States
            elif feature_class == "A" and feature_code == "ADM1":
                cur.execute("""
                    INSERT INTO states (name, alt_names, country_id, geom)
                    VALUES (%s, %s,
                           (SELECT id FROM countries WHERE iso_code=%s LIMIT 1),
                           ST_GeomFromText(%s, 4326))
                    ON CONFLICT DO NOTHING
                """, (name, alt_names, country_code, f"POINT({longitude} {latitude})"))

                for alias in alt_names:
                    cur.execute("""
                        INSERT INTO aliases (alias, canonical_table, canonical_id, source)
                        VALUES (%s, 'states',
                               (SELECT id FROM states WHERE name=%s LIMIT 1),
                               'geonames')
                        ON CONFLICT DO NOTHING
                    """, (alias.strip().lower(), name))

            # Cities
            elif feature_class == "P" and population >= 5000:
                cur.execute("""
                    INSERT INTO cities (name, alt_names, country_id, population, geom)
                    VALUES (%s, %s,
                           (SELECT id FROM countries WHERE iso_code=%s LIMIT 1),
                           %s,
                           ST_GeomFromText(%s, 4326))
                    ON CONFLICT DO NOTHING
                """, (name, alt_names, country_code, population, f"POINT({longitude} {latitude})"))

                for alias in alt_names:
                    cur.execute("""
                        INSERT INTO aliases (alias, canonical_table, canonical_id, source)
                        VALUES (%s, 'cities',
                               (SELECT id FROM cities WHERE name=%s LIMIT 1),
                               'geonames')
                        ON CONFLICT DO NOTHING
                    """, (alias.strip().lower(), name))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("🚀 Loading GeoNames full dataset into PostgreSQL...")
    load_data()
    print("✅ Done.")
