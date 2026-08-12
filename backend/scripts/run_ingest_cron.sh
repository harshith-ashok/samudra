#!/bin/sh
# Wrapper for scheduling scripts/ingest_copernicus.py (Phase 25). Re-runs the
# full pull and overwrites backend/data/cache/ocean/ — safe to run daily.
#
# Not installed into any crontab/launchd schedule by this build; wire it in
# yourself, e.g.:
#   crontab -e
#   0 6 * * * /path/to/samudra_ai/backend/scripts/run_ingest_cron.sh >> /tmp/samudra_ingest.log 2>&1
set -eu
cd "$(dirname "$0")/.."
uv run python3 scripts/ingest_copernicus.py
