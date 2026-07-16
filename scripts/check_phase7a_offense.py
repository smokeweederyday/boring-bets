#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ("AVG", "OBP", "SLG", "OPS", "BB%", "K%")
TIMEFRAMES = ("last_7", "last_30", "season")
LOCATIONS = ("all", "home", "away")

def main() -> int:
    payload = json.loads((ROOT / "data/games.json").read_text())
    games = payload.get("games", []) if isinstance(payload, dict) else payload
    enriched = [g for g in games if g.get("offense")]
    if not enriched:
        print("FAIL: no enriched offense games found.")
        return 1
    failures=[]
    checked=0
    for game in enriched:
        for side in ("away", "home"):
            block=game.get("offense",{}).get(side,{})
            stats=block.get("stats",{})
            team=block.get("team") or game.get(f"{side}_team",{}).get("abbr") or side
            for timeframe in TIMEFRAMES:
                for location in LOCATIONS:
                    selected=stats.get(timeframe,{}).get(location,{})
                    for metric in CORE:
                        row=selected.get(metric,{})
                        value=row.get("overall")
                        rank=row.get("overall_rank")
                        if value is None:
                            failures.append(f"{team} {timeframe}/{location} {metric}: missing value")
                        if not isinstance(rank,int) or not 1 <= rank <= 30:
                            failures.append(f"{team} {timeframe}/{location} {metric}: bad rank {rank}")
                    checked += 1
        if checked >= 18:
            break
    sample=enriched[0]
    print("Sample game:",sample.get("id"))
    for side in ("away","home"):
        team=sample.get(f"{side}_team",{}).get("abbr",side)
        season=sample.get("offense",{}).get(side,{}).get("stats",{}).get("season",{})
        avgs=[season.get(loc,{}).get("AVG",{}).get("overall") for loc in LOCATIONS]
        print(f"{team} season AVG all/home/away: {avgs}")
        if any(v is None for v in avgs) or len(set(avgs)) < 2:
            failures.append(f"{team} season location values empty or identical: {avgs}")
    if failures:
        print(f"FAIL: {len(failures)} offense contract issue(s).")
        for failure in failures[:30]: print(" -",failure)
        return 1
    print(f"PASS: checked {checked} offense timeframe/location blocks with six core values and 1-30 ranks.")
    print("wRC+ is intentionally allowed to remain unavailable during Phase 7A.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
