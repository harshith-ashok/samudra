"""Species movement trajectory (Phase 15 — replaces the single-lat range-shift
line with a full lat/lng path).

OBIS/GBIF records in this build carry year-level dates only, not month, so
binning is by year rather than month — binning to a false monthly precision
would misrepresent what the underlying data actually supports. The rest of
the pipeline matches the todo: per-year centroid -> exponential smoothing ->
forward extrapolation from the recent velocity vector.

A handful of the real GBIF/OBIS pulls in this seed set carry inland
coordinates — almost all of them within a few km of the real coast (a harbor
survey point or coastal town pixel the land mask rounds to "land"), which is
corrected by snapping to the nearest water pixel, same as a GPS-precision fix.
A few are hundreds of km inland (e.g. central Madhya Pradesh for a "Goa coast"
seahorse record) — those aren't a rounding error, they're unrelated bad data,
so past RAW_RECORD_SNAP_MAX_KM they're dropped rather than snapped to an arbitrary
distant position that wouldn't represent where the record actually is.

Separately, the *smoothed centroid* of several corrected in-water points can
still land back on a thin strip of coastline (Kerala's backwaters are
jagged) — that's a property of averaging near a coast, not a bad record, so
it's always snapped (see _nearest_water) rather than ever dropped, since it's
math we computed, not a record we're claiming was observed there.

Getting every individual point into water isn't the whole fix, though: a
straight line between two in-water points on opposite coasts (real records
this sparse can put one year's centroid off Kerala and the next off Odisha)
cuts straight across the Indian subcontinent. `route_historical` /
`route_forecast` give the frontend a real maritime route (searoute) for
exactly the segments where a straight line would cross land, leaving short/
already-clear segments as plain lines.

Two things this got wrong before landing on the current shape, worth noting
so they don't get "fixed" back in:
  1. A hand-rolled alternative (recursively nudge a land-crossing segment's
     midpoint to the nearest water pixel) was tried instead of searoute. It
     doesn't respect line direction — the nearest water to an inland midpoint
     is often not on any sensible path between the endpoints — so it neither
     converged reliably nor ran fast (multi-second recursion blowup on the
     harder segments). searoute, built for exactly this problem, just works.
  2. searoute snaps its start/end to the nearest node in its own routing
     network, not the exact query point — sometimes 100+km off near a sparse
     part of the network (the India/Bangladesh maritime border, in
     particular). Forcing continuity between consecutive per-year segments
     (pinning searoute's output back onto the query point, or chaining from
     wherever it actually ended) just relocated the land-crossing problem to
     the seam between segments instead of fixing it. Each segment is
     therefore returned independently rather than concatenated into one
     polyline — see route_segments_between() — so the frontend draws each
     hop as its own line; a small gap between two hops is just a gap, never
     a fresh, unchecked line across land.
"""

import math

import numpy as np
import searoute as sr
from global_land_mask import globe

from services import conclusions, data

SMOOTHING_ALPHA = 0.5
FORECAST_YEARS = 5
MIN_YEARS = 3
KM_PER_DEGREE = 111.0
RAW_RECORD_SNAP_MAX_KM = 165  # ~1.5 degrees — beyond this a raw record's land
# coordinate is treated as unrelated bad data (wrong region entirely) and
# dropped, not snapped to a fabricated position
DERIVED_POINT_SNAP_MAX_DEG = 8.0  # centroid/forecast points are always safe to
# nudge (they're math we computed, not a record), so this is generous


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


def _nearest_water(lat: float, lng: float, max_radius_deg: float, step_deg: float = 0.02) -> tuple[float, float] | None:
    """Outward ring search for the nearest non-land pixel. Returns None if
    nothing is found within max_radius_deg (the point is too far from any
    coast to plausibly be a precision error).

    Deliberately returns full-precision coordinates, not rounded — rounding a
    candidate that's only just water (found right at the water/land grid
    boundary) can shift it back onto a land pixel. Callers round for display
    after this, once the point no longer needs to survive another is_land check."""
    if not globe.is_land(lat, lng):
        return lat, lng
    r = step_deg
    while r <= max_radius_deg:
        n_points = max(8, int(2 * math.pi * r / step_deg))
        for i in range(n_points):
            theta = 2 * math.pi * i / n_points
            cand_lat, cand_lng = lat + r * math.sin(theta), lng + r * math.cos(theta)
            if not globe.is_land(cand_lat, cand_lng):
                return cand_lat, cand_lng
        r += step_deg
    return None


def _round_keeping_water(lat: float, lng: float) -> tuple[float, float]:
    """round(x, 4) alone can shift a point that's only just water back onto a
    land pixel (grid resolution is ~0.0083°, well above 4-decimal precision,
    but a candidate found right at the boundary can still cross it). Backs off
    to more decimal places until the rounded point survives an is_land check."""
    if not globe.is_land(lat, lng):
        for decimals in (4, 5, 6):
            r_lat, r_lng = round(lat, decimals), round(lng, decimals)
            if not globe.is_land(r_lat, r_lng):
                return r_lat, r_lng
    return lat, lng  # give up rounding rather than risk re-landing it


def _segment_crosses_land(lat1: float, lng1: float, lat2: float, lng2: float, samples: int = 15) -> bool:
    lats = np.linspace(lat1, lat2, samples)
    lngs = np.linspace(lng1, lng2, samples)
    return any(globe.is_land(la, lo) for la, lo in zip(lats, lngs))


def route_between(p1: dict, p2: dict) -> list[list[float]]:
    """One independently-computed hop between two points: a straight line if
    that's already clear of land, otherwise a real maritime route (searoute
    — a navigable sea-route network, not just "technically not land"). Falls
    back to a straight line if searoute raises rather than dropping the hop.
    searoute uses (lng, lat) GeoJSON order; the app uses (lat, lng)
    throughout, so this is the one place that swaps."""
    if not _segment_crosses_land(p1["lat"], p1["lng"], p2["lat"], p2["lng"]):
        return [[p1["lat"], p1["lng"]], [p2["lat"], p2["lng"]]]
    try:
        feature = sr.searoute((p1["lng"], p1["lat"]), (p2["lng"], p2["lat"]))
        return [[lat, lng] for lng, lat in feature["geometry"]["coordinates"]]
    except Exception:
        return [[p1["lat"], p1["lng"]], [p2["lat"], p2["lng"]]]


def route_segments_between(points: list[dict]) -> list[list[list[float]]]:
    """One route_between() result per consecutive pair, kept as separate
    segments rather than concatenated into a single polyline — see the
    module docstring for why forcing them to share an exact joint
    reintroduces the exact problem this is meant to fix."""
    if len(points) < 2:
        return []
    return [route_between(points[i], points[i + 1]) for i in range(len(points) - 1)]


def trajectory(query_species_id: str) -> dict:
    raw_occurrences = [
        o for o in data.biodiversity()["occurrences"]
        if species_id(o["scientific_name"]) == query_species_id.lower()
    ]
    if not raw_occurrences:
        return {"error": f"no occurrence records found for species id '{query_species_id}'"}

    sci = raw_occurrences[0]["scientific_name"]
    common = raw_occurrences[0]["common_name"]

    occurrences = []
    corrected_count = 0
    dropped_count = 0
    for o in raw_occurrences:
        snapped = _nearest_water(o["lat"], o["lng"], max_radius_deg=RAW_RECORD_SNAP_MAX_KM / KM_PER_DEGREE)
        if snapped is None:
            dropped_count += 1
            continue
        lat, lng = snapped
        if (lat, lng) != (o["lat"], o["lng"]):
            corrected_count += 1
        occurrences.append({**o, "lat": lat, "lng": lng})

    if not occurrences:
        return {"error": f"all {len(raw_occurrences)} occurrence record(s) for {sci} were on land, too far from water to correct — none usable"}

    by_year: dict[int, list[dict]] = {}
    for o in occurrences:
        by_year.setdefault(o["year"], []).append(o)
    years = sorted(by_year)
    if len(years) < MIN_YEARS:
        dropped_note = f" ({dropped_count} record(s) too far inland to correct were excluded)" if dropped_count else ""
        return {"error": f"only {len(years)} distinct usable year(s) of occurrence data for {sci} — need at least {MIN_YEARS}{dropped_note}"}

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

    # The smoothed centroid — not any individual input record — is what's actually
    # drawn on the map/chart, so it's what needs to end up in water. Snap after
    # smoothing (a wide radius here, since this is always safe to nudge — it's
    # derived math, not a record), then use the snapped values for velocity/
    # forecast so the whole path stays continuous.
    snapped_smoothed = [
        _nearest_water(smoothed_lat[i], smoothed_lng[i], max_radius_deg=DERIVED_POINT_SNAP_MAX_DEG) or (smoothed_lat[i], smoothed_lng[i])
        for i in range(len(smoothed_lat))
    ]
    smoothed_lat = [p[0] for p in snapped_smoothed]
    smoothed_lng = [p[1] for p in snapped_smoothed]
    smoothed = []
    for i in range(len(historical)):
        r_lat, r_lng = _round_keeping_water(smoothed_lat[i], smoothed_lng[i])
        smoothed.append({"year": historical[i]["year"], "lat": r_lat, "lng": r_lng})

    year_gap = max(1, years[-1] - years[-2])
    lat_velocity = (smoothed_lat[-1] - smoothed_lat[-2]) / year_gap
    lng_velocity = (smoothed_lng[-1] - smoothed_lng[-2]) / year_gap

    forecast = []
    for i in range(1, FORECAST_YEARS + 1):
        raw_lat, raw_lng = smoothed_lat[-1] + lat_velocity * i, smoothed_lng[-1] + lng_velocity * i
        f_lat, f_lng = _nearest_water(raw_lat, raw_lng, max_radius_deg=DERIVED_POINT_SNAP_MAX_DEG) or (raw_lat, raw_lng)
        r_lat, r_lng = _round_keeping_water(f_lat, f_lng)
        forecast.append({"year": years[-1] + i, "lat": r_lat, "lng": r_lng})

    # For the map only — the chart plots smoothed/forecast against year directly,
    # where a land crossing isn't meaningful (it's a value axis, not geography).
    # Each is a list of independently-routed segments, not one flat polyline
    # — see route_segments_between().
    route_historical = route_segments_between(smoothed)
    route_forecast = route_segments_between([smoothed[-1], *forecast])

    drift_km = round(_haversine_km(smoothed[0]["lat"], smoothed[0]["lng"], smoothed[-1]["lat"], smoothed[-1]["lng"]), 1)
    direction = _bearing_label(smoothed[0]["lat"], smoothed[0]["lng"], smoothed[-1]["lat"], smoothed[-1]["lng"])

    confidence = "low" if len(years) < 5 else "medium"
    conclusion = conclusions.conclude(
        f"{common} ({sci}) occurrence centroid drifted about {drift_km} km {direction} across {len(years)} years "
        f"of OBIS/GBIF records ({years[0]}-{years[-1]}), and the recent velocity vector projects it continuing "
        f"{direction} over the next {FORECAST_YEARS} years.",
        confidence,
    )

    correction_note = ""
    if corrected_count:
        correction_note += f" {corrected_count} record(s) with a near-coast inland coordinate were snapped to the nearest water pixel."
    if dropped_count:
        correction_note += f" {dropped_count} record(s) too far inland to plausibly be a precision error were excluded."

    return {
        "species_id": query_species_id.lower(),
        "scientific_name": sci,
        "common_name": common,
        "historical": historical,
        "smoothed": smoothed,
        "forecast": forecast,
        "route_historical": route_historical,
        "route_forecast": route_forecast,
        "drift_km": drift_km,
        "direction": direction,
        "conclusion": conclusion,
        "confidence": confidence,
        "methodology": (
            f"Per-year mean lat/lng centroid of real OBIS/GBIF occurrence records, smoothed with exponential "
            f"smoothing (alpha={SMOOTHING_ALPHA}) to reduce year-to-year sampling noise, then extrapolated "
            f"{FORECAST_YEARS} years forward using the velocity between the last two smoothed points. Binned by "
            "year, not month — the source records only carry year-level dates. route_historical/route_forecast "
            "bend around land wherever a straight line between two sparse yearly centroids would otherwise cut "
            "across it, rather than drawing the direct line."
            f"{correction_note}"
        ),
        "source": "OBIS/GBIF real occurrence records",
        "land_coordinates_corrected": corrected_count,
        "land_coordinates_dropped": dropped_count,
    }
