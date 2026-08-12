"""Three simple, honestly-documented prediction methods. None of this is a
formal stock assessment or climate model; each is a straightforward trend
extrapolation over the seed data, returned with its methodology so the
frontend/judges can see exactly what ran.
"""

import numpy as np

from services import conclusions, confidence, data, ocean_cache


def _common_name(species: str) -> str | None:
    return next((s["common"] for s in data.species() if s["sci"].lower() == species.lower()), None)


def stock_forecast(
    species: str,
    region: str,
    months_ahead: int = 6,
    sst_delta: float = 0.0,
    fishing_pressure: float = 1.0,
) -> dict:
    """sst_delta and fishing_pressure are what-if scenario overrides (Phase 21) —
    both default to a no-op (0.0 / 1.0) so an un-scenario'd call returns exactly
    the real forecast. Neither touches the historical fit, only the forward
    extrapolation, so the fitted trend/CI-width logic stays the real regression."""
    records = [
        r for r in data.catch_records()
        if species.lower() in r["species"].lower() and region.lower() in r["region"].lower()
    ]
    records.sort(key=lambda r: r["date"])
    if len(records) < 3:
        return {"error": f"not enough catch history for {species} in {region}"}

    y = np.array([r["tonnage"] for r in records], dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = slope * x + intercept
    residual_std = float(np.std(y - fitted)) or 1.0

    # Fishing pressure: a heuristic multiplier on the fitted rate of change, not a
    # stock-recruitment model — >1x steepens a decline (or dampens a rise), <1x the
    # opposite. Only applied to the forward projection, never the historical fit.
    scenario_slope = slope * fishing_pressure if slope <= 0 else slope / max(fishing_pressure, 1e-3)

    # SST sensitivity: regression of tonnage on this same series' SST values gives
    # a tonnes-per-degree coefficient, applied as a constant offset for the assumed
    # anomaly. Falls back to 0 if SST barely varies in the window. SST itself is
    # real (Copernicus Marine, via ocean_cache) for any record whose region/month
    # is covered, simulated seed sst_c otherwise — tonnage stays simulated either way.
    sst_effect_per_degree = 0.0
    real_sst_count = 0
    sst_list = []
    for r in records:
        real_sst, _ = ocean_cache.region_monthly_sst(r["region"], r["date"])
        sst_list.append(real_sst if real_sst is not None else r["sst_c"])
        real_sst_count += real_sst is not None
    sst_vals = np.array(sst_list, dtype=float)
    if sst_delta and float(np.std(sst_vals)) > 1e-6:
        sst_slope, _ = np.polyfit(sst_vals, y, 1)
        sst_effect_per_degree = float(sst_slope)

    future_x = np.arange(len(y), len(y) + months_ahead, dtype=float)
    forecast_mean = scenario_slope * future_x + intercept + sst_delta * sst_effect_per_degree
    # widening 80% CI band (z ~ 1.28) that grows with distance from the fit
    z = 1.28
    forecast_lo = forecast_mean - z * residual_std * (1 + 0.15 * np.arange(months_ahead))
    forecast_hi = forecast_mean + z * residual_std * (1 + 0.15 * np.arange(months_ahead))
    # tonnage can't go negative — an aggressive scenario (e.g. high fishing pressure
    # stacked with a warm anomaly) should floor out at zero catch, not report a
    # negative number
    forecast_mean = np.maximum(0.0, forecast_mean)
    forecast_lo = np.maximum(0.0, forecast_lo)
    forecast_hi = np.maximum(0.0, forecast_hi)

    direction = "rising" if slope > 0.5 else "falling" if slope < -0.5 else "roughly flat"
    confidence_label = "low" if len(records) < 6 else "medium" if len(records) < 12 else "high"
    confidence_pct = confidence.pct_from_count(len(records), full_at=12)
    common = _common_name(species)
    species_label = f"{species} ({common})" if common else species
    scenario_active = bool(sst_delta) or fishing_pressure != 1.0
    scenario_note = (
        f" Simulated what-if scenario applied: SST anomaly {sst_delta:+.1f}°C, fishing pressure ×{fishing_pressure:.2f} "
        "— this is a hypothetical, not the live forecast."
        if scenario_active
        else ""
    )
    conclusion = conclusions.conclude(
        f"Linear trend fit to {len(records)} months of catch data for {species_label} in {region}: "
        f"{direction} at {abs(round(float(slope), 1))} tonnes/month, projecting {round(float(forecast_mean[0]), 0)} "
        f"tonnes next month (80% CI {round(float(forecast_lo[0]), 0)}-{round(float(forecast_hi[0]), 0)})."
        f"{scenario_note}",
        confidence_label,
    )

    return {
        "species": species,
        "region": region,
        "history": [{"date": r["date"], "tonnage": r["tonnage"]} for r in records],
        "forecast": [
            {
                "month_offset": i + 1,
                "tonnage": round(float(forecast_mean[i]), 1),
                "low_80ci": round(float(forecast_lo[i]), 1),
                "high_80ci": round(float(forecast_hi[i]), 1),
            }
            for i in range(months_ahead)
        ],
        "trend_tonnage_per_month": round(float(slope), 2),
        "conclusion": conclusion,
        "confidence": confidence_label,
        "confidence_pct": confidence_pct,
        "methodology": "Linear regression (numpy polyfit, degree 1) of monthly catch tonnage vs. time; 80% CI band widens linearly with forecast horizon. Trend-extrapolation only, not a stock assessment.",
        "source": (
            f"catch tonnage: simulated (CMFRI-shaped). SST input: real Copernicus Marine SST "
            f"(OSTIA L4 NRT) for {real_sst_count}/{len(records)} months, simulated seed value otherwise — "
            "half-real, not a fully live forecast."
            if real_sst_count
            else "simulated catch records (CMFRI-shaped)"
        ),
        "scenario": {
            "active": scenario_active,
            "sst_delta_c": sst_delta,
            "fishing_pressure": fishing_pressure,
        },
    }


def bleaching_risk(station_id: str) -> dict:
    st = data.station_by_id(station_id.lower())
    if not st:
        return {"error": f"no station found for id '{station_id}'"}
    history = st["history"]
    sst_series = [h["sst"] for h in history]
    if len(sst_series) < 14:
        return {"error": "not enough SST history for DHW calculation"}

    # Baseline proxy: mean SST over the earliest available 2 weeks, standing in for a
    # long-term climatological Maximum Monthly Mean (MMM) we don't have in this build.
    baseline = float(np.mean(sst_series[:14]))
    threshold = baseline + 1.0

    # Weekly means over the most recent 12 weeks (or as many complete weeks as we have)
    n_weeks = min(12, len(sst_series) // 7)
    weekly_means = [
        float(np.mean(sst_series[len(sst_series) - (i + 1) * 7 : len(sst_series) - i * 7]))
        for i in range(n_weeks)
    ]
    dhw = sum(max(0.0, w - threshold) for w in weekly_means)
    dhw = round(dhw, 2)

    if dhw >= 8:
        alert = "Alert Level 2 — significant bleaching and mortality risk, field check advised within days"
    elif dhw >= 4:
        alert = "Alert Level 1 — significant bleaching risk likely"
    elif dhw >= 1:
        alert = "Bleaching Watch — thermal stress accumulating"
    else:
        alert = "No Stress"

    risk_pct = round(min(100, dhw / 8 * 100), 1)
    confidence_label = "medium" if n_weeks < 8 else "high"
    confidence_pct = confidence.pct_from_count(n_weeks, full_at=8)
    conclusion = conclusions.conclude(
        f"{st['name']} has accumulated {dhw} Degree Heating Weeks over the trailing {n_weeks} weeks, "
        f"putting it at '{alert}' ({risk_pct}% of the alert-2 threshold). Baseline SST proxy {round(baseline, 1)}C, latest reading {st['latest']['sst_c']}C.",
        confidence_label,
    )

    return {
        "station_id": st["id"],
        "station_name": st["name"],
        "dhw": dhw,
        "risk_pct": risk_pct,
        "alert_level": alert,
        "baseline_sst_c": round(baseline, 2),
        "threshold_sst_c": round(threshold, 2),
        "latest_sst_c": st["latest"]["sst_c"],
        "conclusion": conclusion,
        "confidence": confidence_label,
        "confidence_pct": confidence_pct,
        "methodology": "Degree Heating Weeks: sum of weekly-mean SST minus (baseline + 1°C) for weeks above threshold, over the trailing 12 weeks (NOAA Coral Reef Watch-style). Baseline here is a 2-week-early-window proxy, not a multi-year climatology.",
        "source": st["source"],
    }


# Heuristic only (Phase 21 what-if): +/- this fraction of drift velocity per 1°C of
# assumed additional SST anomaly, loosely consistent with warming-correlates-with-
# poleward-shift literature. Illustrative, not a fitted or species-specific coefficient.
SST_VELOCITY_SCALING = 0.15


def range_shift(species: str, sst_delta: float = 0.0) -> dict:
    """sst_delta is a what-if scenario override (Phase 21) — defaults to 0.0 (no-op),
    so an un-scenario'd call returns exactly the real projection. Only scales the
    forward projection's slope, never the observed regression."""
    series_by_species = data.range_shift_series()
    matched_key = next((k for k in series_by_species if species.lower() in k.lower()), None)
    if not matched_key:
        return {"error": f"no range-shift occurrence series for '{species}'", "available": list(series_by_species.keys())}

    series = series_by_species[matched_key]
    if len(series) < 3:
        return {"error": "not enough occurrence-year coverage for a trend line"}

    years = np.array([p["year"] for p in series], dtype=float)
    lats = np.array([p["mean_lat"] for p in series], dtype=float)
    slope, intercept = np.polyfit(years, lats, 1)
    scenario_slope = slope * (1 + SST_VELOCITY_SCALING * sst_delta)

    last_year = int(years.max())
    future_years = np.arange(last_year + 1, last_year + 6)
    # Pivot the projection around the fitted value at the last observed year rather
    # than reusing the year-0 intercept — years are ~2000+, so a small scenario_slope
    # perturbation would otherwise blow up hugely by the time it's multiplied through
    # a ~2000-2030 year value.
    anchor_lat = slope * last_year + intercept
    projected_lats = anchor_lat + scenario_slope * (future_years - last_year)

    direction = "northward (poleward)" if slope > 0 else "southward (equatorward)" if slope < 0 else "no clear shift"
    confidence_label = "low" if len(series) < 5 else "medium"
    # This label logic never reaches "high" — full_at=10 is a reasonable
    # illustrative ceiling for the percentage, not a claim that 10 years
    # would actually earn a "high" label above.
    confidence_pct = confidence.pct_from_count(len(series), full_at=10)
    scenario_active = bool(sst_delta)
    scenario_note = (
        f" Simulated what-if scenario applied: SST anomaly {sst_delta:+.1f}°C scales the projected drift velocity "
        f"by {SST_VELOCITY_SCALING * sst_delta:+.0%} (illustrative heuristic) — this is a hypothetical, not the live projection."
        if scenario_active
        else ""
    )
    conclusion = conclusions.conclude(
        f"Yearly mean occurrence latitude for {matched_key} across {len(series)} years of OBIS/GBIF records "
        f"trends {direction} at {abs(round(float(slope), 3))} degrees latitude/year.{scenario_note}",
        confidence_label,
    )

    return {
        "species": matched_key,
        "observed": series,
        "projection": [
            {"year": int(future_years[i]), "projected_mean_lat": round(float(projected_lats[i]), 3)}
            for i in range(len(future_years))
        ],
        "slope_deg_lat_per_year": round(float(slope), 4),
        "direction": direction,
        "conclusion": conclusion,
        "confidence": confidence_label,
        "confidence_pct": confidence_pct,
        "methodology": "Linear regression (numpy polyfit) of yearly mean occurrence latitude (OBIS/GBIF, Indian EEZ bbox) vs. year, projected 5 years forward. A basic correlation, not a species distribution model.",
        "source": "OBIS/GBIF real occurrence records",
        "scenario": {"active": scenario_active, "sst_delta_c": sst_delta},
    }
