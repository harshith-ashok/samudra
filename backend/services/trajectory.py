"""Species movement trajectory (Phase 15 — replaces the single-lat range-shift
line with a full lat/lng path).

OBIS/GBIF records in this build carry year-level dates only, not month, so
binning is by year rather than month — binning to a false monthly precision
would misrepresent what the underlying data actually supports. The rest of
the pipeline matches the todo: per-year centroid -> exponential smoothing ->
forward extrapolation from the recent velocity vector.
"""

import math

import numpy as np

from services import conclusions, data

SMOOTHING_ALPHA = 0.5
FORECAST_YEARS = 5
MIN_YEARS = 3


def species_id(scientific_name: str) -> str:
    return scientific_name.strip().lower().replace(" ", "_")


def _bearing_label(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    dlng = math.radians(lng2 - lng1)
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    x = math.sin(dlng) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlng)
    bearing = (math.degrees(math.atan2(x, y)) + 360) % 360
    labels = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return labels[round(bearing / 22.5) % 16]


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def trajectory(query_species_id: str) -> dict:
    occurrences = [
        o for o in data.biodiversity()["occurrences"]
        if species_id(o["scientific_name"]) == query_species_id.lower()
    ]
    if not occurrences:
        return {"error": f"no occurrence records found for species id '{query_species_id}'"}

    sci = occurrences[0]["scientific_name"]
    common = occurrences[0]["common_name"]

    by_year: dict[int, list[dict]] = {}
    for o in occurrences:
        by_year.setdefault(o["year"], []).append(o)
    years = sorted(by_year)
    if len(years) < MIN_YEARS:
        return {"error": f"only {len(years)} distinct year(s) of occurrence data for {sci} — need at least {MIN_YEARS}"}

    historical = [
        {
            "year": y,
            "lat": round(float(np.mean([p["lat"] for p in by_year[y]])), 4),
            "lng": round(float(np.mean([p["lng"] for p in by_year[y]])), 4),
            "n": len(by_year[y]),
        }
        for y in years
    ]

    smoothed_lat = [historical[0]["lat"]]
    smoothed_lng = [historical[0]["lng"]]
    for pt in historical[1:]:
        smoothed_lat.append(SMOOTHING_ALPHA * pt["lat"] + (1 - SMOOTHING_ALPHA) * smoothed_lat[-1])
        smoothed_lng.append(SMOOTHING_ALPHA * pt["lng"] + (1 - SMOOTHING_ALPHA) * smoothed_lng[-1])
    smoothed = [
        {"year": historical[i]["year"], "lat": round(smoothed_lat[i], 4), "lng": round(smoothed_lng[i], 4)}
        for i in range(len(historical))
    ]

    year_gap = max(1, years[-1] - years[-2])
    lat_velocity = (smoothed_lat[-1] - smoothed_lat[-2]) / year_gap
    lng_velocity = (smoothed_lng[-1] - smoothed_lng[-2]) / year_gap

    forecast = []
    for i in range(1, FORECAST_YEARS + 1):
        forecast.append(
            {
                "year": years[-1] + i,
                "lat": round(smoothed_lat[-1] + lat_velocity * i, 4),
                "lng": round(smoothed_lng[-1] + lng_velocity * i, 4),
            }
        )

    drift_km = round(_haversine_km(smoothed[0]["lat"], smoothed[0]["lng"], smoothed[-1]["lat"], smoothed[-1]["lng"]), 1)
    direction = _bearing_label(smoothed[0]["lat"], smoothed[0]["lng"], smoothed[-1]["lat"], smoothed[-1]["lng"])

    confidence = "low" if len(years) < 5 else "medium"
    conclusion = conclusions.conclude(
        f"{common} ({sci}) occurrence centroid drifted about {drift_km} km {direction} across {len(years)} years "
        f"of OBIS/GBIF records ({years[0]}-{years[-1]}), and the recent velocity vector projects it continuing "
        f"{direction} over the next {FORECAST_YEARS} years.",
        confidence,
    )

    return {
        "species_id": query_species_id.lower(),
        "scientific_name": sci,
        "common_name": common,
        "historical": historical,
        "smoothed": smoothed,
        "forecast": forecast,
        "drift_km": drift_km,
        "direction": direction,
        "conclusion": conclusion,
        "confidence": confidence,
        "methodology": (
            f"Per-year mean lat/lng centroid of real OBIS/GBIF occurrence records, smoothed with exponential "
            f"smoothing (alpha={SMOOTHING_ALPHA}) to reduce year-to-year sampling noise, then extrapolated "
            f"{FORECAST_YEARS} years forward using the velocity between the last two smoothed points. Binned by "
            "year, not month — the source records only carry year-level dates."
        ),
        "source": "OBIS/GBIF real occurrence records",
    }
