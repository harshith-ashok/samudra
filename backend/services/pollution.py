"""Coastal pollution / treatment plant compliance (Phase 12).

Real-data path: CPCB publishes sewage/effluent treatment plant compliance data
on data.gov.in, but the resource API requires a free API key (api.data.gov.in)
we don't have in this build window. fetch_from_data_gov_in() is the wire-in
point for that later — same pattern as services/vessels.py's GFW stub.

Fallback path (what runs today): a small hand-built set of real coastal cities
with simulated discharge/compliance figures, clearly labeled as such.
"""

import os

from services import data

DATA_GOV_IN_API_KEY = os.environ.get("DATA_GOV_IN_API_KEY")


def fetch_from_data_gov_in() -> list[dict] | None:
    """Real CPCB integration point — unimplemented without an API key."""
    if not DATA_GOV_IN_API_KEY:
        return None
    raise NotImplementedError("DATA_GOV_IN_API_KEY is set, but the real CPCB fetch isn't wired up yet")


def list_plants() -> dict:
    real = fetch_from_data_gov_in()
    plants = real if real is not None else data.pollution()
    return {
        "plants": plants,
        "non_compliant_count": sum(1 for p in plants if p["compliance"] == "non-compliant"),
        "source": "CPCB (live, data.gov.in)" if real is not None else "simulated compliance figures for real coastal cities (no DATA_GOV_IN_API_KEY set)",
    }
