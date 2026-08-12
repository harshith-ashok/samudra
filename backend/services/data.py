"""Loads seed JSON once at import time. No hosted DB for this prototype."""

import json
from pathlib import Path
from functools import lru_cache

from services import ocean_cache

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def _load(name: str):
    with open(DATA_DIR / name) as f:
        return json.load(f)


def stations() -> list[dict]:
    """Real Copernicus SST/chlorophyll merged onto each station's simulated
    record (services/ocean_cache.py), falling back per-station to the
    untouched simulated history/latest whenever the cache doesn't cover that
    station or has gone stale. Returns new dicts each call rather than
    mutating the lru_cache'd seed data, so a cache that goes stale between
    requests degrades gracefully instead of sticking with whatever was merged
    in on the first call."""
    return [
        {
            **s,
            "history": ocean_cache.merged_history(s),
            "latest": ocean_cache.merged_latest(s),
            "source": ocean_cache.source_label(s),
        }
        for s in _load("stations.json")
    ]


def station_by_id(station_id: str) -> dict | None:
    return next((s for s in stations() if s["id"] == station_id), None)


def species() -> list[dict]:
    return _load("species.json")


def species_media() -> dict:
    return _load("species_media.json")


def advisories() -> list[dict]:
    return _load("advisories.json")


def catch_records() -> list[dict]:
    return _load("catch_records.json")


def biodiversity() -> dict:
    return _load("biodiversity.json")


def range_shift_series() -> dict:
    return _load("range_shift_series.json")


def text_chunks() -> list[dict]:
    return _load("text_chunks.json")


def glossary() -> list[dict]:
    return _load("glossary.json")


def mpa_zones() -> list[dict]:
    return _load("mpa_zones.json")


def pollution() -> list[dict]:
    return _load("pollution.json")
