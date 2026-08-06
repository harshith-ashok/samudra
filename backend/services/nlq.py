"""Natural-language query: gpt-oss translates free text into a structured filter,
which we then run directly against the seed data — no hallucinated results, the
model only decides *what to look up*, not the answer itself.
"""

import json

from services import data, llm

TRANSLATE_PROMPT = """Translate the user's ocean/fisheries/biodiversity query into a JSON filter. \
Respond with ONLY a JSON object, no prose, matching this shape exactly:

{
  "region": string or null,       // e.g. "Kerala", "Lakshadweep", "Goa", "Tamil Nadu", "Odisha", "Mannar" — a short place name/substring, not a full sentence
  "species": string or null,      // scientific or common name substring, e.g. "sardine", "Dugong"
  "conservation_status": string or null,  // one of "LC", "NT", "VU", "EN" if the query mentions vulnerability/threatened/endangered status
  "parameter": string or null,    // one of "sst", "salinity", "chlorophyll", "tonnage" if the query is about a sensor/catch measurement
  "advisories_only": boolean,     // true if the query is specifically about advisories
  "eDNA_only": boolean            // true if the query is specifically about eDNA detections
}

Use null/false for anything not mentioned. Do not add extra keys."""


def translate(query: str) -> dict:
    response = llm.chat(
        [
            {"role": "system", "content": TRANSLATE_PROMPT},
            {"role": "user", "content": query},
        ]
    )
    content = response.message.content or "{}"
    try:
        start, end = content.index("{"), content.rindex("}") + 1
        return json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}


def _trace(filt: dict) -> str:
    clauses = []
    if filt.get("region"):
        clauses.append(f"region ILIKE '%{filt['region']}%'")
    if filt.get("species"):
        clauses.append(f"species ILIKE '%{filt['species']}%'")
    if filt.get("conservation_status"):
        clauses.append(f"conservation_status = '{filt['conservation_status']}'")
    if filt.get("parameter"):
        clauses.append(f"parameter = '{filt['parameter']}'")
    if filt.get("advisories_only"):
        clauses.append("status = 'active'")
    if filt.get("eDNA_only"):
        clauses.append("method = 'eDNA'")
    where = " AND ".join(clauses) if clauses else "1=1"
    return f"SELECT * FROM unified_records WHERE {where}"


def _matches(text: str | None, needle: str | None) -> bool:
    if not needle:
        return True
    if not text:
        return False
    return needle.lower() in text.lower()


def search(filt: dict) -> list[dict]:
    results: list[dict] = []
    region = filt.get("region")
    species_q = filt.get("species")
    status = filt.get("conservation_status")

    if not filt.get("advisories_only") and not filt.get("eDNA_only"):
        for s in data.species():
            if _matches(s["region"], region) and _matches(s["sci"] + " " + s["common"], species_q) and (
                not status or s.get("status") == status
            ):
                results.append({"record_type": "species", **s})

        for st in data.stations():
            if _matches(st["name"], region) or _matches(st["type"], region):
                results.append(
                    {
                        "record_type": "station",
                        "id": st["id"],
                        "name": st["name"],
                        "type": st["type"],
                        "lat": st["lat"],
                        "lng": st["lng"],
                        "latest": st["latest"],
                    }
                )

    if filt.get("advisories_only") or (not species_q and not filt.get("eDNA_only")):
        for a in data.advisories():
            if _matches(a["region"], region) and _matches(a["species"], species_q):
                if not filt.get("advisories_only") or a["status"] == "active":
                    results.append({"record_type": "advisory", **a})

    if filt.get("eDNA_only"):
        for d in data.biodiversity()["edna_detections"]:
            if _matches(d["region"], region):
                results.append({"record_type": "edna_detection", **d})

    return results


def run(query: str) -> dict:
    filt = translate(query)
    return {"query": query, "filter": filt, "trace": _trace(filt), "results": search(filt)}
