#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mlb.schedule import parse_schedule
from update_games import (
    build_days_index,
    load_games_file,
    merge_schedule_game,
    migrate_existing_games,
)

GAMES_FILE = ROOT / "data" / "games.json"
DAYS_FILE = ROOT / "data" / "days.json"


def fetch_schedule_range(start_date: str, end_date: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "sportId": 1,
        "startDate": start_date,
        "endDate": end_date,
        "hydrate": "probablePitcher,venue",
        "gameType": "R",
    })
    request = urllib.request.Request(
        f"https://statsapi.mlb.com/api/v1/schedule?{query}",
        headers={"User-Agent": "Boring Bets/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge the complete MLB regular-season schedule into games.json without deleting enriched data."
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    start_date = args.start or f"{args.season}-03-25"
    end_date = args.end or f"{args.season}-10-01"

    first_date = date.fromisoformat(start_date)
    final_date = date.fromisoformat(end_date)

    schedule_games: list[dict[str, Any]] = []
    chunk_start = first_date

    while chunk_start <= final_date:
        chunk_end = min(
            chunk_start + timedelta(days=13),
            final_date,
        )

        chunk_start_text = chunk_start.isoformat()
        chunk_end_text = chunk_end.isoformat()

        print(
            f"Fetching MLB schedule "
            f"{chunk_start_text} through {chunk_end_text}...",
            flush=True,
        )

        raw = fetch_schedule_range(
            chunk_start_text,
            chunk_end_text,
        )

        chunk_games = parse_schedule(raw)
        schedule_games.extend(chunk_games)

        print(
            f"  Received {len(chunk_games)} games.",
            flush=True,
        )

        chunk_start = chunk_end + timedelta(days=1)

    if not schedule_games:
        raise SystemExit(
            "No MLB regular-season games were returned."
        )

    current = load_games_file()
    migrated = migrate_existing_games(current.get("games", []))
    existing = {game.get("id"): game for game in migrated if game.get("id")}

    existing_by_pk: dict[
        int,
        list[dict[str, Any]],
    ] = {}

    for game in migrated:
        try:
            game_pk = int(
                game.get("mlb_game_pk")
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        existing_by_pk.setdefault(
            game_pk,
            [],
        ).append(game)

    merged_by_id = dict(existing)
    added = 0
    updated = 0

    for schedule_game in schedule_games:
        game_id = schedule_game["id"]

        candidates: list[dict[str, Any]] = []

        direct_match = merged_by_id.get(
            game_id
        )

        if direct_match is not None:
            candidates.append(
                direct_match
            )

        try:
            schedule_pk = int(
                schedule_game.get(
                    "mlb_game_pk"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            schedule_pk = None

        if schedule_pk is not None:
            for candidate in existing_by_pk.get(
                schedule_pk,
                [],
            ):
                if candidate not in candidates:
                    candidates.append(
                        candidate
                    )

        existing_game = (
            max(
                candidates,
                key=lambda game: len(
                    json.dumps(
                        game,
                        sort_keys=True,
                    )
                ),
            )
            if candidates
            else None
        )

        for candidate in candidates:
            previous_id = candidate.get(
                "id"
            )

            if (
                previous_id
                and previous_id != game_id
            ):
                merged_by_id.pop(
                    previous_id,
                    None,
                )

        if existing_game is None:
            added += 1
        else:
            updated += 1

        merged_game = merge_schedule_game(
            existing_game,
            schedule_game,
        )

        merged_by_id[game_id] = (
            merged_game
        )

        if schedule_pk is not None:
            existing_by_pk[
                schedule_pk
            ] = [merged_game]

    games = list(merged_by_id.values())
    games.sort(key=lambda game: (
        game.get("date") or "",
        game.get("game_time") or "",
        game.get("id") or "",
    ))

    current["schema_version"] = "3.9"
    current["schedule_sync"] = {
        "season": args.season,
        "start_date": start_date,
        "end_date": end_date,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "regular_season_games": len(schedule_games),
    }
    current["games"] = games

    GAMES_FILE.write_text(
        json.dumps(
            current,
            ensure_ascii=False,
            separators=(",", ":"),
        ) + "\n",
        encoding="utf-8",
    )
    days_index = build_days_index(
        games
    )

    DAYS_FILE.write_text(
        json.dumps(
            days_index,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    unique_dates = len({game.get("date") for game in schedule_games if game.get("date")})
    print(f"Fetched {len(schedule_games)} MLB regular-season games across {unique_dates} dates.")
    print(f"Added {added} new game shells; refreshed {updated} existing games.")
    print(f"games.json now contains {len(games)} total games across all retained dates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
