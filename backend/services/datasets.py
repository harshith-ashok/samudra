"""Catalog + generic query layer over the app's tabular data sources, for the
Data Dashboard page (todo.md). Each dataset here is just a curated view onto
an existing services.data loader — this adds a uniform way to list, search,
sort, and correlate them, not a new data source.

Field types drive the frontend: "category"/"string" get free-text search,
"number" fields are sortable and offered as correlation axes. Display labels
for the dataset and its fields live in frontend i18n (datasets.catalog.* /
datasets.fields.*) — same boundary as every other UI-chrome string in this
app; only `source` (attribution) stays backend-side and untranslated, like
StationSummary.source and VesselsResponse.source elsewhere.
"""

import statistics

from services import data


def _stations_rows() -> list[dict]:
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "type": s["type"],
            "state": s["state"],
            "sst_c": s["latest"]["sst_c"],
            "salinity_psu": s["latest"]["salinity_psu"],
            "chlorophyll_mg_m3": s["latest"]["chlorophyll_mg_m3"],
        }
        for s in data.stations()
    ]


def _species_rows() -> list[dict]:
    return [
        {
            "sci": sp["sci"],
            "common": sp["common"],
            "region": sp["region"],
            "status": sp["status"] or "NE",
        }
        for sp in data.species()
    ]


def _catch_rows() -> list[dict]:
    return [
        {
            "id": r["id"],
            "species": r["species"],
            "region": r["region"],
            "date": r["date"],
            "tonnage": r["tonnage"],
            "sst_c": r["sst_c"],
            "advisory_status": r["advisory_status"],
        }
        for r in data.catch_records()
    ]


def _biodiversity_rows() -> list[dict]:
    bio = data.biodiversity()
    rows = [
        {
            "id": o["id"],
            "scientific_name": o["scientific_name"],
            "common_name": o["common_name"],
            "region": o["region"],
            "method": o["method"],
            "conservation_status": o["conservation_status"] or "NE",
            "confidence": o["confidence"],
            "year": o["year"],
        }
        for o in bio["occurrences"]
    ]
    rows += [
        {
            "id": d["id"],
            "scientific_name": d["scientific_name"],
            "common_name": d["common_name"],
            "region": d["region"],
            "method": d["method"],
            "conservation_status": d["conservation_status"] or "NE",
            "confidence": d["confidence"],
            "year": int(d["detected_month"][:4]),
        }
        for d in bio["edna_detections"]
    ]
    return rows


def _advisory_rows() -> list[dict]:
    return [
        {
            "id": a["id"],
            "region": a["region"],
            "species": a["species"],
            "status": a["status"],
            "issued": a["issued"],
            "severity": a["severity"],
        }
        for a in data.advisories()
    ]


def _pollution_rows() -> list[dict]:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "city": p["city"],
            "region": p["region"],
            "type": p["type"],
            "discharge_mld": p["discharge_mld"],
            "compliance": p["compliance"],
            "last_inspected": p["last_inspected"],
        }
        for p in data.pollution()
    ]


DATASETS: dict[str, dict] = {
    "stations": {
        "loader": _stations_rows,
        "fields": {
            "id": "string",
            "name": "string",
            "type": "category",
            "state": "category",
            "sst_c": "number",
            "salinity_psu": "number",
            "chlorophyll_mg_m3": "number",
        },
        "search_fields": ["id", "name", "type", "state"],
        "default_sort": "name",
        "source": "INCOIS-style buoy network plus simulated eDNA/advisory/coral stations",
    },
    "species": {
        "loader": _species_rows,
        "fields": {"sci": "string", "common": "string", "region": "category", "status": "category"},
        "search_fields": ["sci", "common", "region"],
        "default_sort": "common",
        "source": "OBIS/GBIF species list curated for this build",
    },
    "catch_records": {
        "loader": _catch_rows,
        "fields": {
            "id": "string",
            "species": "category",
            "region": "category",
            "date": "date",
            "tonnage": "number",
            "sst_c": "number",
            "advisory_status": "category",
        },
        "search_fields": ["id", "species", "region"],
        "default_sort": "date",
        "source": "CMFRI-style catch records — simulated tonnage paired with real species/region",
    },
    "biodiversity": {
        "loader": _biodiversity_rows,
        "fields": {
            "id": "string",
            "scientific_name": "string",
            "common_name": "string",
            "region": "category",
            "method": "category",
            "conservation_status": "category",
            "confidence": "number",
            "year": "number",
        },
        "search_fields": ["id", "scientific_name", "common_name", "region"],
        "default_sort": "scientific_name",
        "source": "Real OBIS/GBIF occurrences plus simulated eDNA detections layered on top",
    },
    "advisories": {
        "loader": _advisory_rows,
        "fields": {
            "id": "string",
            "region": "category",
            "species": "category",
            "status": "category",
            "issued": "date",
            "severity": "category",
        },
        "search_fields": ["id", "region", "species"],
        "default_sort": "issued",
        "source": "Fishing advisory notices issued for this build",
    },
    "pollution": {
        "loader": _pollution_rows,
        "fields": {
            "id": "string",
            "name": "string",
            "city": "category",
            "region": "category",
            "type": "category",
            "discharge_mld": "number",
            "compliance": "category",
            "last_inspected": "date",
        },
        "search_fields": ["id", "name", "city", "region"],
        "default_sort": "name",
        "source": "CPCB-style coastal treatment plant registry",
    },
}


def _dataset(dataset_id: str) -> dict:
    if dataset_id not in DATASETS:
        raise KeyError(dataset_id)
    return DATASETS[dataset_id]


def list_datasets() -> list[dict]:
    result = []
    for dataset_id, spec in DATASETS.items():
        rows = spec["loader"]()
        numeric_fields = [f for f, t in spec["fields"].items() if t == "number"]
        result.append(
            {
                "id": dataset_id,
                "record_count": len(rows),
                "fields": spec["fields"],
                "search_fields": spec["search_fields"],
                "numeric_fields": numeric_fields,
                "default_sort": spec["default_sort"],
                "correlatable": len(numeric_fields) >= 2,
                "source": spec["source"],
            }
        )
    return result


def get_records(dataset_id: str, search: str = "", sort: str | None = None, order: str = "asc") -> dict:
    spec = _dataset(dataset_id)
    rows = spec["loader"]()

    if search:
        needle = search.strip().lower()
        search_fields = spec["search_fields"]
        rows = [r for r in rows if any(needle in str(r.get(f, "")).lower() for f in search_fields)]

    sort_key = sort if sort in spec["fields"] else spec["default_sort"]
    reverse = order == "desc"
    # Missing values always sort last, in both directions — otherwise flipping
    # `order` would bury real values under None on one of the two directions.
    present = [r for r in rows if r.get(sort_key) is not None]
    missing = [r for r in rows if r.get(sort_key) is None]
    present.sort(key=lambda r: r[sort_key], reverse=reverse)

    return {"rows": present + missing, "total": len(rows), "sort": sort_key, "order": order}


def correlate(dataset_id: str, x: str, y: str) -> dict:
    spec = _dataset(dataset_id)
    if spec["fields"].get(x) != "number" or spec["fields"].get(y) != "number":
        raise ValueError(f"'{x}' and '{y}' must both be numeric fields of dataset '{dataset_id}'")

    rows = spec["loader"]()
    label_field = spec["search_fields"][0]
    points = [
        {"x": r[x], "y": r[y], "label": str(r.get(label_field, ""))}
        for r in rows
        if r.get(x) is not None and r.get(y) is not None
    ]
    r = _pearson([p["x"] for p in points], [p["y"] for p in points])
    return {
        "dataset": dataset_id,
        "x": x,
        "y": y,
        "points": points,
        "correlation_r": r,
        "n": len(points),
        "methodology": f"Pearson correlation coefficient between '{x}' and '{y}' across the {len(points)} {dataset_id} records where both fields are present.",
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    std_x = (sum((x - mean_x) ** 2 for x in xs)) ** 0.5
    std_y = (sum((y - mean_y) ** 2 for y in ys)) ** 0.5
    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 3)
