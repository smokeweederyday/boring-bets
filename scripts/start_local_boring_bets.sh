#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p logs .run

TODAY="$(date +%F)"
PORT="${BORING_BETS_LOCAL_PORT:-8001}"
HOST="127.0.0.1"
URL="http://${HOST}:${PORT}/todays-card.html"

stop_pid_file() {
  local pid_file="$1"

  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
  fi

  rm -f "$pid_file"
}

echo "Stopping old local Boring Bets processes..."

stop_pid_file ".run/local-live-mlb.pid"
stop_pid_file ".run/local-starter-watch.pid"
stop_pid_file ".run/local-web.pid"

pkill -f 'scripts/live_mlb_refresh.py' 2>/dev/null || true
pkill -f 'scripts/watch_mlb_starters.py' 2>/dev/null || true
pkill -f 'scripts/refresh_mlb_starters.py' 2>/dev/null || true
pkill -f "python3 -m http.server ${PORT}" 2>/dev/null || true

sleep 1

echo "Starting live MLB feed for ${TODAY}..."

nohup python3 -u scripts/live_mlb_refresh.py \
  --date "${TODAY}" \
  --interval 2 \
  --pregame-interval 10 \
  --settled-interval 60 \
  > logs/local-live-mlb.log 2>&1 &

echo $! > .run/local-live-mlb.pid

echo "Starting MLB starter watcher..."

nohup python3 -u scripts/watch_mlb_starters.py \
  > logs/local-starter-watch.log 2>&1 &

echo $! > .run/local-starter-watch.pid

echo "Starting local website on port ${PORT}..."

nohup python3 -m http.server "${PORT}" \
  --bind "${HOST}" \
  > logs/local-web.log 2>&1 &

echo $! > .run/local-web.pid

echo "Waiting for the local site..."

SITE_READY=0

for _ in {1..30}; do
  if curl -fsS \
    "http://${HOST}:${PORT}/todays-card.html?v=$(date +%s)" \
    >/dev/null 2>&1
  then
    SITE_READY=1
    break
  fi

  sleep 1
done

echo
echo "=== LOCAL SERVICES ==="

for pid_file in \
  .run/local-web.pid \
  .run/local-live-mlb.pid \
  .run/local-starter-watch.pid
do
  name="$(basename "$pid_file" .pid)"
  pid="$(cat "$pid_file" 2>/dev/null || true)"

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "RUNNING  ${name}  PID ${pid}"
  else
    echo "FAILED   ${name}"
  fi
done

echo
echo "=== LIVE FEED CHECK ==="

if curl -fsS \
  "http://${HOST}:${PORT}/data/live-games/${TODAY}.json?v=$(date +%s)" \
  >/dev/null 2>&1
then
  echo "PASS: live MLB JSON is available"
else
  echo "WARNING: live MLB JSON is not available yet"
fi

echo

if [[ "$SITE_READY" -eq 1 ]]; then
  echo "Opening Google Chrome:"
  echo "$URL"

  if open -Ra "Google Chrome" 2>/dev/null; then
    open -a "Google Chrome" "$URL"
  else
    echo "Google Chrome was not found."
    echo "Open manually: $URL"
  fi
else
  echo "FAIL: local website did not respond."
  echo
  echo "Web log:"
  tail -30 logs/local-web.log || true
  exit 1
fi

echo
echo "Watch the logs with:"
echo "tail -F logs/local-web.log logs/local-live-mlb.log logs/local-starter-watch.log"
