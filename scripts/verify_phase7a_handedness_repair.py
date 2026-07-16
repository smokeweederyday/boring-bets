#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mlb.offense import fetch_statcast_terminal_pas


def verify_source(day_text: str) -> None:
    rows = fetch_statcast_terminal_pas(day_text)
    print(f"Baseball Savant terminal PAs for {day_text}: {len(rows)}")
    if not rows:
        raise SystemExit(
            "FAIL: Baseball Savant returned no mapped terminal plate appearances. "
            "Send this output before rebuilding."
        )
    sample = rows[0]
    print(
        "Sample:",
        {key: sample.get(key) for key in ("team_id", "location", "pitcher_hand", "event")},
    )


def verify_games(game_id: str) -> None:
    raw = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
    games = raw.get("games", raw) if isinstance(raw, dict) else raw
    game = next((item for item in games if item.get("id") == game_id), None)
    if not game:
        raise SystemExit(f"FAIL: could not find {game_id} in games.json")

    failures: list[str] = []
    print(f"Game: {game_id}")
    for side in ("away", "home"):
        team = game.get(f"{side}_team", {}).get("abbr", side.upper())
        stats = game.get("offense", {}).get(side, {}).get("stats", {})
        hand_values = []
        location_values = []
        print(f"\n{team}")
        for timeframe in ("last_7", "last_30", "season"):
            overall = stats.get(timeframe, {}).get("all", {}).get("AVG", {})
            location = stats.get(timeframe, {}).get(side, {}).get("AVG", {})
            row = (
                overall.get("vs_hand"), overall.get("vs_hand_rank"),
                location.get("vs_hand"), location.get("vs_hand_rank"),
            )
            hand_values.append(row[:2])
            location_values.append(row[2:])
            print(
                f"{timeframe}: vs hand={row[0]} rank={row[1]} | "
                f"{side} vs hand={row[2]} rank={row[3]}"
            )
            if row[0] is None or row[1] is None:
                failures.append(f"{team} {timeframe}: missing all-location handedness value/rank")
            if row[2] is None or row[3] is None:
                failures.append(f"{team} {timeframe}: missing {side} handedness value/rank")
        if len(set(hand_values)) == 1:
            failures.append(f"{team}: all-location handedness value/rank is static across all timeframes")
        if len(set(location_values)) == 1:
            failures.append(f"{team}: {side} handedness value/rank is static across all timeframes")

    cache_path = ROOT / "data" / "cache" / f"mlb-offense-rank-matrix-{game_id[:10]}.json"
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        print("\nCache cutoff:", cache.get("cutoff_date"))
        if cache.get("pregame_cutoff") is not True:
            failures.append("offense cache is not marked as pregame cutoff")
        expected = (datetime.strptime(game_id[:10], "%Y-%m-%d").date()).toordinal() - 1
        cutoff = cache.get("cutoff_date")
        if cutoff:
            actual = datetime.strptime(cutoff, "%Y-%m-%d").date().toordinal()
            if actual != expected:
                failures.append(f"cache cutoff {cutoff} does not exclude selected game date")
    else:
        failures.append(f"missing offense cache {cache_path.name}")

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(" -", failure)
        raise SystemExit(1)
    print("\nPASS: handedness values/ranks are date-bound and the selected game is excluded.")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "source"
    if mode == "source":
        day_text = sys.argv[2] if len(sys.argv) > 2 else "2026-07-15"
        verify_source(day_text)
    elif mode == "games":
        game_id = sys.argv[2] if len(sys.argv) > 2 else "2026-07-16-nym-phi"
        verify_games(game_id)
    else:
        raise SystemExit("Usage: verify_phase7a_handedness_repair.py source [YYYY-MM-DD] | games [GAME_ID]")


if __name__ == "__main__":
    main()
