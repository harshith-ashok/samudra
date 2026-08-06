"""Per-station timeline for the frontend's scrubbable map (Phase 9).

Blends real recorded sensor history with a short linear-trend forecast tail,
reusing the same trend-extrapolation approach as services/predict.py. Every
point is tagged "recorded" or "forecast" so the frontend never presents a
projection as measured fact.
"""

import numpy as np

from services import data

METRICS = ("sst", "salinity", "chlorophyll")
FORECAST_RATIO = 0.3  # fraction of the requested window that projects into the future


def _metric_field(metric: str) -> str:
    return {"sst": "sst", "salinity": "salinity", "chlorophyll": "chlorophyll"}[metric]


def station_timeline(station: dict, metric: str, days: int) -> list[dict]:
    field = _metric_field(metric)
    forecast_days = max(1, round(days * FORECAST_RATIO))
    recorded_days = max(2, days - forecast_days)

    history = station["history"][-recorded_days:]
    recorded_values = [h[field] for h in history]

    x = np.arange(len(recorded_values), dtype=float)
    slope, intercept = np.polyfit(x, recorded_values, 1)
    future_x = np.arange(len(recorded_values), len(recorded_values) + forecast_days, dtype=float)
    forecast_values = slope * future_x + intercept

    entries = [{"day": h["day"], "value": round(h[field], 2), "kind": "recorded"} for h in history]
    entries += [
        {"day": i + 1, "value": round(float(forecast_values[i]), 2), "kind": "forecast"}
        for i in range(forecast_days)
    ]
    return entries


def timeline(metric: str, days: int = 30) -> dict:
    if metric not in METRICS:
        return {"error": f"unknown metric '{metric}', expected one of {METRICS}"}
    days = max(4, min(days, 60))
    forecast_days = max(1, round(days * FORECAST_RATIO))
    recorded_days = max(2, days - forecast_days)
    stations = {st["id"]: station_timeline(st, metric, days) for st in data.stations()}
    return {
        "metric": metric,
        "days": days,
        "min_day": -(recorded_days - 1),
        "max_day": forecast_days,
        "forecast_from_day": 1,
        "stations": stations,
        "methodology": "Recorded days come directly from station sensor history; forecast days (day > 0) extrapolate a linear trend fit to the recorded window — the same trend-extrapolation approach used in /api/predict/stock.",
    }
