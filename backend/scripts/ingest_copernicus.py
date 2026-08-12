"""Phase 25 ingestion: pulls real per-station SST + chlorophyll series from
Copernicus Marine and writes them to backend/data/cache/ocean/ as parquet.

Product IDs confirmed against the live catalogue on 2026-08-12 (the user's
first guess for SST didn't exist; this is the corrected, verified pair):

  SST         product SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001 (OSTIA)
              dataset METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2, variable analysed_sst
              NRT only — the rolling archive already covers 2024-01-17 to date,
              well past the 2-year target, so no reanalysis needed here.

  Chlorophyll product OCEANCOLOUR_GLO_BGC_L4_NRT_009_102, variable CHL
              NRT dataset cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D
              only retains a ~2-week rolling window — nowhere near 2 years.
              Backfilled with the reprocessed line's gap-free dataset
              (cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D, which
              CMEMS keeps extended to within ~days of the present) for
              everything before the NRT window, then NRT for the trailing
              stretch. Each row's `chl_source` column says which one it came
              from — never silently blended without a trail.

Re-runnable: safe to run again anytime (a cron job, a manual re-run before a
demo) — always re-pulls the full available range and overwrites, no
incremental state to get out of sync. Runtime is a few minutes for SST, longer
for chlorophyll (see below), not per-request, per CLAUDE.md's ingestion
convention.

A note on the chlorophyll MY (history) pull specifically: lazy point access
via copernicusmarine.open_dataset(...).sel(lat, lng).load() — the approach
that works fine for SST in seconds — hangs indefinitely on this particular
dataset regardless of service ("arco-geo-series" vs "arco-time-series") or
requested date range (tested full 28-year range and a bounded ~3-year range;
both hung past 45s with the point-load itself, not the dataset open, stuck at
0% CPU). copernicusmarine.subset() (an actual file download, not lazy chunk
access) works reliably against the same dataset in ~30-40s per small box, so
that's what's used here for the MY pull. NRT chlorophyll and SST stay on the
fast lazy-load path since both are small and were verified to work directly.
"""

import json
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import copernicusmarine
import numpy as np
import pandas as pd
import xarray as xr

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache" / "ocean"

SST_DATASET = "METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2"
CHL_NRT_DATASET = "cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D"
CHL_MY_DATASET = "cmems_obs-oc_glo_bgc-plankton_my_l4-gapfree-multi-4km_P1D"

# Covers every station in data/stations.json with margin for the nearest-valid-
# pixel search below.
BBOX = dict(minimum_longitude=67.5, maximum_longitude=93.5, minimum_latitude=7.0, maximum_latitude=23.5)

# How far a station's real-data pixel may drift from its plotted coordinate
# when the exact point is land-masked (coastal buoys often sit on a masked
# shoreline pixel at ~5km/4km grid resolution) — grown in steps until a valid
# ocean cell is found, capped so a station never silently binds to a
# wildly-wrong-looking pixel.
SEARCH_STEPS_DEG = [0.05, 0.1, 0.2, 0.35, 0.5]


def stations() -> list[dict]:
    return json.loads((DATA_DIR / "stations.json").read_text())


def _nearest_ocean_pixel(mask_slice, lat: float, lng: float) -> tuple[float, float] | None:
    """First non-NaN pixel found in `mask_slice` (a single time-step 2D
    DataArray), searching an expanding window centered on (lat, lng)."""
    for radius in SEARCH_STEPS_DEG:
        window = mask_slice.sel(
            latitude=slice(lat - radius, lat + radius),
            longitude=slice(lng - radius, lng + radius),
        )
        if window.size == 0:
            continue
        valid = window.where(~window.isnull(), drop=True)
        if valid.size == 0:
            continue
        # nearest among the valid cells only
        lat_grid, lng_grid = np.meshgrid(valid.latitude.values, valid.longitude.values, indexing="ij")
        dist2 = (lat_grid - lat) ** 2 + (lng_grid - lng) ** 2
        vals = valid.values
        dist2 = np.where(np.isnan(vals), np.inf, dist2)
        idx = np.unravel_index(np.argmin(dist2), dist2.shape)
        return float(valid.latitude.values[idx[0]]), float(valid.longitude.values[idx[1]])
    return None


def _resolve_station_pixels(mask_slice, sts: list[dict]) -> dict[str, tuple[float, float]]:
    resolved = {}
    for st in sts:
        pixel = _nearest_ocean_pixel(mask_slice, st["lat"], st["lng"])
        if pixel is None:
            print(f"  ! {st['id']}: no valid ocean pixel found within {SEARCH_STEPS_DEG[-1]}deg — skipping", flush=True)
            continue
        drift_km = ((pixel[0] - st["lat"]) ** 2 + (pixel[1] - st["lng"]) ** 2) ** 0.5 * 111
        flag = " (land-adjacent, snapped)" if drift_km > 1 else ""
        print(f"  {st['id']:12s} ({st['lat']:.3f},{st['lng']:.3f}) -> pixel ({pixel[0]:.3f},{pixel[1]:.3f}) drift~{drift_km:.1f}km{flag}", flush=True)
        resolved[st["id"]] = pixel
    return resolved


def pull_sst(sts: list[dict]) -> tuple[dict[str, pd.DataFrame], dict[str, tuple[float, float]]]:
    print("Opening SST dataset (lazy)...", flush=True)
    ds = copernicusmarine.open_dataset(dataset_id=SST_DATASET, variables=["analysed_sst"], **BBOX)
    first_step = ds["analysed_sst"].isel(time=0).load()
    print("Resolving station pixels against SST land mask...", flush=True)
    pixels = _resolve_station_pixels(first_step, sts)

    out = {}
    for st in sts:
        if st["id"] not in pixels:
            continue
        lat, lng = pixels[st["id"]]
        series = ds["analysed_sst"].sel(latitude=lat, longitude=lng, method="nearest").load()
        df = pd.DataFrame({"date": pd.to_datetime(series.time.values).date, "sst_c": series.values - 273.15})
        df = df.dropna(subset=["sst_c"])
        df["sst_c"] = df["sst_c"].round(3)
        out[st["id"]] = df
        print(f"  {st['id']}: {len(df)} SST days ({df['date'].min()} to {df['date'].max()})", flush=True)
    return out, pixels


def _subset_box_series(dataset_id: str, lat: float, lng: float, start: str, end: str, tmp_dir: Path, box_deg: float = 0.05) -> pd.Series:
    """Downloads a small box (a handful of pixels, not a full grid — per the
    checklist) around (lat, lng) and averages whatever real (non-NaN) pixels
    land inside it into one daily series. Returns a pandas Series indexed by
    date, value = spatial-mean CHL for that day."""
    out_name = f"box_{lat:.3f}_{lng:.3f}.nc"
    copernicusmarine.subset(
        dataset_id=dataset_id,
        variables=["CHL"],
        minimum_longitude=lng - box_deg, maximum_longitude=lng + box_deg,
        minimum_latitude=lat - box_deg, maximum_latitude=lat + box_deg,
        start_datetime=start, end_datetime=end,
        output_directory=str(tmp_dir), output_filename=out_name,
        disable_progress_bar=True,
    )
    with xr.open_dataset(tmp_dir / out_name) as ds:
        series = ds["CHL"].mean(dim=["latitude", "longitude"], skipna=True).load()
        result = pd.Series(series.values, index=pd.to_datetime(series.time.values))
    (tmp_dir / out_name).unlink(missing_ok=True)
    return result


def pull_chlorophyll(sts: list[dict], pixels: dict[str, tuple[float, float]]) -> dict[str, pd.DataFrame]:
    """MY (history) via subset()-download per station — see module docstring
    for why lazy access hangs on this specific dataset. NRT (trailing window)
    stays on the fast lazy-load path since it's small and was verified to
    work directly. Reuses the SST-resolved pixel per station rather than
    re-deriving a chlorophyll-specific land mask (same real-world point;
    close enough between the two products' grids that a small subset box
    around it reliably contains a valid ocean pixel either way)."""
    print("Checking chlorophyll NRT dataset's available date range (lazy, metadata only)...", flush=True)
    ds_nrt = copernicusmarine.open_dataset(dataset_id=CHL_NRT_DATASET, variables=["CHL"], **BBOX)
    nrt_start = pd.Timestamp(ds_nrt.time.values.min())
    my_end = (nrt_start - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    # Same start as SST for parity across variables (both real, both ~2.5yrs).
    my_start = "2024-01-17"

    tmp_dir = Path(tempfile.mkdtemp(prefix="samudra_chl_"))
    out = {}
    try:
        for i, st in enumerate(sts):
            if st["id"] not in pixels:
                continue
            lat, lng = pixels[st["id"]]
            t0 = time.time()
            my_vals = _subset_box_series(CHL_MY_DATASET, lat, lng, my_start, my_end, tmp_dir)
            my_df = pd.DataFrame({"date": my_vals.index, "chl_mg_m3": my_vals.values, "chl_source": "copernicus_my_gapfree"})

            # Wider box for NRT: its trailing-window gap-fill is short enough
            # that a single coastal/turbid pixel can still come back fully
            # NaN even though the MY product's longer fill window covers the
            # same spot (observed at the Mumbai pixel during dry-run testing)
            # — a bigger box has a better chance of finding a valid neighbor.
            nrt_end = ds_nrt.time.values.max()
            nrt_vals = _subset_box_series(
                CHL_NRT_DATASET, lat, lng, str(nrt_start.date()), str(pd.Timestamp(nrt_end).date()), tmp_dir, box_deg=0.15
            )
            nrt_df = pd.DataFrame({"date": nrt_vals.index, "chl_mg_m3": nrt_vals.values, "chl_source": "copernicus_nrt_gapfree"})

            combined = pd.concat([my_df, nrt_df], ignore_index=True).dropna(subset=["chl_mg_m3"])
            combined["date"] = combined["date"].dt.date
            combined["chl_mg_m3"] = combined["chl_mg_m3"].round(4)
            combined = combined.sort_values("date").drop_duplicates("date", keep="last")
            out[st["id"]] = combined
            print(
                f"  ({i + 1}/{len(sts)}) {st['id']}: {len(combined)} CHL days "
                f"({combined['date'].min()} to {combined['date'].max()}) in {time.time() - t0:.1f}s",
                flush=True,
            )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return out


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    sts = stations()
    t0 = time.time()

    sst_by_station, pixels = pull_sst(sts)
    chl_by_station = pull_chlorophyll(sts, pixels)

    manifest = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "sst_dataset": SST_DATASET,
        "chl_nrt_dataset": CHL_NRT_DATASET,
        "chl_my_dataset": CHL_MY_DATASET,
        "stations": {},
    }

    for st in sts:
        sid = st["id"]
        sst_df = sst_by_station.get(sid)
        chl_df = chl_by_station.get(sid)
        if sst_df is None and chl_df is None:
            continue
        merged = pd.merge(
            sst_df if sst_df is not None else pd.DataFrame(columns=["date", "sst_c"]),
            chl_df if chl_df is not None else pd.DataFrame(columns=["date", "chl_mg_m3", "chl_source"]),
            on="date",
            how="outer",
        ).sort_values("date")
        merged["date"] = pd.to_datetime(merged["date"])
        out_path = CACHE_DIR / f"{sid}.parquet"
        merged.to_parquet(out_path, index=False)
        manifest["stations"][sid] = {
            "rows": len(merged),
            "sst_days": int(merged["sst_c"].notna().sum()) if "sst_c" in merged else 0,
            "chl_days": int(merged["chl_mg_m3"].notna().sum()) if "chl_mg_m3" in merged else 0,
            "date_min": str(merged["date"].min().date()) if len(merged) else None,
            "date_max": str(merged["date"].max().date()) if len(merged) else None,
        }

    (CACHE_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nDone in {round(time.time() - t0, 1)}s — {len(manifest['stations'])} stations written to {CACHE_DIR}", flush=True)


if __name__ == "__main__":
    main()
