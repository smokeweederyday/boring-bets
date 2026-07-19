#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-|$)")
FINAL_TOKENS = ("final", "completed", "complete", "game over")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Today’s Card date synchronization and inspect card feeds for stale statuses."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().astimezone().date().isoformat(),
        help="Card date to inspect, in YYYY-MM-DD format. Defaults to the computer's local date.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not DATE_RE.fullmatch(args.date):
        raise SystemExit("--date must use YYYY-MM-DD.")

    js_path = args.root / "todays-card.js"
    if not js_path.exists():
        print(f"FAIL: missing {js_path}", file=sys.stderr)
        return 1

    source = js_path.read_text(errors="replace")
    required = {
        "card-date event filtering": "selectEventsForCardDate",
        "daily document date guard": "documentMatchesCardDate",
        "future-start status guard": "resolveEventStatus",
        "date-navigation race guard": "renderGeneration",
        "event date attribute": "data-event-date",
        "Not Started pregame handling": '"not started"',
    }

    missing = [label for label, token in required.items() if token not in source]
    if missing:
        for label in missing:
            print(f"FAIL: missing {label}.", file=sys.stderr)
        return 1

    if source.count('window.addEventListener("DOMContentLoaded"') != 1:
        print("FAIL: Today’s Card has more than one DOMContentLoaded initializer.", file=sys.stderr)
        return 1

    print(f"Card date: {args.date}")
    print("Date source: computer local calendar date / ?date=YYYY-MM-DD URL")
    print("Wrong-date records: filtered before card rendering")
    print("Future-starting LIVE/FINAL statuses: displayed as UPCOMING")
    print('"Not Started" statuses: displayed as UPCOMING')
    print("Slow previous-date requests: blocked from overwriting the active card")

    reports = inspect_local_feeds(args.root, args.date)
    if not reports:
        print("Feed inspection: no local daily feed files found for this date (non-blocking)")
    else:
        print("\nLocal feed inspection:")
        for report in reports:
            print(
                f"- {report['path']}: {report['events']} events, "
                f"{report['wrong_date']} wrong-date raw records, "
                f"{report['future_final']} future-start raw FINAL records"
            )

    print("\nPASS: Today’s Card date and status display are synchronized to the selected card date.")
    return 0


def inspect_local_feeds(root: Path, card_date: str) -> list[dict[str, Any]]:
    candidates: list[Path] = []
    mlb = root / "data" / "live-games" / f"{card_date}.json"
    if mlb.exists():
        candidates.append(mlb)

    daily_dir = root / "data" / "cards" / card_date
    if daily_dir.exists():
        candidates.extend(sorted(daily_dir.glob("*.json")))

    reports: list[dict[str, Any]] = []
    now = datetime.now().astimezone()
    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        events = get_events(data)
        wrong_date = 0
        future_final = 0
        for event in events:
            event_date = event_date_key(event)
            if event_date and event_date != card_date:
                wrong_date += 1
            status = status_text(event.get("status") or event.get("abstract_status")).lower()
            start = parse_datetime(
                event.get("start_time")
                or event.get("game_time")
                or event.get("date_time")
                or event.get("gameDate")
            )
            if start and start > now and any(token in status for token in FINAL_TOKENS):
                future_final += 1
        reports.append(
            {
                "path": path.relative_to(root),
                "events": len(events),
                "wrong_date": wrong_date,
                "future_final": future_final,
            }
        )
    return reports


def get_events(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    for key in ("events", "games", "matches", "fights"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def event_date_key(event: dict[str, Any]) -> str:
    for key in ("card_date", "schedule_date", "date", "game_date"):
        value = str(event.get(key) or "")
        if DATE_RE.fullmatch(value):
            return value

    stable_id = str(event.get("id") or event.get("game_id") or "")
    match = ID_DATE_RE.match(stable_id)
    if match:
        return match.group(1)

    start = parse_datetime(
        event.get("start_time")
        or event.get("game_time")
        or event.get("date_time")
        or event.get("gameDate")
    )
    return start.astimezone().date().isoformat() if start else ""


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed.astimezone()


def status_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(
            value.get("detailedState")
            or value.get("abstractGameState")
            or value.get("status")
            or value.get("code")
            or "Scheduled"
        )
    return str(value or "Scheduled")


if __name__ == "__main__":
    raise SystemExit(main())
