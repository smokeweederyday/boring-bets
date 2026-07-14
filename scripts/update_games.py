#!/usr/bin/env python3

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import json
import sys

from mlb.schedule import (
    fetch_schedule,
    parse_schedule,
)


ROOT = Path(__file__).resolve().parents[1]
GAMES_FILE = ROOT / "data/games.json"


def load_games_file() -> dict[str, Any]:
    if not GAMES_FILE.exists():
        return {
            "schema_version": "2.2",
            "default_controls": {
                "timeframe": "last_30",
                "location": "all",
            },
            "games": [],
        }

    return json.loads(
        GAMES_FILE.read_text(encoding="utf-8")
    )


def merge_schedule_game(
    existing: dict[str, Any] | None,
    schedule_game: dict[str, Any],
) -> dict[str, Any]:
    """
    Update schedule-controlled fields while preserving
    existing research, statistics, notes and editorial data.
    """

    game = dict(existing or {})

    game["id"] = schedule_game["id"]
    game["mlb_game_pk"] = schedule_game.get("mlb_game_pk")
    game["date"] = schedule_game.get("date")
    game["game_time"] = schedule_game.get("game_time")
    game["sport"] = "MLB"
    game["status"] = schedule_game.get("status", "scheduled")
    game["venue"] = schedule_game.get("venue", {})
    game["away_team"] = schedule_game.get("away_team", {})
    game["home_team"] = schedule_game.get("home_team", {})

    game.setdefault(
        "controls",
        {
            "default_timeframe": "last_30",
            "default_location": "all",
        },
    )

    existing_pitchers = game.get("pitchers", {})

    game["pitchers"] = {
        "away": merge_pitcher(
            existing_pitchers.get("away"),
            schedule_game
            .get("pitchers", {})
            .get("away", {}),
        ),
        "home": merge_pitcher(
            existing_pitchers.get("home"),
            schedule_game
            .get("pitchers", {})
            .get("home", {}),
        ),
    }

    game.setdefault("offense", {})
    game.setdefault("lineups", {})
    game.setdefault("pitcher_vs_lineup", {})
    game.setdefault("bullpens", {})
    game.setdefault("weather", {})
    game.setdefault("market", {})
    game.setdefault("injuries", [])
    game.setdefault("notes", "")

    game["last_updated"] = datetime.now(
        timezone.utc
    ).isoformat()

    return game


def merge_pitcher(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    pitcher = dict(existing or {})

    incoming_id = incoming.get("id")
    existing_id = pitcher.get("id")

    # If MLB names a different starter, preserve the old
    # record only when the incoming pitcher is still TBD.
    if incoming_id and incoming_id != existing_id:
        pitcher = {}

    pitcher["id"] = incoming_id
    pitcher["name"] = incoming.get(
        "name",
        "Starter TBD",
    )
    pitcher["status"] = incoming.get(
        "status",
        "unknown",
    )

    pitcher.setdefault("age", None)
    pitcher.setdefault("throws", None)
    pitcher.setdefault("profile_url", "#")
    pitcher.setdefault(
        "stats",
        {
            "last_7": {
                "all": {},
                "home": {},
                "away": {},
            },
            "last_30": {
                "all": {},
                "home": {},
                "away": {},
            },
            "season": {
                "all": {},
                "home": {},
                "away": {},
            },
            "vs_lhh": {},
            "vs_rhh": {},
        },
    )

    return pitcher


def main() -> None:
    target_date = (
        sys.argv[1]
        if len(sys.argv) > 1
        else date.today().isoformat()
    )

    current = load_games_file()
    existing_games = {
        game["id"]: game
        for game in current.get("games", [])
        if game.get("id")
    }

    raw_schedule = fetch_schedule(target_date)
    schedule_games = parse_schedule(raw_schedule)

    merged_games = []

    for schedule_game in schedule_games:
        existing = existing_games.get(
            schedule_game["id"]
        )

        merged_games.append(
            merge_schedule_game(
                existing,
                schedule_game,
            )
        )

    # Preserve games from other dates.
    other_dates = [
        game
        for game in current.get("games", [])
        if game.get("date") != target_date
    ]

    current["games"] = (
        other_dates + merged_games
    )

    current["games"].sort(
        key=lambda game: (
            game.get("date", ""),
            game.get("game_time", ""),
        )
    )

    GAMES_FILE.write_text(
        json.dumps(
            current,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"Updated {len(merged_games)} MLB game(s) "
        f"for {target_date}."
    )

    print(
        f"games.json now contains "
        f"{len(current['games'])} total game(s)."
    )


if __name__ == "__main__":
    main()