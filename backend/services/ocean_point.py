"""Click-anywhere-on-the-ocean point query (Phase 24 follow-up). There's no
live sensor grid in this build (see CLAUDE.md's non-goals — no live
ingestion), so a point that isn't one of the 23 real/simulated stations gets
an *estimate*: inverse-distance-weighted interpolation from the nearest real
stations, clearly labeled as such rather than presented as a live reading.

Two guardrails, both using tools already in this codebase:
  - on land? (global_land_mask, already a dependency via services/trajectory.py)
    -> rejected outright, a marine reading on land makes no sense.
  - too far from every station to interpolate honestly (open ocean far off
    the coast, nothing nearby to interpolate from) -> rejected rather than
    extrapolating a number with no real basis.
"""

from global_land_mask import globe

from services import data, geo

NEAREST_K = 4  # how many stations feed the interpolation
MAX_DISTANCE_KM = 600  # beyond this, no station is close enough to honestly estimate from


def estimate(lat: float, lng: float) -> dict:
    if globe.is_land(lat, lng):
        return {"error": "that point is on land, not ocean"}

    stations = data.stations()
    ranked = sorted(
        ({"station": s, "distance_km": geo.haversine_km(lat, lng, s["lat"], s["lng"])} for s in stations),
        key=lambda r: r["distance_km"],
    )
    if not ranked or ranked[0]["distance_km"] > MAX_DISTANCE_KM:
        return {"error": f"no monitored station within {MAX_DISTANCE_KM} km of that point to estimate from"}

    nearest = ranked[:NEAREST_K]
    # inverse-distance-squared weighting; the tiny epsilon guards a click
    # essentially on top of a station (distance ~0) from dividing by zero
    weights = [1.0 / (r["distance_km"] + 0.05) ** 2 for r in nearest]
    total_w = sum(weights)

    def weighted(field: str) -> float:
        return sum(w * r["station"]["latest"][field] for w, r in zip(weights, nearest)) / total_w

    return {
        "lat": round(lat, 4),
        "lng": round(lng, 4),
        "sst_c": round(weighted("sst_c"), 2),
        "salinity_psu": round(weighted("salinity_psu"), 2),
        "chlorophyll_mg_m3": round(weighted("chlorophyll_mg_m3"), 2),
        "nearest_station": nearest[0]["station"]["name"],
        "nearest_station_km": round(nearest[0]["distance_km"], 1),
        "stations_used": len(nearest),
        "methodology": (
            f"Inverse-distance-weighted estimate from the {len(nearest)} nearest real stations "
            f"(closest: {nearest[0]['station']['name']}, {round(nearest[0]['distance_km'], 1)} km away) — "
            "not a live reading at this exact point, there's no sensor here."
        ),
    }
