#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "scripts").resolve()))

from mlb.matchup_history import build_game_career_bvp  # noqa: E402


GAMES_PATH = ROOT / "data" / "games.json"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python3 -u scripts/maintenance/"
            "backfill_matchup_history.py YYYY-MM-DD"
        )

    target_date = sys.argv[1]

    raw = json.loads(
        GAMES_PATH.read_text(encoding="utf-8")
    )

    games = raw.get("games", [])
    target_games = [
        game
        for game in games
        if game.get("date") == target_date
    ]

    if not target_games:
        raise SystemExit(
            f"No games found for {target_date}."
        )

    print(
        f"Building matchup history for "
        f"{len(target_games)} game(s) on {target_date}..."
    )

    updated = 0
    skipped = 0
    failed = 0

    for index, game in enumerate(target_games, start=1):
        game_id = game.get("id") or "unknown"

        pitchers = game.get("pitchers") or {}
        lineups = game.get("lineups") or {}

        ready = (
            (pitchers.get("away") or {}).get("id")
            and (pitchers.get("home") or {}).get("id")
            and len((lineups.get("away") or {}).get("players") or []) >= 9
            and len((lineups.get("home") or {}).get("players") or []) >= 9
        )

        print(
            f"[{index}/{len(target_games)}] {game_id}"
        )

        if not ready:
            print("  SKIP: missing pitchers or complete lineups.")
            skipped += 1
            continue

        try:
            history = build_game_career_bvp(game)
            game["pitcher_vs_lineup"] = history

            away_rows = (
                history.get("away_pitcher", {})
                .get("batters", {})
            )
            home_rows = (
                history.get("home_pitcher", {})
                .get("batters", {})
            )

            away_pa = sum(
                int(row.get("plate_appearances") or 0)
                for row in away_rows.values()
            )
            home_pa = sum(
                int(row.get("plate_appearances") or 0)
                for row in home_rows.values()
            )

            print(
                f"  WROTE: away pitcher {len(away_rows)} batters/"
                f"{away_pa} PA; home pitcher {len(home_rows)} batters/"
                f"{home_pa} PA"
            )

            updated += 1

        except Exception as error:
            print(f"  FAIL: {error}")
            failed += 1

    if updated:
        GAMES_PATH.write_text(
            json.dumps(raw, indent=2) + "\n",
            encoding="utf-8",
        )

    print()
    print("MATCHUP HISTORY BACKFILL COMPLETE")
    print("Updated:", updated)
    print("Skipped:", skipped)
    print("Failed:", failed)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
