#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GAMES_PATH = ROOT / "data" / "games.json"
TEST_GAME_ID = "2026-03-25-nyy-sfg"


def main() -> None:
    games = json.loads(
        GAMES_PATH.read_text(encoding="utf-8")
    )["games"]

    game = next(
        item
        for item in games
        if item.get("id") == TEST_GAME_ID
    )

    block = game.get("pitcher_vs_lineup") or {}
    failures: list[str] = []

    print("SAVED MATCHUP HISTORY CHECK")
    print("---------------------------")
    print("Game:", TEST_GAME_ID)

    for key in ("away_pitcher", "home_pitcher"):
        record: dict[str, Any] = block.get(key) or {}
        rows = record.get("batters") or {}

        combined_pa = sum(
            int(row.get("plate_appearances") or 0)
            for row in rows.values()
            if isinstance(row, dict)
        )

        print()
        print(key)
        print("Pitcher:", record.get("pitcher_name"))
        print("Batters:", len(rows))
        print("Combined PA:", combined_pa)
        print("Source:", record.get("source"))
        print("Scope:", record.get("history_scope"))
        print("As of:", record.get("as_of_date"))

        if len(rows) != 9:
            failures.append(
                f"{key}: expected 9 batter records, found {len(rows)}."
            )

        if record.get("source") != "MLB play-by-play career history":
            failures.append(
                f"{key}: incorrect source."
            )

        if record.get("history_scope") != "career_entering_game":
            failures.append(
                f"{key}: incorrect history scope."
            )

        if record.get("as_of_date") != game.get("date"):
            failures.append(
                f"{key}: as-of date does not match game date."
            )

        if combined_pa <= 0:
            failures.append(
                f"{key}: no career plate appearances saved."
            )

        for batter_id, row in rows.items():
            if not isinstance(row, dict):
                failures.append(
                    f"{key} {batter_id}: invalid batter row."
                )
                continue

            if row.get("as_of_date") != game.get("date"):
                failures.append(
                    f"{key} {batter_id}: incorrect as-of date."
                )

            if "home_runs" not in row:
                failures.append(
                    f"{key} {batter_id}: missing home_runs."
                )

            if "strikeout_rate" not in row:
                failures.append(
                    f"{key} {batter_id}: missing strikeout_rate."
                )

            if "walk_rate" not in row:
                failures.append(
                    f"{key} {batter_id}: missing walk_rate."
                )

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)

    print(
        "\nPASS: career matchup history is saved "
        "with the correct date-aware structure."
    )


if __name__ == "__main__":
    main()
