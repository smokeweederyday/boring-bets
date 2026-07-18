#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GAMES_FILE = ROOT / "data" / "games.json"
META_FILE = ROOT / "data" / "games-meta.json"
DATE_DIR = ROOT / "data" / "games"


def sort_key(game: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(game.get("date") or ""),
        str(game.get("game_time") or ""),
        str(game.get("id") or ""),
    )


def main() -> None:
    if not META_FILE.exists():
        raise SystemExit(
            "Missing data/games-meta.json."
        )

    metadata = json.loads(
        META_FILE.read_text(
            encoding="utf-8"
        )
    )

    existing_payload = {}

    if GAMES_FILE.exists():
        existing_payload = json.loads(
            GAMES_FILE.read_text(
                encoding="utf-8"
            )
        )

    games: list[dict[str, Any]] = []

    for path in sorted(
        DATE_DIR.glob("*.json")
    ):
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        date_games = payload.get(
            "games",
            [],
        )

        if not isinstance(date_games, list):
            raise SystemExit(
                f"{path} does not contain a games list."
            )

        games.extend(
            game
            for game in date_games
            if isinstance(game, dict)
        )

    games.sort(key=sort_key)

    ids = [
        game.get("id")
        for game in games
        if game.get("id")
    ]

    if len(ids) != len(set(ids)):
        raise SystemExit(
            "Duplicate game IDs found while assembling."
        )

    rebuilt = dict(metadata)
    rebuilt["games"] = games

    old_games = {
        game.get("id"): game
        for game in existing_payload.get(
            "games",
            [],
        )
        if isinstance(game, dict)
        and game.get("id")
    }

    new_games = {
        game.get("id"): game
        for game in games
        if game.get("id")
    }

    old_metadata = {
        key: value
        for key, value in existing_payload.items()
        if key != "games"
    }

    print(
        "Existing games match:",
        old_games == new_games,
    )
    print(
        "Existing metadata matches:",
        old_metadata == metadata,
    )

    GAMES_FILE.write_text(
        json.dumps(
            rebuilt,
            ensure_ascii=False,
            separators=(",", ":"),
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"Assembled {len(games)} games."
    )
    print(
        "Master size:",
        f"{GAMES_FILE.stat().st_size / 1024 / 1024:.2f} MB",
    )


if __name__ == "__main__":
    main()
