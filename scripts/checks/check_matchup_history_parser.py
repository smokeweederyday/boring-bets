#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "scripts").resolve()))

from mlb.matchup_history import (  # noqa: E402
    fetch_live_game,
    summarize_game_matchups,
)


GAMES_PATH = ROOT / "data" / "games.json"
TEST_GAME_ID = "2026-03-25-nyy-sfg"


def main() -> None:
    games = json.loads(
        GAMES_PATH.read_text(encoding="utf-8")
    )["games"]

    game = next(
        item for item in games
        if item.get("id") == TEST_GAME_ID
    )

    raw = fetch_live_game(
        int(game["mlb_game_pk"])
    )

    rows = summarize_game_matchups(raw)

    parsed = {
        "ab": 0,
        "h": 0,
        "hr": 0,
        "k": 0,
        "bb": 0,
        "hbp": 0,
        "sf": 0,
    }

    for row in rows.values():
        parsed["ab"] += int(row.get("at_bats") or 0)
        parsed["h"] += int(row.get("hits") or 0)
        parsed["hr"] += int(row.get("home_runs") or 0)
        parsed["k"] += int(row.get("strikeouts") or 0)
        parsed["bb"] += int(row.get("walks") or 0)
        parsed["hbp"] += int(row.get("hit_by_pitch") or 0)
        parsed["sf"] += int(row.get("sac_flies") or 0)

    teams = raw["liveData"]["boxscore"]["teams"]

    box = {
        "ab": sum(
            teams[side]["teamStats"]["batting"].get("atBats", 0)
            for side in ("away", "home")
        ),
        "h": sum(
            teams[side]["teamStats"]["batting"].get("hits", 0)
            for side in ("away", "home")
        ),
        "hr": sum(
            teams[side]["teamStats"]["batting"].get("homeRuns", 0)
            for side in ("away", "home")
        ),
        "k": sum(
            teams[side]["teamStats"]["batting"].get("strikeOuts", 0)
            for side in ("away", "home")
        ),
        "bb": sum(
            teams[side]["teamStats"]["batting"].get("baseOnBalls", 0)
            for side in ("away", "home")
        ),
        "hbp": sum(
            teams[side]["teamStats"]["batting"].get("hitByPitch", 0)
            for side in ("away", "home")
        ),
        "sf": sum(
            teams[side]["teamStats"]["batting"].get("sacFlies", 0)
            for side in ("away", "home")
        ),
    }

    failures = []

    print("MATCHUP HISTORY PARSER CHECK")
    print("----------------------------")
    print("Game:", TEST_GAME_ID)
    print("Matchups:", len(rows))

    for field in parsed:
        passed = parsed[field] == box[field]

        print(
            field.upper(),
            "PASS" if passed else "FAIL",
            parsed[field],
            box[field],
        )

        if not passed:
            failures.append(
                f"{field}: parsed={parsed[field]} box={box[field]}"
            )

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)

    print("\nPASS: play-by-play totals match the official box score.")


if __name__ == "__main__":
    main()
