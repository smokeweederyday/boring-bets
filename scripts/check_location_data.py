#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
games = json.loads((ROOT / "data" / "games.json").read_text())
if isinstance(games, dict):
    games = games.get("games", [])

game = next((g for g in games if g.get("pitchers") and g.get("offense")), None)
if not game:
    raise SystemExit("No enriched game found in data/games.json")

print("Game:", game.get("id"))
failed = False
for side in ("away", "home"):
    team = game.get(f"{side}_team", {}).get("abbr", side.upper())
    offense = game.get("offense", {}).get(side, {}).get("stats", {})
    vals = []
    for loc in ("all", "home", "away"):
        avg = offense.get("season", {}).get(loc, {}).get("AVG", {}).get("overall")
        vals.append(avg)
    print(f"{team} offense season AVG all/home/away: {vals}")
    if vals[1] == vals[0] == vals[2] or vals[1] is None or vals[2] is None:
        failed = True

    pitcher = game.get("pitchers", {}).get(side, {})
    pvals = [pitcher.get("stats", {}).get("season", {}).get(loc, {}).get("era") for loc in ("all","home","away")]
    print(f"{pitcher.get('name', team)} pitcher season ERA all/home/away: {pvals}")
    if pvals[1] is None and pvals[2] is None:
        failed = True

if failed:
    raise SystemExit("FAIL: location blocks are still empty or identical. Send this output.")
print("PASS: separate offense and pitcher location blocks are present.")
