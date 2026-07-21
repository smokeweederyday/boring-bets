#!/usr/bin/env python3
"""Validate starter coverage and complete pitcher snapshots."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
GAMES_FILE = ROOT / "data" / "games.json"
EASTERN = ZoneInfo("America/New_York")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        default=datetime.now(EASTERN).date().isoformat(),
    )
    parser.add_argument("--days-ahead", type=int, default=7)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    first = date.fromisoformat(args.date)
    end = first + timedelta(days=args.days_ahead)

    payload = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    games: List[Dict[str, Any]] = payload.get("games", [])

    target_games = [
        game
        for game in games
        if first.isoformat() <= str(game.get("date") or "") <= end.isoformat()
    ]

    statuses = Counter()
    known = 0
    complete = 0
    with_last_start_sample = 0
    pending = []
    missing_slots = []
    incomplete = []
    changes = []

    for game in target_games:
        for side in ("away", "home"):
            pitcher = ((game.get("pitchers") or {}).get(side) or {})
            status = str(pitcher.get("status") or "unknown")
            statuses[status] += 1

            if not pitcher.get("id"):
                missing_slots.append(
                    (
                        game.get("date"),
                        game.get("id"),
                        side,
                        pitcher.get("name") or "Starter TBD",
                    )
                )
                continue

            known += 1
            stats = pitcher.get("stats") or {}
            last_starts = stats.get("last_starts")
            structure_complete = (
                isinstance(last_starts, dict)
                and all(str(count) in last_starts for count in (1, 3, 7, 10, 20))
            )
            last_one = (
                ((last_starts or {}).get("1") or {}).get("all") or {}
            )
            if structure_complete:
                complete += 1
                if last_one:
                    with_last_start_sample += 1
            else:
                row = (
                    game.get("date"),
                    game.get("id"),
                    side,
                    pitcher.get("name"),
                    pitcher.get("id"),
                    pitcher.get("snapshot_status"),
                )
                incomplete.append(row)
                if pitcher.get("snapshot_status") == "pending":
                    pending.append(row)

            if pitcher.get("changed_since_last_refresh"):
                changes.append(
                    (
                        game.get("date"),
                        game.get("id"),
                        side,
                        (pitcher.get("previous_pitcher") or {}).get("name"),
                        pitcher.get("name"),
                        pitcher.get("changed_at"),
                    )
                )

    print(f"Date window: {first} through {end}")
    print(f"Games: {len(target_games)}")
    print(f"Starter slots: {len(target_games) * 2}")
    print(f"Status counts: {dict(statuses)}")
    print(f"Known starters: {known}")
    print(f"Complete pitcher snapshots: {complete}/{known}")
    print(f"Pitchers with a prior-start sample: {with_last_start_sample}/{known}")
    print(f"Snapshots pending retry: {len(pending)}")
    print(f"Unknown starter slots: {len(missing_slots)}")
    print(f"Changes flagged this refresh: {len(changes)}")

    if missing_slots:
        print("\nUnknown slots:")
        for row in missing_slots[:60]:
            print(" ", row)

    if incomplete:
        print("\nIncomplete identified starters:")
        for row in incomplete:
            print(" ", row)

    if changes:
        print("\nStarter changes:")
        for row in changes:
            print(" ", row)

    if incomplete:
        print("\nFAIL: identified starters remain without complete snapshot structures.")
        print("Transient pending snapshots will be retried by the watcher.")
        return 1

    print("\nPASS: every identified starter has a complete snapshot structure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
