#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GAMES_FILE = ROOT / "data" / "games.json"
DATE_DIR = ROOT / "data" / "games"
INDEX_FILE = ROOT / "data" / "games-index.json"
META_FILE = ROOT / "data" / "games-meta.json"


def write_compact(path: Path, payload: Any) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ) + "\n",
        encoding="utf-8",
    )


def team_summary(team: Any) -> dict[str, Any]:
    team = team if isinstance(team, dict) else {}

    return {
        key: team.get(key)
        for key in (
            "team_id",
            "abbr",
            "name",
        )
        if team.get(key) is not None
    }


def venue_summary(venue: Any) -> dict[str, Any]:
    venue = venue if isinstance(venue, dict) else {}

    return {
        key: venue.get(key)
        for key in (
            "id",
            "name",
            "city",
            "state",
            "timezone",
            "latitude",
            "longitude",
        )
        if venue.get(key) is not None
    }


def index_game(game: dict[str, Any]) -> dict[str, Any]:
    result = {
        key: game.get(key)
        for key in (
            "id",
            "date",
            "game_time",
            "sport",
            "status",
            "mlb_game_pk",
            "game_number",
            "doubleheader",
        )
        if game.get(key) is not None
    }

    result["away_team"] = team_summary(
        game.get("away_team")
    )
    result["home_team"] = team_summary(
        game.get("home_team")
    )
    result["venue"] = venue_summary(
        game.get("venue")
    )

    return result


def sort_key(game: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(game.get("date") or ""),
        str(game.get("game_time") or ""),
        str(game.get("id") or ""),
    )


def main() -> None:
    payload = json.loads(
        GAMES_FILE.read_text(
            encoding="utf-8"
        )
    )

    games = payload.get("games", [])

    if not isinstance(games, list):
        raise SystemExit(
            "data/games.json does not contain a games list."
        )

    by_date: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for game in games:
        if not isinstance(game, dict):
            continue

        game_date = game.get("date")

        if game_date:
            by_date[str(game_date)].append(
                game
            )

    DATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    expected_files: set[Path] = set()

    for game_date, date_games in sorted(
        by_date.items()
    ):
        date_games.sort(key=sort_key)

        output_path = (
            DATE_DIR / f"{game_date}.json"
        )
        expected_files.add(output_path)

        write_compact(
            output_path,
            {
                "schema_version":
                    payload.get(
                        "schema_version"
                    ),
                "updated_at":
                    payload.get(
                        "updated_at"
                    ),
                "date": game_date,
                "default_controls":
                    payload.get(
                        "default_controls",
                        {},
                    ),
                "games": date_games,
            },
        )

    removed = 0

    for existing_path in DATE_DIR.glob(
        "*.json"
    ):
        if existing_path not in expected_files:
            existing_path.unlink()
            removed += 1

    metadata = {
        key: value
        for key, value in payload.items()
        if key != "games"
    }

    write_compact(
        META_FILE,
        metadata,
    )

    indexed_games = [
        index_game(game)
        for game in sorted(
            games,
            key=sort_key,
        )
        if isinstance(game, dict)
    ]

    write_compact(
        INDEX_FILE,
        {
            "schema_version":
                payload.get(
                    "schema_version"
                ),
            "updated_at":
                payload.get(
                    "updated_at"
                ),
            "games": indexed_games,
        },
    )

    date_size = sum(
        path.stat().st_size
        for path in expected_files
    )

    print(
        f"Wrote {len(expected_files)} date files."
    )
    print(
        f"Wrote {len(indexed_games)} games "
        "to games-index.json."
    )
    print(
        "Date files total:",
        f"{date_size / 1024 / 1024:.2f} MB",
    )
    print(
        "Metadata size:",
        f"{META_FILE.stat().st_size / 1024:.2f} KB",
    )
    print(
        "Index size:",
        f"{INDEX_FILE.stat().st_size / 1024 / 1024:.2f} MB",
    )
    print(
        f"Removed {removed} stale date files."
    )


if __name__ == "__main__":
    main()
