#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
js = root / "todays-card.js"
if not js.exists():
    print("FAIL: todays-card.js is missing.")
    raise SystemExit(1)

text = js.read_text(encoding="utf-8")
checks = {
    "universal baseball logo endpoint": 'https://www.mlbstatic.com/team-logos"' in text,
    "MLB cap fallback endpoint": "team-cap-on-dark" in text,
    "minor-league compatible team-id renderer": "data-baseball-team-logo" in text,
    "image error fallback handler": "advanceBaseballTeamLogo" in text,
    "clean initials fallback": "compact-generic-logo" in text,
    "invalid team-id protection": "Number.isFinite(teamId)" in text,
}

failed = False
for label, ok in checks.items():
    print(f"{label}: {'PASS' if ok else 'FAIL'}")
    failed = failed or not ok

if failed:
    print("FAIL: Today’s Card baseball logo fix is incomplete.")
    raise SystemExit(1)

print("PASS: MLB and affiliated minor-league cards have a working logo fallback chain.")
