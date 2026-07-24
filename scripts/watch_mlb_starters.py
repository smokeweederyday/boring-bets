#!/usr/bin/env python3
"""Continuously refresh MLB starters at fast and broad cadences."""

from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"
GAMES_DIR = DATA / "games"
LIVE_DIR = DATA / "live-games"
CACHE = ROOT / ".cache"

WATCH_LOCK = CACHE / "mlb-starter-watch.lock"
EASTERN = ZoneInfo("America/New_York")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Watch live MLB pitcher assignments, immediately enrich today's "
            "changed starters, and periodically refresh upcoming dates."
        )
    )

    parser.add_argument(
        "--fast-interval",
        type=float,
        default=10.0,
        help="Seconds between today's live/enriched pitcher comparisons.",
    )

    parser.add_argument(
        "--broad-interval",
        type=float,
        default=900.0,
        help="Seconds between broader upcoming-starter refreshes.",
    )

    parser.add_argument(
        "--days-ahead",
        type=int,
        default=7,
        help="Upcoming date horizon for the broad refresh.",
    )

    parser.add_argument(
        "--retry-cooldown",
        type=float,
        default=45.0,
        help="Seconds before retrying the same unresolved mismatch.",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Check today's live/enriched pitchers once and exit.",
    )

    return parser.parse_args()


def eastern_today() -> str:
    return datetime.now(EASTERN).date().isoformat()


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    return value if isinstance(value, dict) else None


def game_identity(game: dict[str, Any]) -> tuple[str, str]:
    game_pk = game.get("mlb_game_pk")

    if game_pk not in (None, ""):
        return ("pk", str(game_pk))

    return ("id", str(game.get("id") or ""))


def pitcher_id(pitcher: Any) -> str:
    if not isinstance(pitcher, dict):
        return ""

    value = pitcher.get("id")

    if value in (None, ""):
        return ""

    return str(value)


def pitcher_name(pitcher: Any) -> str:
    if not isinstance(pitcher, dict):
        return ""

    return str(pitcher.get("name") or "").strip()


def pitcher_status(pitcher: Any) -> str:
    if not isinstance(pitcher, dict):
        return "unknown"

    return str(pitcher.get("status") or "unknown").strip().lower()


def pitcher_complete(pitcher: Any) -> bool:
    if not isinstance(pitcher, dict):
        return False

    if not pitcher_id(pitcher):
        return False

    stats = pitcher.get("stats")

    if not isinstance(stats, dict):
        return False

    season = stats.get("season")

    if not isinstance(season, dict):
        return False

    season_all = season.get("all")

    if not isinstance(season_all, dict):
        return False

    last_starts = stats.get("last_starts")

    if not isinstance(last_starts, dict):
        return False

    return all(
        str(count) in last_starts
        for count in (1, 3, 7, 10, 20)
    )


def today_mismatches(target_date: str) -> list[dict[str, str]]:
    live_path = LIVE_DIR / f"{target_date}.json"
    games_path = GAMES_DIR / f"{target_date}.json"

    live_document = load_json(live_path)
    games_document = load_json(games_path)

    if live_document is None or games_document is None:
        return []

    live_games = [
        game
        for game in live_document.get("games", [])
        if isinstance(game, dict)
    ]

    enriched_games = [
        game
        for game in games_document.get("games", [])
        if isinstance(game, dict)
    ]

    enriched_by_key = {
        game_identity(game): game
        for game in enriched_games
    }

    mismatches: list[dict[str, str]] = []

    for live_game in live_games:
        key = game_identity(live_game)
        enriched_game = enriched_by_key.get(key)

        if not enriched_game:
            continue

        live_pitchers = live_game.get("pitchers") or {}
        enriched_pitchers = enriched_game.get("pitchers") or {}

        for side in ("away", "home"):
            live_pitcher = live_pitchers.get(side) or {}
            enriched_pitcher = enriched_pitchers.get(side) or {}

            live_id = pitcher_id(live_pitcher)
            enriched_id = pitcher_id(enriched_pitcher)

            live_name = pitcher_name(live_pitcher) or "Starter TBD"
            enriched_name = pitcher_name(enriched_pitcher) or "Starter TBD"

            live_status = pitcher_status(live_pitcher)
            enriched_status = pitcher_status(enriched_pitcher)

            reason = ""

            if live_id and live_id != enriched_id:
                reason = "pitcher identity changed"

            elif (
                live_id
                and live_id == enriched_id
                and not pitcher_complete(enriched_pitcher)
            ):
                reason = "pitcher snapshot incomplete"

            elif (
                live_id
                and live_id == enriched_id
                and live_name
                and live_name != enriched_name
            ):
                reason = "pitcher name changed"

            elif (
                live_id
                and live_status == "confirmed"
                and enriched_status != "confirmed"
            ):
                reason = "pitcher status upgraded"

            elif (
                not live_id
                and live_status == "unknown"
                and enriched_id
                and enriched_status in {"probable", "confirmed"}
            ):
                reason = "official live feed removed listed pitcher"

            if not reason:
                continue

            mismatches.append(
                {
                    "game": str(
                        enriched_game.get("id")
                        or live_game.get("id")
                        or key[1]
                    ),
                    "side": side,
                    "reason": reason,
                    "live_id": live_id or "TBD",
                    "live_name": live_name,
                    "enriched_id": enriched_id or "TBD",
                    "enriched_name": enriched_name,
                }
            )

    return mismatches


def mismatch_signature(
    mismatches: list[dict[str, str]],
) -> str:
    rows = sorted(
        (
            row["game"],
            row["side"],
            row["reason"],
            row["live_id"],
            row["enriched_id"],
        )
        for row in mismatches
    )

    return json.dumps(
        rows,
        separators=(",", ":"),
    )


def run_refresh(
    target_date: str,
    days_ahead: int,
    label: str,
) -> int:
    command = [
        sys.executable,
        "-u",
        str(SCRIPTS / "refresh_mlb_starters.py"),
        "--date",
        target_date,
        "--days-ahead",
        str(days_ahead),
    ]

    print()
    print(
        f"[{datetime.now(EASTERN).isoformat(timespec='seconds')}] "
        f"{label}"
    )
    print("Command:", " ".join(command))
    sys.stdout.flush()

    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
    )

    if completed.returncode != 0:
        print(
            f"WARNING: starter refresh exited with code "
            f"{completed.returncode}."
        )

    return completed.returncode


def print_mismatches(
    mismatches: list[dict[str, str]],
) -> None:
    print("Live pitcher mismatch detected:")

    for row in mismatches:
        print(
            f"  {row['game']} {row['side']}: "
            f"{row['enriched_name']} ({row['enriched_id']}) "
            f"-> {row['live_name']} ({row['live_id']}) "
            f"[{row['reason']}]"
        )


def acquire_lock():
    CACHE.mkdir(parents=True, exist_ok=True)

    handle = WATCH_LOCK.open("w")

    try:
        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        raise SystemExit(
            "Another MLB starter watcher is already running."
        )

    handle.write(str(Path("/proc/self").resolve()) + "\n")
    handle.flush()

    return handle


def main() -> int:
    args = parse_args()
    lock_handle = acquire_lock()

    # Keep the lock file handle alive for the process lifetime.
    _ = lock_handle

    print("Boring Bets MLB starter watcher")
    print(
        f"Fast today check: every {args.fast_interval:.0f} seconds"
    )
    print(
        f"Broad {args.days_ahead}-day refresh: "
        f"every {args.broad_interval / 60:.0f} minutes"
    )
    print(
        "Changed live pitcher IDs trigger an immediate today-only "
        "snapshot rebuild."
    )
    print(
        "Projected starters remain lower priority than MLB probable "
        "and confirmed assignments."
    )
    sys.stdout.flush()

    last_broad_refresh = 0.0
    last_targeted_signature = ""
    last_targeted_time = 0.0

    while True:
        cycle_started = time.monotonic()
        target_date = eastern_today()

        mismatches = today_mismatches(target_date)

        if mismatches:
            signature = mismatch_signature(mismatches)
            retry_due = (
                signature != last_targeted_signature
                or (
                    cycle_started - last_targeted_time
                    >= args.retry_cooldown
                )
            )

            if retry_due:
                print()
                print_mismatches(mismatches)

                run_refresh(
                    target_date=target_date,
                    days_ahead=0,
                    label=(
                        "Running immediate today-only starter enrichment."
                    ),
                )

                last_targeted_signature = signature
                last_targeted_time = time.monotonic()

                remaining = today_mismatches(target_date)

                if remaining:
                    print(
                        "Today-only refresh completed, but some mismatches "
                        "remain and will be retried after the cooldown."
                    )
                else:
                    print(
                        "PASS: live pitcher assignments and enriched "
                        "snapshots now match."
                    )

        if args.once:
            return 0

        now = time.monotonic()

        if (
            last_broad_refresh == 0.0
            or now - last_broad_refresh >= args.broad_interval
        ):
            run_refresh(
                target_date=target_date,
                days_ahead=max(0, args.days_ahead),
                label=(
                    f"Running broad {args.days_ahead}-day "
                    "starter refresh."
                ),
            )

            last_broad_refresh = time.monotonic()

        elapsed = time.monotonic() - cycle_started
        sleep_seconds = max(
            1.0,
            args.fast_interval - elapsed,
        )

        time.sleep(sleep_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
