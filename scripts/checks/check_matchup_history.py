#!/usr/bin/env python3

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GAMES_PATH = ROOT / "data" / "games.json"


def load_games() -> list[dict[str, Any]]:
    raw = json.loads(GAMES_PATH.read_text(encoding="utf-8"))
    games = raw.get("games", raw) if isinstance(raw, dict) else raw
    if not isinstance(games, list):
        raise SystemExit("FAIL: data/games.json does not contain a games list.")
    return games


def lineup_count(game: dict[str, Any], side: str) -> int:
    lineup = ((game.get("lineups") or {}).get(side) or {})
    players = lineup.get("players") or []
    return sum(1 for player in players if player.get("id"))


def has_pitcher(game: dict[str, Any], side: str) -> bool:
    pitcher = ((game.get("pitchers") or {}).get(side) or {})
    return bool(pitcher.get("id"))


def bvp_side_ready(game: dict[str, Any], key: str) -> bool:
    block = game.get("pitcher_vs_lineup") or {}
    record = block.get(key) or {}
    batters = record.get("batters") or {}
    return isinstance(batters, dict) and bool(batters)


def main() -> None:
    games = load_games()
    today = date.today().isoformat()

    groups = {
        "past": [],
        "today": [],
        "future": [],
    }

    for game in games:
        game_date = game.get("date") or ""
        if game_date < today:
            groups["past"].append(game)
        elif game_date == today:
            groups["today"].append(game)
        else:
            groups["future"].append(game)

    print("BORING BETS MATCHUP HISTORY CHECK")
    print("---------------------------------")

    failures: list[str] = []

    for label, items in groups.items():
        structurally_ready = 0
        populated = 0

        for game in items:
            both_pitchers = (
                has_pitcher(game, "away")
                and has_pitcher(game, "home")
            )
            both_lineups = (
                lineup_count(game, "away") >= 9
                and lineup_count(game, "home") >= 9
            )

            if both_pitchers and both_lineups:
                structurally_ready += 1

            if (
                bvp_side_ready(game, "away_pitcher")
                and bvp_side_ready(game, "home_pitcher")
            ):
                populated += 1

        print()
        print(label.upper())
        print("Games:", len(items))
        print("Structurally ready:", structurally_ready)
        print("BVP populated both sides:", populated)

        if label == "past" and structurally_ready > 0:
            missing = structurally_ready - populated
            coverage = populated / structurally_ready

            print("Missing ready games:", missing)
            print("Coverage:", f"{coverage:.1%}")

            if populated < structurally_ready:
                failures.append(
                    f"Past BVP coverage is incomplete: "
                    f"{populated}/{structurally_ready} ready games populated."
                )

    print()
    if failures:
        print("FAIL:")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)

    print("PASS: matchup history coverage check completed.")


if __name__ == "__main__":
    main()
