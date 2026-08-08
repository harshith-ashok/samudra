"""Rough map areas for region names that show up in structured tool results
(Phase 24) — lets the AI Assistant temporarily highlight the actual place a
response is talking about.

Deliberately grounded in which regions the *tool calls* touched during a chat
turn (see services/rag.py), not by parsing the model's free-text answer for
place names — that would risk highlighting somewhere the model just mentioned
in passing, or hallucinated. Tool results are real structured data, so
whatever regions appear there are exactly what the answer is grounded in.
This also naturally limits the feature to "a specific set of questions that
involves a region" (advisories, catch trend, species info, pollution, vessel
violations) rather than firing on every chat answer — a question that never
triggers a region-tagged tool just returns no regions.

Two tiers, in priority order:
  1. MPA zones already have real hand-traced polygons (data/mpa_zones.json)
     — reused directly, more accurate than a circle.
  2. Every other named coastal region gets a hand-picked circle. Centers/
     radii below are eyeballed from this build's own station clusters (see
     data/stations.json) — approximate, not survey-grade administrative
     boundaries, which is why resolve() marks them "approximate": true.
"""

from services import data

# name -> (lat, lng, radius_km). Covers every region string that actually
# appears in advisories.json / catch_records.json / species.json /
# pollution.json (checked against the seed data, not guessed blind).
REGION_CIRCLES: dict[str, tuple[float, float, float]] = {
    "Kerala coast": (9.4, 76.4, 120),
    "Tamil Nadu coast": (11.3, 79.8, 180),
    "Goa coast": (15.49, 73.83, 60),
    "Arabian Sea": (14.0, 71.0, 350),
    "Lakshadweep": (10.9, 72.5, 100),
    "Odisha coast": (20.3, 86.6, 100),
    "Andaman Islands": (11.8, 92.85, 80),
    "Andhra Pradesh coast": (17.69, 83.22, 100),
    "Gujarat coast": (21.2, 69.9, 150),
    "Karnataka coast": (12.91, 74.86, 80),
    "Mumbai coast": (19.08, 72.88, 60),
    "Puducherry coast": (11.91, 79.81, 50),
    "Sundarbans": (21.63, 88.5, 80),
    "West Bengal coast": (21.8, 88.2, 100),
}


def _mpa_zone_for(name: str) -> dict | None:
    for zone in data.mpa_zones():
        if zone["name"] == name or zone["region"] == name:
            return zone
    return None


def resolve(region_name: str) -> dict | None:
    """A drawable area for a region name, or None if this build doesn't know
    that name. Polygon areas come from real MPA boundaries; circle areas are
    illustrative — both cases are labeled via "approximate" so the frontend
    can be honest about which is which if it wants to."""
    zone = _mpa_zone_for(region_name)
    if zone:
        return {
            "name": zone["name"],
            "kind": "polygon",
            "polygon": zone["polygon"],
            "approximate": False,
        }
    circle = REGION_CIRCLES.get(region_name)
    if circle:
        lat, lng, radius_km = circle
        return {
            "name": region_name,
            "kind": "circle",
            "lat": lat,
            "lng": lng,
            "radius_km": radius_km,
            "approximate": True,
        }
    return None


def resolve_many(region_names: set[str]) -> list[dict]:
    resolved = []
    seen = set()
    for name in region_names:
        area = resolve(name)
        if area and area["name"] not in seen:
            resolved.append(area)
            seen.add(area["name"])
    return resolved


def extract_region_names(tool_result: dict) -> set[str]:
    """Pulls every region-like string out of a tool result: a top-level
    "region" field, or a "region"/"violation_zone" field on any list item —
    covers every shape services/tools.py's functions actually return,
    generically, rather than hardcoding per-tool-name logic that would need
    updating each time a tool's response shape changes."""
    found: set[str] = set()
    if not isinstance(tool_result, dict):
        return found
    if isinstance(tool_result.get("region"), str):
        found.add(tool_result["region"])
    for value in tool_result.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("region"), str):
                found.add(item["region"])
            if isinstance(item.get("violation_zone"), str):
                found.add(item["violation_zone"])
    return found
