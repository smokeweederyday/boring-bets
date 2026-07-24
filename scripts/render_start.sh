#!/usr/bin/env bash
set -euo pipefail

mkdir -p logs

echo "Starting MLB starter watcher..."
python3 -u scripts/watch_mlb_starters.py \
  >> logs/render-mlb-starter-watch.log 2>&1 &

STARTER_WATCH_PID=$!

cleanup() {
  kill "$STARTER_WATCH_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Starting Boring Bets web server..."
exec python3 -u scripts/render_staging.py
