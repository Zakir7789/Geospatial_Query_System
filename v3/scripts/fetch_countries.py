# scripts/fetch_countries.py
import pandas as pd
import requests
from io import StringIO
import os

def fetch_countries(output_path="../data/countries.csv"):
    print("🌍 Downloading GeoNames country data...")

    url = "https://download.geonames.org/export/dump/countryInfo.txt"
    response = requests.get(url)
    response.raise_for_status()

    # Filter comment lines (start with #)
    lines = [line for line in response.text.split("\n") if not line.startswith("#") and line.strip() != ""]
    data = "\n".join(lines)

    # Define the correct columns based on GeoNames documentation
    columns = [
        "ISO", "ISO3", "ISO-Numeric", "fips", "Country", "Capital", "Area(in sq km)",
        "Population", "Continent", "tld", "CurrencyCode", "CurrencyName",
        "Phone", "Postal Code Format", "Postal Code Regex", "Languages",
        "geonameid", "neighbours", "EquivalentFipsCode"
    ]

    # Read into DataFrame
    df = pd.read_csv(StringIO(data), sep="\t", names=columns)

    # Select only needed columns
    df = df[["ISO", "Country", "Capital", "Continent", "Population", "Area(in sq km)", "CurrencyCode"]]

    # Rename and clean
    df = df.rename(columns={
        "ISO": "iso_code",
        "Country": "country_name",
        "Continent": "continent",
        "Capital": "capital",
        "Population": "population",
        "Area(in sq km)": "area_sq_km",
        "CurrencyCode": "currency"
    })

    df["country_name"] = df["country_name"].str.strip().str.lower()

    # Create output folder if missing
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"✅ Saved cleaned country data to {output_path}")
    print(df.head())

if __name__ == "__main__":
    fetch_countries()
