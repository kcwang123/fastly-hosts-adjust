#!/bin/sh
# OpenWrt cron entrypoint. Exclusive lock; never removes another process' lock.
set -eu
BASE=/etc/fastly-optimizer
STATE=/tmp/fastly-optimizer
LOCK=/tmp/fastly-optimizer-run.lock
mkdir -p "$STATE"
if ! mkdir "$LOCK" 2>/dev/null; then
  logger -t fastly-optimizer "previous scan still holds lock; skipped"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT HUP INT TERM
python3 /usr/lib/fastly-optimizer/readonly_launcher.py \
  --config "$BASE/config.json" \
  --state "$STATE/state.json" \
  --scan-output "$STATE/scan.json"
