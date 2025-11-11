# scripts/fetch_cities.py
import pandas as pd
import requests, zipfile, io, os

def fetch_cities(output_path="../data/cities.csv"):
    print("🏙️ Downloading GeoNames cities data (cities500)...")

    url = "https://download.geonames.org/export/dump/cities500.zip"
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Download into memory buffer safely
    data = io.BytesIO()
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        data.write(chunk)
    data.seek(0)

    # Extract and read
    with zipfile.ZipFile(data) as z:
        with z.open("cities500.txt") as f:
            columns = [
                "geonameid", "name", "asciiname", "alternatenames",
                "latitude", "longitude", "feature_class", "feature_code",
                "country_code", "cc2", "admin1_code", "admin2_code",
                "admin3_code", "admin4_code", "population", "elevation",
                "dem", "timezone", "modification_date"
            ]
            # Read with better error handling for encoding
            df = pd.read_csv(f, sep="\t", names=columns, dtype=str, encoding_errors="ignore")

    # Convert numeric columns
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["population"] = pd.to_numeric(df["population"], errors="coerce")

    # Normalize text
    df["city_name"] = df["name"].str.lower().str.strip()
    df["alt_names"] = df["alternatenames"].fillna("").apply(
        lambda x: [n.strip().lower() for n in str(x).split(",") if n]
    )

    df = df.rename(columns={
        "latitude": "lat",
        "longitude": "lon",
        "country_code": "country_code",
        "admin1_code": "state_code"
    })

    df = df[["city_name", "alt_names", "country_code", "state_code", "lat", "lon", "population"]]

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"✅ Saved cleaned city data to {output_path}")
    print(f"📊 Total rows: {len(df):,}")
    print(df.head())

if __name__ == "__main__":
    fetch_cities()
