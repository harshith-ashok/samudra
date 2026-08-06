"""Aggregate views for the Analytics panel (Phase 13). Each function derives its
number from data already served elsewhere in the app (catch records, real
OBIS/GBIF occurrences, pollution snapshot, simulated vessel tracks) — nothing
here is a new data source, just a different cut of existing ones.
"""

import statistics

from services import data, vessels


def catch_vs_sst() -> dict:
    """Monthly (SST, tonnage) pairs per species/region, plus Pearson's r."""
    records = data.catch_records()
    series: dict[str, list[dict]] = {}
    for r in records:
        key = f"{r['species']}|{r['region']}"
        series.setdefault(key, []).append({"date": r["date"], "sst_c": r["sst_c"], "tonnage": r["tonnage"]})

    result = []
    for key, points in series.items():
        species, region = key.split("|")
        sst_vals = [p["sst_c"] for p in points]
        tonnage_vals = [p["tonnage"] for p in points]
        r = _pearson(sst_vals, tonnage_vals)
        result.append({"species": species, "region": region, "points": points, "correlation_r": r})
    return {
        "series": result,
        "methodology": "Pearson correlation coefficient between monthly SST and catch tonnage. sst_c is a simulated value paired with the (also simulated) tonnage series — see catch_records.json.",
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


def biodiversity_index() -> dict:
    """Distinct species observed per region — real OBIS/GBIF occurrences plus
    simulated eDNA detections layered on top of them (see biodiversity.json)."""
    bio = data.biodiversity()
    by_region: dict[str, set[str]] = {}
    for o in bio["occurrences"]:
        by_region.setdefault(o["region"], set()).add(o["scientific_name"])
    for d in bio["edna_detections"]:
        by_region.setdefault(d["region"], set()).add(d["scientific_name"])
    regions = [{"region": region, "species_count": len(species)} for region, species in by_region.items()]
    regions.sort(key=lambda r: -r["species_count"])
    return {
        "regions": regions,
        "methodology": "Count of distinct species scientific names observed per region — real OBIS/GBIF occurrence records plus simulated eDNA detections layered on top (see biodiversity.json). A rough indicator, not a formal diversity index (e.g. Shannon).",
    }


def compliance_trend() -> dict:
    """Illustrative monthly % of treatment plants compliant, since CPCB inspection
    history isn't available without a data.gov.in API key (see services/pollution.py).
    Interpolates from today's snapshot back to a plausible starting point rather
    than inventing an unrelated series.
    """
    plants = data.pollution()
    current_pct = round(100 * sum(1 for p in plants if p["compliance"] == "compliant") / len(plants), 1)
    months = ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]
    start_pct = min(95.0, current_pct + 15)  # assume a mild decline into the current snapshot
    step = (current_pct - start_pct) / (len(months) - 1)
    trend = [{"month": m, "pct_compliant": round(start_pct + step * i, 1)} for i, m in enumerate(months)]
    return {
        "trend": trend,
        "current_snapshot_pct": current_pct,
        "methodology": "Illustrative trend interpolated toward today's real plant-count snapshot — CPCB doesn't expose historical inspection data without a data.gov.in API key we don't have. Only the final point (current_snapshot_pct) is computed from actual plant records.",
    }


def vessel_activity() -> dict:
    """Sample each vessel's track at evenly-spaced points across its loop and
    count how often it falls inside an MPA — a real derived statistic over the
    simulated tracks, not a fabricated time series.
    """
    zones = data.mpa_zones()
    samples_per_loop = 12
    zone_counts = {z["id"]: {"zone_id": z["id"], "zone_name": z["name"], "violation_ticks": 0, "total_ticks": 0} for z in zones}

    for v in vessels.FLEET:
        for i in range(samples_per_loop):
            t = i / samples_per_loop
            lat, lng, _ = vessels.position_on_track(v["track"], t)
            for zone in zones:
                zone_counts[zone["id"]]["total_ticks"] += 1
                if vessels.point_in_polygon(lat, lng, zone["polygon"]):
                    zone_counts[zone["id"]]["violation_ticks"] += 1

    return {
        "zones": list(zone_counts.values()),
        "samples_per_vessel_loop": samples_per_loop,
        "methodology": f"Each vessel's fixed loop track is sampled at {samples_per_loop} evenly-spaced points and checked against each MPA polygon — a real point-in-polygon computation over the simulated tracks, not a persisted historical log.",
    }
