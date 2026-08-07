"""Loads seed JSON once at import time. No hosted DB for this prototype."""

import json
from pathlib import Path
from functools import lru_cache

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def _load(name: str):
    with open(DATA_DIR / name) as f:
        return json.load(f)


def stations() -> list[dict]:
    return _load("stations.json")


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
