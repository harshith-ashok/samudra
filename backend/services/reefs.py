"""Multi-factor coral bleaching model (Phase 16 — replaces the single-gauge
view with a documented, weighted composite so the score isn't a black box).

Three inputs, each already used elsewhere in the app or clearly labeled where
it's illustrative:
  1. DHW (0.60 weight) — the same NOAA-style Degree Heating Weeks calculation
     as services/predict.py, but returned as a full weekly series instead of
     one final number, so the frontend can chart the buildup.
  2. Chlorophyll trend (0.25) — direction/magnitude of chlorophyll-a drift
     over the same window, from real recorded sensor history.
  3. Historical bleaching frequency (0.15) — no per-reef bleaching event log
     is available for this build, so this is an illustrative estimate keyed
     to well-documented global mass-bleaching years (2010, 2016, 2020) and
     clearly labeled as such, not a claim of measured local data.
"""

import numpy as np

from services import conclusions, data

WEIGHTS = {"dhw": 0.60, "chlorophyll_trend": 0.25, "historical_frequency": 0.15}

# Illustrative only — see module docstring. Keyed by known global mass-bleaching
# years; not a per-reef measured event log.
HISTORICAL_BLEACHING_EVENTS = {
    "lakshadweep": [2010, 2016, 2020],
    "kadmat": [2016, 2020],
    "kutch": [2016],
}
MAX_EVENTS_IN_WINDOW = 3  # normalizes the frequency factor to 0-1


def _weekly_dhw_series(sst_series: list[float]) -> tuple[list[dict], float, float]:
    baseline = float(np.mean(sst_series[:14]))
    threshold = baseline + 1.0
    n_weeks = len(sst_series) // 7
    cumulative = 0.0
    weeks = []
    for i in range(n_weeks):
        week_vals = sst_series[i * 7 : (i + 1) * 7]
        week_mean = float(np.mean(week_vals))
        excess = max(0.0, week_mean - threshold)
        cumulative += excess
        weeks.append(
            {
                "week": i + 1,
                "mean_sst_c": round(week_mean, 2),
                "excess_c": round(excess, 2),
                "cumulative_dhw": round(cumulative, 2),
            }
        )
    return weeks, baseline, threshold


def _chlorophyll_trend_factor(chl_series: list[float]) -> tuple[float, float]:
    x = np.arange(len(chl_series), dtype=float)
    slope, _ = np.polyfit(x, chl_series, 1)
    total_change = float(slope) * len(chl_series)
    # A swing of +-0.4 mg/m3 across the window (roughly the seed data's spread)
    # maps to full stress; a sharp move either direction reads as reef stress.
    stress = min(1.0, abs(total_change) / 0.4)
    return round(total_change, 3), round(stress, 3)


def bleaching_trend(station_id: str) -> dict:
    st = data.station_by_id(station_id.lower())
    if not st:
        return {"error": f"no station found for id '{station_id}'"}
    if st["type"] != "coral":
        return {"error": f"'{station_id}' is not a coral reef site"}

    history = st["history"]
    sst_series = [h["sst"] for h in history]
    chl_series = [h["chlorophyll"] for h in history]
    if len(sst_series) < 14:
        return {"error": "not enough SST history for a bleaching trend"}

    weeks, baseline, threshold = _weekly_dhw_series(sst_series)
    final_dhw = weeks[-1]["cumulative_dhw"] if weeks else 0.0
    dhw_norm = min(1.0, final_dhw / 8)

    chl_total_change, chl_stress = _chlorophyll_trend_factor(chl_series)

    events = HISTORICAL_BLEACHING_EVENTS.get(st["id"], [])
    freq_norm = min(1.0, len(events) / MAX_EVENTS_IN_WINDOW)

    composite = round(
        100 * (WEIGHTS["dhw"] * dhw_norm + WEIGHTS["chlorophyll_trend"] * chl_stress + WEIGHTS["historical_frequency"] * freq_norm),
        1,
    )

    if composite >= 65:
        alert = "Alert Level 2 — significant bleaching and mortality risk"
    elif composite >= 40:
        alert = "Alert Level 1 — significant bleaching risk likely"
    elif composite >= 15:
        alert = "Bleaching Watch — thermal stress accumulating"
    else:
        alert = "No Stress"

    factors = [
        {
            "factor": "dhw",
            "label": "Heat stress buildup (DHW)",
            "weight": WEIGHTS["dhw"],
            "raw_value": final_dhw,
            "normalized": round(dhw_norm, 3),
            "contribution_pct": round(100 * WEIGHTS["dhw"] * dhw_norm, 1),
        },
        {
            "factor": "chlorophyll_trend",
            "label": "Chlorophyll-a drift",
            "weight": WEIGHTS["chlorophyll_trend"],
            "raw_value": chl_total_change,
            "normalized": round(chl_stress, 3),
            "contribution_pct": round(100 * WEIGHTS["chlorophyll_trend"] * chl_stress, 1),
        },
        {
            "factor": "historical_frequency",
            "label": "Historical bleaching frequency (illustrative)",
            "weight": WEIGHTS["historical_frequency"],
            "raw_value": len(events),
            "normalized": round(freq_norm, 3),
            "contribution_pct": round(100 * WEIGHTS["historical_frequency"] * freq_norm, 1),
        },
    ]

    confidence = "medium" if len(weeks) < 8 else "high"
    conclusion = conclusions.conclude(
        f"{st['name']} composite bleaching score is {composite}/100 ({alert}). Breakdown: "
        f"DHW {final_dhw} contributes {factors[0]['contribution_pct']} pts, chlorophyll drift of "
        f"{chl_total_change} mg/m3 contributes {factors[1]['contribution_pct']} pts, historical bleaching "
        f"frequency ({len(events)} known events) contributes {factors[2]['contribution_pct']} pts.",
        confidence,
    )

    return {
        "station_id": st["id"],
        "station_name": st["name"],
        "weekly_series": weeks,
        "baseline_sst_c": round(baseline, 2),
        "threshold_sst_c": round(threshold, 2),
        "composite_score": composite,
        "alert_level": alert,
        "factors": factors,
        "conclusion": conclusion,
        "confidence": confidence,
        "methodology": (
            "Composite = 60% Degree Heating Weeks (NOAA Coral Reef Watch-style, trailing weeks of recorded SST) "
            "+ 25% chlorophyll-a drift over the same window + 15% historical bleaching frequency. The frequency "
            "factor is illustrative (keyed to known global mass-bleaching years 2010/2016/2020, not a measured "
            "per-reef event log) — every other input is computed from real recorded sensor history."
        ),
        "source": st["source"],
    }
