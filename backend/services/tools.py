"""Structured tools the model can call for deterministic, no-hallucination numbers.

These hit the seed JSON "database" directly (see services/data.py) rather than
going through the vector store — the unstructured/vector path lives in
services/rag.py. Both feed into the same gpt-oss call in services/chat.py.
"""

from services import data, pollution, vessels

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_catch_trend",
            "description": "Get monthly fisheries catch tonnage for a species in a region, most recent months first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "species": {"type": "string", "description": "Scientific name, e.g. 'Sardinella longiceps'"},
                    "region": {"type": "string", "description": "Region name, e.g. 'Kerala coast'"},
                },
                "required": ["species", "region"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sensor_readings",
            "description": "Get the latest ocean sensor readings (SST, salinity, chlorophyll) and recent history for a station.",
            "parameters": {
                "type": "object",
                "properties": {
                    "station_id": {"type": "string", "description": "Station id, e.g. 'kochi', 'lakshadweep'"},
                },
                "required": ["station_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_advisories",
            "description": "Get active fishing/conservation advisories, optionally filtered by region.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "Optional region filter, e.g. 'Lakshadweep atolls'"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_species_info",
            "description": "Get conservation status and region for a species by scientific or common name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Scientific or common name, e.g. 'Dugong dugon'"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vessel_status",
            "description": "Get current vessel positions and which ones are right now inside a marine protected area (MPA) — the live illegal-fishing/violation check.",
            "parameters": {
                "type": "object",
                "properties": {
                    "violations_only": {
                        "type": "boolean",
                        "description": "If true, return only vessels currently inside a protected zone. Default false (return the whole fleet).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pollution_status",
            "description": "Get coastal sewage/effluent treatment plant locations and CPCB-style compliance status, optionally filtered by city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Optional city filter, e.g. 'Chennai'"},
                },
                "required": [],
            },
        },
    },
]


def get_catch_trend(species: str, region: str | None = None) -> dict:
    records = [
        r for r in data.catch_records()
        if species.lower() in r["species"].lower()
        and (region is None or region.lower() in r["region"].lower())
    ]
    records.sort(key=lambda r: r["date"], reverse=True)
    return {"species": species, "region": region, "records": records, "source": "simulated (CMFRI-shaped) — see catch_records.json"}


def get_sensor_readings(station_id: str) -> dict:
    st = data.station_by_id(station_id.lower())
    if not st:
        return {"error": f"no station found for id '{station_id}'"}
    return {
        "id": st["id"],
        "name": st["name"],
        "type": st["type"],
        "latest": st["latest"],
        "recent_history": st["history"][-7:],
        "source": st["source"],
    }


def get_active_advisories(region: str | None = None) -> dict:
    advisories = [a for a in data.advisories() if a["status"] == "active"]
    if region:
        advisories = [a for a in advisories if region.lower() in a["region"].lower()]
    return {"advisories": advisories}


def get_species_info(name: str) -> dict:
    name_lower = name.lower()
    for s in data.species():
        if name_lower in s["sci"].lower() or name_lower in s["common"].lower():
            return s
    return {"error": f"no species found matching '{name}'"}


def get_vessel_status(violations_only: bool = False) -> dict:
    result = vessels.list_vessels()
    fleet = result["vessels"]
    if violations_only:
        fleet = [v for v in fleet if v["in_violation"]]
    return {
        "vessels": [
            {
                "id": v["id"],
                "name": v["name"],
                "type": v["type"],
                "in_violation": v["in_violation"],
                "violation_zone": v["violation_zone"],
            }
            for v in fleet
        ],
        "violation_count": result["violation_count"],
        "source": result["source"],
    }


def get_pollution_status(city: str | None = None) -> dict:
    result = pollution.list_plants()
    plants = result["plants"]
    if city:
        plants = [p for p in plants if city.lower() in p["city"].lower()]
    return {
        "plants": plants,
        "non_compliant_count": sum(1 for p in plants if p["compliance"] == "non-compliant"),
        "source": result["source"],
    }


DISPATCH = {
    "get_catch_trend": get_catch_trend,
    "get_sensor_readings": get_sensor_readings,
    "get_active_advisories": get_active_advisories,
    "get_species_info": get_species_info,
    "get_vessel_status": get_vessel_status,
    "get_pollution_status": get_pollution_status,
}


def run_tool(name: str, arguments: dict) -> dict:
    func = DISPATCH.get(name)
    if not func:
        return {"error": f"unknown tool '{name}'"}
    try:
        return func(**arguments)
    except TypeError as e:
        return {"error": str(e)}
