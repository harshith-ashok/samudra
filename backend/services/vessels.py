"""Vessel tracking (Phase 8).

Real-data path: Global Fishing Watch's API needs a free API key we don't have in
this build window (GFW_API_KEY env var). If one is ever set, fetch_from_gfw()
is the place to wire in a real call — everything downstream (point-in-polygon
check, /api/vessels response shape) is written against the same vessel record
shape either way, so switching data sources later doesn't touch the router.

Fallback path (default, and what actually runs today): a small fleet of
simulated AIS-like vessels, each moving along a fixed track. Position is
computed live from wall-clock time so vessels visibly drift on repeated polls
without needing any persisted server state — no live sensor ingestion, a
periodic refresh of mocked data is fine for this build.
"""

import math
import os
import time

from services import data

GFW_API_KEY = os.environ.get("GFW_API_KEY")


def fetch_from_gfw(bbox: tuple[float, float, float, float]) -> list[dict] | None:
    """Real GFW integration point — unimplemented without an API key.

    Returns None (meaning "use simulated data") until GFW_API_KEY is set and
    this is filled in against https://gateway.api.globalfishingwatch.org.
    """
    if not GFW_API_KEY:
        return None
    raise NotImplementedError("GFW_API_KEY is set, but the real API call isn't wired up yet")


# Each vessel loops around a fixed closed track. A couple of "trawler" tracks
# deliberately clip through an MPA polygon so the violation flag has something
# real to demonstrate; the rest run legitimate coastal shipping lanes.
FLEET = [
    {
        "id": "IN-TRW-4471",
        "name": "Meenakshi Star",
        "type": "trawler",
        "period_s": 90,
        # Waypoint [9.18, 78.86] deliberately sits inside the real Gulf of
        # Mannar polygon (mpa-mannar-1) so the violation flag still has a
        # live demonstration now that MPA boundaries are real, disjoint reef
        # clusters rather than one hand-traced blob covering the whole strait.
        "track": [
            [9.0, 78.4],
            [9.18, 78.86],
            [9.05, 79.0],
            [8.85, 79.15],
            [8.9, 78.7],
            [9.0, 78.4],
        ],
    },
    {
        "id": "IN-TRW-2290",
        "name": "Rameswaram Fortune",
        "type": "trawler",
        "period_s": 110,
        "track": [
            [8.9, 78.3],
            [9.05, 78.5],
            [8.95, 78.9],
            [8.8, 78.7],
            [8.9, 78.3],
        ],
    },
    {
        "id": "IN-TRW-8834",
        "name": "Lakshadweep Tide",
        "type": "trawler",
        "period_s": 75,
        "track": [
            [10.5, 72.5],
            [10.6, 72.6],
            [10.5, 72.75],
            [10.4, 72.6],
            [10.5, 72.5],
        ],
    },
    {
        "id": "IN-CGO-1123",
        "name": "Konkan Carrier",
        "type": "cargo",
        "period_s": 160,
        "track": [
            [19.0, 72.7],
            [17.5, 73.0],
            [15.4, 73.6],
            [13.0, 80.1],
        ],
    },
    {
        "id": "IN-CGO-5567",
        "name": "Coromandel Express",
        "type": "cargo",
        "period_s": 150,
        "track": [
            [13.08, 80.3],
            [15.5, 80.5],
            [17.7, 83.3],
            [21.9, 88.9],
        ],
    },
    {
        "id": "IN-TNK-3312",
        "name": "Arabian Voyager",
        "type": "tanker",
        "period_s": 200,
        "track": [
            [19.1, 72.8],
            [16.0, 73.2],
            [11.6, 75.5],
            [9.9, 76.3],
        ],
    },
    {
        "id": "IN-FSH-9081",
        "name": "Goa Kadal",
        "type": "fishing",
        "period_s": 70,
        "track": [
            [15.4, 73.7],
            [15.55, 73.85],
            [15.45, 74.0],
            [15.3, 73.85],
            [15.4, 73.7],
        ],
    },
    {
        "id": "IN-FSH-6620",
        "name": "Vizag Voyager",
        "type": "fishing",
        "period_s": 85,
        "track": [
            [17.6, 83.1],
            [17.75, 83.25],
            [17.6, 83.4],
            [17.45, 83.25],
            [17.6, 83.1],
        ],
    },
    {
        "id": "IN-FSH-1145",
        "name": "Port Blair Runner",
        "type": "fishing",
        "period_s": 95,
        "track": [
            [11.6, 92.6],
            [11.75, 92.75],
            [11.6, 92.9],
            [11.45, 92.75],
            [11.6, 92.6],
        ],
    },
]


def point_in_polygon(lat: float, lng: float, polygon: list[list[float]]) -> bool:
    """Standard ray-casting point-in-polygon test. polygon is [[lat, lng], ...]."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        lat_i, lng_i = polygon[i]
        lat_j, lng_j = polygon[j]
        intersects = ((lng_i > lng) != (lng_j > lng)) and (
            lat < (lat_j - lat_i) * (lng - lng_i) / (lng_j - lng_i + 1e-12) + lat_i
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _bearing(a: list[float], b: list[float]) -> float:
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    d_lng = lng2 - lng1
    x = math.sin(d_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def position_on_track(track: list[list[float]], t: float) -> tuple[float, float, float]:
    """t in [0, 1) fraction of the way around the closed loop `track`."""
    n = len(track)
    seg_float = t * n
    i = int(seg_float) % n
    local_t = seg_float - int(seg_float)
    a, b = track[i], track[(i + 1) % n]
    lat = a[0] + (b[0] - a[0]) * local_t
    lng = a[1] + (b[1] - a[1]) * local_t
    heading = _bearing(a, b)
    return lat, lng, heading


def _mpa_zones() -> list[dict]:
    return data.mpa_zones()


def _simulated_fleet() -> list[dict]:
    now = time.time()
    zones = _mpa_zones()
    vessels = []
    for v in FLEET:
        t = (now % v["period_s"]) / v["period_s"]
        lat, lng, heading = position_on_track(v["track"], t)
        violated_zone = next((z for z in zones if point_in_polygon(lat, lng, z["polygon"])), None)
        vessels.append(
            {
                "id": v["id"],
                "name": v["name"],
                "type": v["type"],
                "lat": round(lat, 4),
                "lng": round(lng, 4),
                "heading_deg": round(heading, 1),
                "speed_knots": round(4 + 3 * math.sin(now / 17 + hash(v["id"]) % 10), 1),
                "track": v["track"],
                "in_violation": violated_zone is not None,
                # Real MPA boundaries can be split across several disjoint
                # polygon entries sharing one region (see data/mpa_zones.json)
                # — report the region, not the per-fragment "(part N/M)" name.
                "violation_zone": violated_zone["region"] if violated_zone else None,
            }
        )
    return vessels


def list_vessels(bbox: tuple[float, float, float, float] | None = None) -> dict:
    real = fetch_from_gfw(bbox) if bbox else fetch_from_gfw((5, 66, 24, 94))
    vessels = real if real is not None else _simulated_fleet()
    return {
        "vessels": vessels,
        "mpa_zones": _mpa_zones(),
        "violation_count": sum(1 for v in vessels if v["in_violation"]),
        "source": "Global Fishing Watch (live)" if real is not None else "simulated AIS-like tracks (no GFW_API_KEY set)",
    }
