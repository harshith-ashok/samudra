"""Three simple, honestly-documented prediction methods — see CLAUDE.md's
"Predictions" section. None of this is a formal stock assessment or climate
model; each is a straightforward trend extrapolation over the seed data,
returned with its methodology so the frontend/judges can see exactly what ran.
"""

import numpy as np

from services import conclusions, data


def stock_forecast(species: str, region: str, months_ahead: int = 6) -> dict:
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

    future_x = np.arange(len(y), len(y) + months_ahead, dtype=float)
    forecast_mean = slope * future_x + intercept
    # widening 80% CI band (z ~ 1.28) that grows with distance from the fit
    z = 1.28
    forecast_lo = forecast_mean - z * residual_std * (1 + 0.15 * np.arange(months_ahead))
    forecast_hi = forecast_mean + z * residual_std * (1 + 0.15 * np.arange(months_ahead))

    direction = "rising" if slope > 0.5 else "falling" if slope < -0.5 else "roughly flat"
    confidence = "low" if len(records) < 6 else "medium" if len(records) < 12 else "high"
    conclusion = conclusions.conclude(
        f"Linear trend fit to {len(records)} months of catch data for {species} in {region}: "
        f"{direction} at {abs(round(float(slope), 1))} tonnes/month, projecting {round(float(forecast_mean[0]), 0)} "
        f"tonnes next month (80% CI {round(float(forecast_lo[0]), 0)}-{round(float(forecast_hi[0]), 0)}).",
        confidence,
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
        "confidence": confidence,
        "methodology": "Linear regression (numpy polyfit, degree 1) of monthly catch tonnage vs. time; 80% CI band widens linearly with forecast horizon. Trend-extrapolation only, not a stock assessment.",
        "source": "simulated catch records (CMFRI-shaped)",
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
    confidence = "medium" if n_weeks < 8 else "high"
    conclusion = conclusions.conclude(
        f"{st['name']} has accumulated {dhw} Degree Heating Weeks over the trailing {n_weeks} weeks, "
        f"putting it at '{alert}' ({risk_pct}% of the alert-2 threshold). Baseline SST proxy {round(baseline, 1)}C, latest reading {st['latest']['sst_c']}C.",
        confidence,
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
        "confidence": confidence,
        "methodology": "Degree Heating Weeks: sum of weekly-mean SST minus (baseline + 1°C) for weeks above threshold, over the trailing 12 weeks (NOAA Coral Reef Watch-style). Baseline here is a 2-week-early-window proxy, not a multi-year climatology.",
        "source": st["source"],
    }


def range_shift(species: str) -> dict:
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

    last_year = int(years.max())
    future_years = np.arange(last_year + 1, last_year + 6)
    projected_lats = slope * future_years + intercept

    direction = "northward (poleward)" if slope > 0 else "southward (equatorward)" if slope < 0 else "no clear shift"
    confidence = "low" if len(series) < 5 else "medium"
    conclusion = conclusions.conclude(
        f"Yearly mean occurrence latitude for {matched_key} across {len(series)} years of OBIS/GBIF records "
        f"trends {direction} at {abs(round(float(slope), 3))} degrees latitude/year.",
        confidence,
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
        "confidence": confidence,
        "methodology": "Linear regression (numpy polyfit) of yearly mean occurrence latitude (OBIS/GBIF, Indian EEZ bbox) vs. year, projected 5 years forward. A basic correlation, not a species distribution model.",
        "source": "OBIS/GBIF real occurrence records",
    }
