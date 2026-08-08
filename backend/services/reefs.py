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

from services import conclusions, confidence, data

WEIGHTS = {"dhw": 0.60, "chlorophyll_trend": 0.25, "historical_frequency": 0.15}

# (threshold, label) pairs matching the alert_level bands above, ascending.
ALERT_THRESHOLDS = [
    (15.0, "Bleaching Watch"),
    (40.0, "Alert Level 1"),
    (65.0, "Alert Level 2"),
]
COUNTDOWN_TREND_WEEKS = 4  # how many recent weeks set the "current trend" rate

# Illustrative only — see module docstring. Keyed by known global mass-bleaching
# years; not a per-reef measured event log.
HISTORICAL_BLEACHING_EVENTS = {
    "lakshadweep": [2010, 2016, 2020],
    "kadmat": [2016, 2020],
    "kutch": [2016],
}
MAX_EVENTS_IN_WINDOW = 3  # normalizes the frequency factor to 0-1


def _weekly_dhw_series(sst_series: list[float], baseline_series: list[float] | None = None) -> tuple[list[dict], float, float]:
    """baseline_series lets a what-if SST delta shift the *readings* being
    compared against a fixed historical baseline, without also shifting the
    baseline itself — computing the baseline from the same already-shifted
    series would cancel the delta out entirely (a uniform +N°C offset to both
    the readings and the baseline they're compared against changes nothing).
    Defaults to sst_series so the no-scenario case is unaffected."""
    baseline = float(np.mean((baseline_series or sst_series)[:14]))
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


def _chlorophyll_trend_factor(chl_series: list[float], extra_drift: float = 0.0) -> tuple[float, float]:
    """extra_drift is a what-if scenario override — added as a linear ramp
    (0 at the first day, extra_drift at the last) rather than a uniform shift.
    This measures a *trend*, and a constant offset added to every point in a
    linear regression leaves the fitted slope completely unchanged — a uniform
    shift would silently be a no-op here, the same way it would cancel out for
    DHW's baseline-relative threshold if applied the same way (see
    _weekly_dhw_series). A ramp actually changes the slope, which is what a
    "chlorophyll delta scenario" needs to mean anything."""
    n = len(chl_series)
    if extra_drift and n > 1:
        chl_series = [v + extra_drift * (i / (n - 1)) for i, v in enumerate(chl_series)]
    x = np.arange(n, dtype=float)
    slope, _ = np.polyfit(x, chl_series, 1)
    total_change = float(slope) * n
    # A swing of +-0.4 mg/m3 across the window (roughly the seed data's spread)
    # maps to full stress; a sharp move either direction reads as reef stress.
    stress = min(1.0, abs(total_change) / 0.4)
    return round(total_change, 3), round(stress, 3)


def _time_to_next_alert(composite: float, weeks: list[dict], chl_stress: float, freq_norm: float) -> dict:
    """Extrapolates the recent DHW accumulation rate forward to estimate days
    until the composite score crosses into the next alert tier, holding the
    chlorophyll and historical-frequency factors constant (they don't grow
    week-over-week the way DHW does — they're a fixed read of the current
    window, not something that trends). Reuses Phase 16's weekly_series, no
    new data source."""
    next_threshold_label = next(((t, label) for t, label in ALERT_THRESHOLDS if t > composite), None)
    if next_threshold_label is None:
        return {"status": "at_max", "message": "Already at the highest alert tier (Alert Level 2) — no next threshold to project."}
    next_threshold, next_label = next_threshold_label

    recent = weeks[-COUNTDOWN_TREND_WEEKS:] if len(weeks) >= COUNTDOWN_TREND_WEEKS else weeks
    weekly_dhw_rate = float(np.mean([w["excess_c"] for w in recent])) if recent else 0.0
    if weekly_dhw_rate <= 0:
        return {"status": "not_trending", "message": "Heat stress isn't currently accumulating — no crossing projected at this trend."}

    fixed_contribution_pts = 100 * (WEIGHTS["chlorophyll_trend"] * chl_stress + WEIGHTS["historical_frequency"] * freq_norm)
    needed_dhw_norm = (next_threshold - fixed_contribution_pts) / (100 * WEIGHTS["dhw"])
    if needed_dhw_norm > 1.0:
        return {
            "status": "unreachable",
            "message": f"{next_label} isn't reachable from heat-stress buildup alone at the current chlorophyll/frequency contribution — those would need to shift too.",
        }

    current_dhw = weeks[-1]["cumulative_dhw"] if weeks else 0.0
    needed_dhw = needed_dhw_norm * 8  # dhw_norm = min(1, dhw/8) in bleaching_trend
    dhw_gap = max(0.0, needed_dhw - current_dhw)
    days = round((dhw_gap / weekly_dhw_rate) * 7, 1)

    return {
        "status": "projected",
        "next_alert_label": next_label,
        "days": days,
        "weekly_dhw_rate": round(weekly_dhw_rate, 3),
        "message": f"{next_label} in ~{round(days)} day{'s' if round(days) != 1 else ''} at the current heat-stress trend.",
    }


def bleaching_trend(station_id: str, sst_delta: float = 0.0, chlorophyll_delta: float = 0.0) -> dict:
    """sst_delta and chlorophyll_delta are what-if scenario overrides (Phase 21) —
    both default to 0.0 (no-op) so an un-scenario'd call returns exactly the real
    trend. Applied as a uniform shift across the recorded window (i.e. "what if
    conditions were consistently N warmer/greener over this period"), not a
    forecast of how they'd actually evolve."""
    st = data.station_by_id(station_id.lower())
    if not st:
        return {"error": f"no station found for id '{station_id}'"}
    if st["type"] != "coral":
        return {"error": f"'{station_id}' is not a coral reef site"}

    history = st["history"]
    sst_series_actual = [h["sst"] for h in history]
    sst_series = [s + sst_delta for s in sst_series_actual]
    chl_series = [h["chlorophyll"] for h in history]
    if len(sst_series) < 14:
        return {"error": "not enough SST history for a bleaching trend"}

    # baseline_series stays unshifted — see _weekly_dhw_series docstring for why
    # shifting both the readings and the baseline they're compared against would
    # cancel the scenario out entirely.
    weeks, baseline, threshold = _weekly_dhw_series(sst_series, baseline_series=sst_series_actual)
    final_dhw = weeks[-1]["cumulative_dhw"] if weeks else 0.0
    dhw_norm = min(1.0, final_dhw / 8)

    chl_total_change, chl_stress = _chlorophyll_trend_factor(chl_series, extra_drift=chlorophyll_delta)

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

    confidence_label = "medium" if len(weeks) < 8 else "high"
    confidence_pct = confidence.pct_from_count(len(weeks), full_at=8)
    threshold_countdown = _time_to_next_alert(composite, weeks, chl_stress, freq_norm)
    scenario_active = bool(sst_delta) or bool(chlorophyll_delta)
    scenario_note = (
        f" Simulated what-if scenario applied: SST {sst_delta:+.1f}°C, chlorophyll {chlorophyll_delta:+.2f} mg/m3 "
        "shifted uniformly across the window — this is a hypothetical, not the live reading."
        if scenario_active
        else ""
    )
    conclusion = conclusions.conclude(
        f"{st['name']} composite bleaching score is {composite}/100 ({alert}). Breakdown: "
        f"DHW {final_dhw} contributes {factors[0]['contribution_pct']} pts, chlorophyll drift of "
        f"{chl_total_change} mg/m3 contributes {factors[1]['contribution_pct']} pts, historical bleaching "
        f"frequency ({len(events)} known events) contributes {factors[2]['contribution_pct']} pts.{scenario_note}",
        confidence_label,
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
        "confidence": confidence_label,
        "confidence_pct": confidence_pct,
        "threshold_countdown": threshold_countdown,
        "methodology": (
            "Composite = 60% Degree Heating Weeks (NOAA Coral Reef Watch-style, trailing weeks of recorded SST) "
            "+ 25% chlorophyll-a drift over the same window + 15% historical bleaching frequency. The frequency "
            "factor is illustrative (keyed to known global mass-bleaching years 2010/2016/2020, not a measured "
            "per-reef event log) — every other input is computed from real recorded sensor history."
        ),
        "source": st["source"],
        "scenario": {
            "active": scenario_active,
            "sst_delta_c": sst_delta,
            "chlorophyll_delta_mgm3": chlorophyll_delta,
        },
    }
