"""One-off script to source one real, CC-licensed photo per species from GBIF's
occurrence media (real observation photos with attribution metadata), falling
back to a genus-level search for species.json entries that aren't resolved to
species rank (e.g. "Gymnothorax sp.", the eDNA-only moray eel match).

Run with: uv run backend/data/fetch_species_media.py
Writes backend/data/species_media.json, keyed by the same species_id slug the
frontend already derives from the scientific name (see utils/speciesId.ts and
services/trajectory.py's species_id()).
"""

import json
import os
import time
import urllib.parse
import urllib.request

DATA_DIR = os.path.dirname(__file__)
OCCURRENCE_SEARCH_URL = "https://api.gbif.org/v1/occurrence/search"


def species_id(scientific_name: str) -> str:
    return scientific_name.strip().lower().replace(" ", "_")


def _search(params: dict, retries: int = 3) -> list[dict]:
    q = urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{OCCURRENCE_SEARCH_URL}?{q}", timeout=20) as r:
                return json.load(r).get("results", [])
        except Exception as e:
            if attempt == retries - 1:
                print(f"  search failed after {retries} attempts: {e}")
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def find_media(sci_name: str) -> dict | None:
    """Exact scientificName match first; falls back to a genus-level free-text
    search for names GBIF's backbone can't resolve to species rank (e.g. "sp.")."""
    for params in (
        {"scientificName": sci_name, "mediaType": "StillImage", "limit": 5},
        {"q": sci_name.split()[0], "mediaType": "StillImage", "limit": 5},
    ):
        for record in _search(params):
            for m in record.get("media", []):
                if m.get("type") == "StillImage" and m.get("identifier"):
                    return {
                        "identifier": m["identifier"],
                        "license": m.get("license", "unknown"),
                        "rights_holder": m.get("rightsHolder") or m.get("creator") or "unknown",
                        "matched_name": record.get("scientificName", sci_name),
                        "is_genus_level": params.get("scientificName") is None,
                    }
    return None


def main():
    with open(os.path.join(DATA_DIR, "species.json")) as f:
        species = json.load(f)

    media_by_id: dict[str, dict] = {}
    for s in species:
        sci = s["sci"]
        sid = species_id(sci)
        print(f"fetching media for {sci} ({sid})...")
        found = find_media(sci)
        if not found:
            print(f"  no media found for {sci}")
            time.sleep(0.3)
            continue

        genus_note = (
            f" — genus-level representative photo ({found['matched_name']}), not this exact species/morph"
            if found["is_genus_level"]
            else ""
        )
        media_by_id[sid] = {
            "image_url": found["identifier"],
            "attribution": f"{found['rights_holder']} via GBIF/iNaturalist, {found['license']}{genus_note}",
            "source": "GBIF occurrence media (real observation photo)",
            "license": found["license"],
            "is_genus_level": found["is_genus_level"],
        }
        print(f"  ok: {found['identifier']}")
        time.sleep(0.3)

    out_path = os.path.join(DATA_DIR, "species_media.json")
    with open(out_path, "w") as f:
        json.dump(media_by_id, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {len(media_by_id)}/{len(species)} species to {out_path}")


if __name__ == "__main__":
    main()
