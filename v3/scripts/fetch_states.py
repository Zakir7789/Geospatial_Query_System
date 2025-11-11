# scripts/fetch_states.py
import pandas as pd
import requests
from io import StringIO
import os

def fetch_states(output_path="../data/states.csv"):
    print("📜 Downloading GeoNames admin1 (state) data...")

    url = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
    response = requests.get(url)
    response.raise_for_status()

    # Define columns as per GeoNames documentation
    columns = ["code", "name", "name_ascii", "geonameid"]

    # Load file
    df = pd.read_csv(StringIO(response.text), sep="\t", names=columns)

    # Extract country code and state code from the 'code' column (e.g. IN.MH)
    df["country_code"] = df["code"].apply(lambda x: x.split(".")[0])
    df["state_code"] = df["code"].apply(lambda x: x.split(".")[1] if "." in x else None)
    df["state_name"] = df["name"].str.lower().str.strip()

    # Select and reorder
    df = df[["country_code", "state_code", "state_name", "geonameid"]]

    # Create output directory if missing
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save cleaned dataset
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"✅ Saved cleaned state data to {output_path}")
    print(df.head())

if __name__ == "__main__":
    fetch_states()
