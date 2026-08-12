"""Reads the Copernicus-derived per-station SST/chlorophyll series written by
scripts/ingest_copernicus.py to backend/data/cache/ocean/, and merges them
into the exact shapes services/predict.py, services/reefs.py, and
services/timeline.py already expect from data.stations() — so DHW, the
timeline scrubber, and the correlation/stock-forecast SST input get real data
with zero change to those modules' own function signatures or output shape.

Falls back to the original simulated data/stations.json `history` array
whenever the cache is missing, empty, or doesn't cover a station — every
`_merged_history()` call re-checks this per station per call rather than
caching a "cache is present" flag at import time, so a cache that goes stale
mid-demo (or gets deleted) degrades gracefully on the very next request
instead of requiring a restart.
"""

from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "ocean"
STALE_AFTER_DAYS = 5  # NRT SST/CHL update ~daily; a gap this wide means the scheduled pull stopped running

# Which station stands in for each catch-record region string — same
# "eyeballed from station clusters" methodology already used by
# services/regions.py's REGION_CIRCLES, not survey-grade zoning.
REGION_STATION = {
    "kerala coast": "kochi",
    "tamil nadu coast": "chennai",
    "arabian sea": "mumbai",
}

# station_id -> (mtime, DataFrame). A plain @lru_cache on station_id alone
# would never notice the underlying parquet file changing (a re-run of
# scripts/ingest_copernicus.py, or the file being moved/deleted to test the
# fallback path) short of a process restart — keying on mtime instead means a
# changed or removed file is picked up on the very next call, which is what
# the module docstring above actually promises.
_frame_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def _load_station_frame(station_id: str) -> pd.DataFrame | None:
    path = CACHE_DIR / f"{station_id}.parquet"
    if not path.exists():
        _frame_cache.pop(station_id, None)
        return None
    mtime = path.stat().st_mtime
    cached = _frame_cache.get(station_id)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        df = pd.read_parquet(path)
    except Exception:
        return None
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    _frame_cache[station_id] = (mtime, df)
    return df


def cache_status(station_id: str) -> dict:
    """Diagnostic only (not used by the prediction code path) — lets a
    reliability check or a debug endpoint see why a station did or didn't get
    real data without re-deriving the fallback logic."""
    df = _load_station_frame(station_id)
    if df is None:
        return {"available": False, "reason": "no cache file for this station"}
    latest = df["date"].max()
    age_days = (pd.Timestamp.now(tz=None) - latest).days
    stale = age_days > STALE_AFTER_DAYS
    return {
        "available": not stale,
        "reason": f"latest cached day is {age_days}d old (stale after {STALE_AFTER_DAYS}d)" if stale else None,
        "rows": len(df),
        "date_min": str(df["date"].min().date()),
        "date_max": str(latest.date()),
    }


def merged_history(station: dict) -> list[dict]:
    """Real sst/chlorophyll merged onto the station's existing simulated
    `history` shape ({day, sst, salinity, chlorophyll}), day-indexed the same
    way the simulated data always was (day 0 = most recent, negative = past).
    Salinity has no Copernicus source in this pull (SST + chlorophyll only,
    per the ground rules) so it's carried over from the simulated series,
    cycling it across the longer real date range rather than inventing new
    values — clearly not claimed as real (see source label on the caller side).
    Falls back to the untouched simulated `history` verbatim if the cache
    doesn't cover this station or has gone stale.
    """
    df = _load_station_frame(station["id"])
    if df is None:
        return station["history"]

    latest = df["date"].max()
    if (pd.Timestamp.now(tz=None) - latest).days > STALE_AFTER_DAYS:
        return station["history"]

    sim = station["history"]
    sim_salinity = [h["salinity"] for h in sim] or [35.0]

    rows = df.to_dict("records")
    merged = []
    for i, row in enumerate(rows):
        day = (row["date"].date() - latest.date()).days
        sst = row.get("sst_c")
        chl = row.get("chl_mg_m3")
        if pd.isna(sst) and pd.isna(chl):
            continue
        merged.append(
            {
                "day": day,
                "sst": round(float(sst), 2) if pd.notna(sst) else None,
                "salinity": sim_salinity[i % len(sim_salinity)],
                "chlorophyll": round(float(chl), 3) if pd.notna(chl) else None,
            }
        )

    # DHW/timeline/reefs.py's chlorophyll-trend fit all need every day in the
    # window to have a value (np.polyfit can't handle a None) — forward-fill
    # isolated real gaps rather than dropping the day entirely, which would
    # shift the day-index spacing the callers assume is daily. A backward
    # pass then covers the case where the very first day(s) start with a gap
    # and have nothing earlier to forward-fill from.
    for field in ("sst", "chlorophyll"):
        last = None
        for row in merged:
            if row[field] is None:
                row[field] = last
            else:
                last = row[field]
        last = None
        for row in reversed(merged):
            if row[field] is None:
                row[field] = last
            else:
                last = row[field]
    merged = [r for r in merged if r["sst"] is not None and r["chlorophyll"] is not None]
    return merged if merged else station["history"]


def source_label(station: dict) -> str:
    """Overrides the station's hardcoded simulated `source` string once real
    data is actually feeding it — the field is judge-facing (surfaced
    verbatim in /api/predict/bleaching), so it needs to track reality, not
    just say "simulated" forever after this cache lands."""
    df = _load_station_frame(station["id"])
    if df is None:
        return station["source"]
    latest = df["date"].max()
    if (pd.Timestamp.now(tz=None) - latest).days > STALE_AFTER_DAYS:
        return station["source"]
    return (
        f"SST: Copernicus Marine OSTIA L4 NRT (real, through {latest.date()}). "
        "Chlorophyll: Copernicus Marine Ocean Colour L4 gap-free, reprocessed history "
        "+ NRT trailing window (real). Salinity: simulated (INCOIS/CMEMS-shaped, no live feed)."
    )


def merged_latest(station: dict) -> dict:
    df = _load_station_frame(station["id"])
    fallback = station["latest"]
    if df is None:
        return fallback
    latest_row = df.iloc[-1]
    if (pd.Timestamp.now(tz=None) - latest_row["date"]).days > STALE_AFTER_DAYS:
        return fallback
    return {
        "sst_c": round(float(latest_row["sst_c"]), 2) if pd.notna(latest_row.get("sst_c")) else fallback["sst_c"],
        "salinity_psu": fallback["salinity_psu"],
        "chlorophyll_mg_m3": round(float(latest_row["chl_mg_m3"]), 3) if pd.notna(latest_row.get("chl_mg_m3")) else fallback["chlorophyll_mg_m3"],
    }


def region_monthly_sst(region: str, date_str: str) -> tuple[float | None, str]:
    """Mean real SST for the calendar month of `date_str` (a catch record's
    "YYYY-MM-01" date) at the station standing in for `region`. Returns
    (None, "simulated") if there's no real coverage for that region/month —
    the caller falls back to the catch record's own seed sst_c in that case."""
    station_id = REGION_STATION.get(region.lower())
    if not station_id:
        return None, "simulated"
    df = _load_station_frame(station_id)
    if df is None:
        return None, "simulated"
    target = pd.Timestamp(date_str)
    month_mask = (df["date"].dt.year == target.year) & (df["date"].dt.month == target.month)
    month_vals = df.loc[month_mask, "sst_c"].dropna()
    if month_vals.empty:
        return None, "simulated"
    return round(float(month_vals.mean()), 2), "copernicus_sst_l4_nrt"
