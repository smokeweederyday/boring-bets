#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mlb.offense import fetch_team_hitting_stats
from mlb.pitchers import _global_pitcher_stats


def main() -> int:
    season = 2026
    team_id = 121
    all_stats = fetch_team_hitting_stats(team_id, "season", season)
    home_stats = fetch_team_hitting_stats(team_id, "season", season, sit_code="h")
    away_stats = fetch_team_hitting_stats(team_id, "season", season, sit_code="a")
    print("NYM offense season")
    print("ALL :", all_stats)
    print("HOME:", home_stats)
    print("AWAY:", away_stats)

    all_pitchers = _global_pitcher_stats("2026-07-16", "season", "all")
    home_pitchers = _global_pitcher_stats("2026-07-16", "season", "home")
    away_pitchers = _global_pitcher_stats("2026-07-16", "season", "away")
    print(f"Pitcher rows — all:{len(all_pitchers)} home:{len(home_pitchers)} away:{len(away_pitchers)}")

    offense_differs = home_stats != away_stats and home_stats != all_stats
    pitcher_available = bool(home_pitchers) and bool(away_pitchers)
    if not offense_differs or not pitcher_available:
        print("FAIL: location filters are still not producing distinct data.")
        return 1
    print("PASS: offense and pitcher location filters are active.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
