
import requests
import io
import zipfile

URL = "http://download.geonames.org/export/dump/cities15000.zip"

def search_in_zip():
    print("Downloading zip header...")
    response = requests.get(URL)
    print("Searching for 'Hosur'...")
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        with z.open('cities15000.txt') as f:
            for line in f:
                decoded = line.decode('utf-8')
                if "Hosur" in decoded:
                    row = decoded.strip().split('\t')
                    print(f"FOUND: Name={row[1].encode('ascii', 'replace')}, Ascii={row[2].encode('ascii', 'replace')}, Pop={row[14]}")

if __name__ == "__main__":
    search_in_zip()
