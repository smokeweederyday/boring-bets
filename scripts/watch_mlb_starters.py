#!/usr/bin/env python3
"""Continuously run the fast Boring Bets MLB starter refresh."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
CACHE = ROOT / "data" / "cache"
WATCH_LOCK = CACHE / "mlb-starter-watch.lock"
EASTERN = ZoneInfo("America/New_York")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch MLB starter assignments and refresh changed pitchers."
    )
    parser.add_argument("--interval-minutes", type=float, default=3.0)
    parser.add_argument("--days-ahead", type=int, default=7)
    parser.add_argument("--no-projections", action="store_true")
    parser.add_argument("--skip-card-data", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_lock() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if WATCH_LOCK.exists():
        try:
            payload = json.loads(WATCH_LOCK.read_text(encoding="utf-8"))
            pid = int(payload.get("pid"))
        except Exception:
            pid = 0
        if pid and process_exists(pid):
            raise SystemExit(
                f"Starter watcher is already running with PID {pid}.\n"
                f"Lock: {WATCH_LOCK}"
            )
        WATCH_LOCK.unlink()
    WATCH_LOCK.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "started_at": datetime.now(EASTERN).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def release_lock() -> None:
    try:
        WATCH_LOCK.unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    args = parse_args()
    if args.interval_minutes < 1:
        raise SystemExit("The minimum watcher interval is 1 minute.")
    if args.days_ahead < 0 or args.days_ahead > 14:
        raise SystemExit("--days-ahead must be between 0 and 14.")

    acquire_lock()
    print("Boring Bets MLB starter watcher")
    print("Press Control-C to stop.")
    print(
        "Projected starters are labeled rotation inferences; "
        "MLB probable and confirmed starters override them."
    )

    try:
        cycle = 0
        while True:
            cycle += 1
            now = datetime.now(EASTERN)
            command = [
                sys.executable,
                "-u",
                str(SCRIPTS / "refresh_mlb_starters.py"),
                "--date",
                now.date().isoformat(),
                "--days-ahead",
                str(args.days_ahead),
            ]
            if args.no_projections:
                command.append("--no-projections")
            if args.skip_card_data:
                command.append("--skip-card-data")

            print(
                f"\n=== Starter cycle {cycle} · "
                f"{now.strftime('%Y-%m-%d %I:%M:%S %p %Z')} ===",
                flush=True,
            )
            completed = subprocess.run(command, cwd=str(ROOT), check=False)
            if completed.returncode != 0:
                print(
                    f"WARNING: starter refresh exited with code "
                    f"{completed.returncode}. The watcher will retry.",
                    file=sys.stderr,
                    flush=True,
                )

            if args.once:
                break

            sleep_seconds = max(60.0, args.interval_minutes * 60.0)
            print(f"Next starter check in {sleep_seconds / 60:.0f} minutes.")
            try:
                time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                break
    finally:
        release_lock()

    print("Starter watcher stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
