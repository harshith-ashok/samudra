"""
Builds curated seed JSON from the raw OBIS/GBIF pulls in backend/data/raw/.
Run after fetch_seed_data.py: uv run backend/data/build_seed_data.py
"""

import json
import os
import statistics

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
OUT_DIR = os.path.dirname(__file__)

SPECIES_META = {
    "Sardinella longiceps": {
        "common": "Indian oil sardine",
        "region": "Kerala coast",
        "status": "NT",
        "method": "survey",
    },
    "Chelonia mydas": {
        "common": "Green sea turtle",
        "region": "Odisha coast",
        "status": "VU",
        "method": "survey",
    },
    "Acropora formosa": {
        "common": "Staghorn coral",
        "region": "Lakshadweep atolls",
        "status": "VU",
        "method": "survey",
    },
    "Hippocampus kuda": {
        "common": "Yellow seahorse",
        "region": "Goa coast",
        "status": "VU",
        "method": "survey",
    },
    "Dugong dugon": {
        "common": "Dugong",
        "region": "Gulf of Mannar",
        "status": "VU",
        "method": "survey",
    },
    "Thunnus albacares": {
        "common": "Yellowfin tuna",
        "region": "Arabian Sea",
        "status": "LC",
        "method": "survey",
    },
    "Rastrelliger kanagurta": {
        "common": "Indian mackerel",
        "region": "Tamil Nadu coast",
        "status": "LC",
        "method": "survey",
    },
}


def load_raw(prefix, sci_name):
    path = os.path.join(RAW_DIR, f"{prefix}_{sci_name.replace(' ', '_')}.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


# Indian EEZ-ish bounding box — keeps occurrence records regionally relevant to the
# stations on the map (global OBIS pulls otherwise include e.g. African/Pacific records)
BBOX = {"lat_min": 5, "lat_max": 24, "lng_min": 66, "lng_max": 94}


def _in_bbox(lat, lng):
    return BBOX["lat_min"] <= lat <= BBOX["lat_max"] and BBOX["lng_min"] <= lng <= BBOX["lng_max"]


def extract_points(sci_name):
    """Return list of {lat, lng, year} from combined OBIS+GBIF raw records, Indian EEZ only."""
    points = []
    for rec in load_raw("obis", sci_name):
        lat = rec.get("decimalLatitude")
        lng = rec.get("decimalLongitude")
        year = rec.get("date_year")
        if lat is not None and lng is not None and year and _in_bbox(lat, lng):
            points.append({"lat": round(lat, 3), "lng": round(lng, 3), "year": int(year)})
    for rec in load_raw("gbif", sci_name):
        lat = rec.get("decimalLatitude")
        lng = rec.get("decimalLongitude")
        year = rec.get("year")
        if lat is not None and lng is not None and year and _in_bbox(lat, lng):
            points.append({"lat": round(lat, 3), "lng": round(lng, 3), "year": int(year)})
    # keep plausible years and dedupe roughly
    points = [p for p in points if 1990 <= p["year"] <= 2026]
    points.sort(key=lambda p: p["year"])
    return points


def build_biodiversity_records():
    records = []
    rid = 1
    for sci_name, meta in SPECIES_META.items():
        points = extract_points(sci_name)
        # keep every few points across the span, plus most recent, so the JSON stays small
        sample = points[::max(1, len(points) // 15)][:15] if points else []
        for p in sample:
            records.append(
                {
                    "id": f"bio-{rid:04d}",
                    "scientific_name": sci_name,
                    "common_name": meta["common"],
                    "region": meta["region"],
                    "method": meta["method"],
                    "conservation_status": meta["status"],
                    "lat": p["lat"],
                    "lng": p["lng"],
                    "year": p["year"],
                    "confidence": None,
                    "source": "OBIS/GBIF (real occurrence record)",
                }
            )
            rid += 1
    return records


def build_edna_detections():
    """Simulated eDNA detections layered on top of the real species list — no real wet-lab eDNA
    pipeline in this build, per the project's stated non-goals."""
    sim = [
        {
            "id": "edna-0001",
            "scientific_name": "Gymnothorax sp.",
            "common_name": "Moray eel (eDNA match)",
            "region": "Lakshadweep atolls",
            "method": "eDNA",
            "conservation_status": None,
            "confidence": 0.91,
            "detected_month": "2026-07",
        },
        {
            "id": "edna-0002",
            "scientific_name": "Doto sp.",
            "common_name": "Nudibranch (eDNA match)",
            "region": "Lakshadweep atolls",
            "method": "eDNA",
            "conservation_status": None,
            "confidence": 0.87,
            "detected_month": "2026-07",
        },
        {
            "id": "edna-0003",
            "scientific_name": "Gobiidae sp.",
            "common_name": "Deep-sea goby (eDNA match)",
            "region": "Lakshadweep atolls",
            "method": "eDNA",
            "conservation_status": None,
            "confidence": 0.98,
            "detected_month": "2026-07",
        },
    ]
    return sim


def range_shift_series(sci_name):
    """Yearly mean latitude — the basic trend used by the range-shift prediction endpoint."""
    points = extract_points(sci_name)
    by_year = {}
    for p in points:
        by_year.setdefault(p["year"], []).append(p["lat"])
    series = [
        {"year": y, "mean_lat": round(statistics.mean(v), 3), "n": len(v)}
        for y, v in sorted(by_year.items())
        if len(v) >= 1
    ]
    return series


def main():
    bio = build_biodiversity_records()
    edna = build_edna_detections()
    with open(os.path.join(OUT_DIR, "biodiversity.json"), "w") as f:
        json.dump({"occurrences": bio, "edna_detections": edna}, f, indent=2)
    print(f"biodiversity.json: {len(bio)} real occurrence records + {len(edna)} simulated eDNA detections")

    range_shift = {
        sci_name: range_shift_series(sci_name)
        for sci_name in ["Thunnus albacares", "Rastrelliger kanagurta"]
    }
    with open(os.path.join(OUT_DIR, "range_shift_series.json"), "w") as f:
        json.dump(range_shift, f, indent=2)
    for k, v in range_shift.items():
        print(f"range_shift_series.json[{k}]: {len(v)} yearly points")


if __name__ == "__main__":
    main()
