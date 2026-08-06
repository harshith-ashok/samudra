"""
One-off script to pull real species occurrence data from OBIS/GBIF for SAMUDRA seed data.
Run with: uv run backend/data/fetch_seed_data.py
Writes raw responses to backend/data/raw/ for inspection; curated seed JSON is hand-built
separately in build_seed_data.py using these as ground truth for real lat/lng/year values.
"""

import json
import urllib.request
import urllib.parse
import time
import os

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
os.makedirs(RAW_DIR, exist_ok=True)

SPECIES = [
    "Sardinella longiceps",
    "Chelonia mydas",
    "Acropora formosa",
    "Hippocampus kuda",
    "Dugong dugon",
    "Thunnus albacares",
    "Rastrelliger kanagurta",
]

# Rough Indian EEZ bounding box to keep occurrence records regionally relevant
BBOX = {"lat_min": 5, "lat_max": 24, "lng_min": 66, "lng_max": 94}


def fetch_obis(sci_name: str, size: int = 200):
    q = urllib.parse.urlencode({"scientificname": sci_name, "size": size})
    url = f"https://api.obis.org/v3/occurrence?{q}"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    return data.get("results", [])


def fetch_gbif(sci_name: str, limit: int = 200):
    q = urllib.parse.urlencode(
        {
            "scientificName": sci_name,
            "limit": limit,
            "hasCoordinate": "true",
            "decimalLatitude": f"{BBOX['lat_min']},{BBOX['lat_max']}",
            "decimalLongitude": f"{BBOX['lng_min']},{BBOX['lng_max']}",
        }
    )
    url = f"https://api.gbif.org/v1/occurrence/search?{q}"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    return data.get("results", [])


def main():
    for sp in SPECIES:
        print(f"Fetching OBIS for {sp}...")
        try:
            obis_results = fetch_obis(sp)
        except Exception as e:
            print(f"  OBIS failed: {e}")
            obis_results = []
        with open(os.path.join(RAW_DIR, f"obis_{sp.replace(' ', '_')}.json"), "w") as f:
            json.dump(obis_results, f)
        print(f"  {len(obis_results)} OBIS records")
        time.sleep(0.5)

        print(f"Fetching GBIF for {sp}...")
        try:
            gbif_results = fetch_gbif(sp)
        except Exception as e:
            print(f"  GBIF failed: {e}")
            gbif_results = []
        with open(os.path.join(RAW_DIR, f"gbif_{sp.replace(' ', '_')}.json"), "w") as f:
            json.dump(gbif_results, f)
        print(f"  {len(gbif_results)} GBIF records")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
