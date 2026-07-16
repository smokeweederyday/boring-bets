#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

ROOT = Path(__file__).resolve().parents[1]

PLAYS_FILE = ROOT / "data/plays.json"
TODAYS_CARD_FILE = ROOT / "data/todays-card.json"
RESULTS_FILE = ROOT / "data/results.json"

VALID_RESULTS = {"win", "loss", "push", "void"}


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise SystemExit(f"Could not read {path.name}: {error}")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def choose_play(plays: list[dict[str, Any]]) -> dict[str, Any]:
    pending = [
        play for play in plays
        if str(play.get("result") or "pending").lower() == "pending"
    ]

    if not pending:
        raise SystemExit("No pending plays found.")

    pending.sort(
        key=lambda play: (
            play.get("date") or "",
            play.get("game_id") or "",
            play.get("id") or "",
        )
    )

    print("Pending plays")
    print("-" * 50)

    for index, play in enumerate(pending, start=1):
        print(
            f"{index}. {play.get('date')} · "
            f"{play.get('play')} · "
            f"{play.get('odds')} · "
            f"{play.get('units')}u"
        )

    while True:
        value = input("Choose play number: ").strip()

        try:
            number = int(value)
        except ValueError:
            print("Enter one of the listed numbers.")
            continue

        if 1 <= number <= len(pending):
            return pending[number - 1]

        print("Enter one of the listed numbers.")


def american_profit(odds: str, risk: float) -> float:
    cleaned = str(odds).strip().replace("+", "")

    try:
        number = float(cleaned)
    except ValueError:
        raise SystemExit(
            f"Cannot calculate units from odds: {odds}"
        )

    if number > 0:
        return risk * (number / 100.0)

    if number < 0:
        return risk * (100.0 / abs(number))

    raise SystemExit("Odds cannot be zero.")


def calculate_units_result(
    result: str,
    odds: str,
    units: float,
) -> float:
    if result == "win":
        return round(american_profit(odds, units), 4)

    if result == "loss":
        return round(-units, 4)

    return 0.0


def update_record_list(
    records: list[dict[str, Any]],
    record_id: str,
    updates: dict[str, Any],
) -> list[dict[str, Any]]:
    output = []

    for record in records:
        if record.get("id") == record_id:
            updated = dict(record)
            updated.update(updates)
            output.append(updated)
        else:
            output.append(record)

    return output


def main() -> None:
    plays_payload = load_json(
        PLAYS_FILE,
        {
            "schema_version": "1.2",
            "updated_at": None,
            "plays": [],
        },
    )

    plays = plays_payload.get("plays", [])
    if not isinstance(plays, list):
        plays = []

    selected = choose_play(plays)

    while True:
        result = input(
            "Result [win/loss/push/void]: "
        ).strip().lower()

        if result in VALID_RESULTS:
            break

        print("Enter win, loss, push, or void.")

    final_score = input(
        "Final score, for example NYM 4, PHI 2: "
    ).strip()

    closing_odds = input(
        "Closing odds [optional]: "
    ).strip() or None

    closing_line = input(
        "Closing line [optional]: "
    ).strip() or None

    units = float(selected.get("units") or 0)
    units_result = calculate_units_result(
        result,
        str(selected.get("odds") or ""),
        units,
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    result_id = selected.get("result_id") or f"result-{selected['id']}"

    updates = {
        "result": result,
        "units_result": units_result,
        "final_score": final_score or None,
        "graded_at": timestamp,
        "closing_odds": closing_odds,
        "closing_line": closing_line,
        "result_id": result_id,
    }

    plays_payload["updated_at"] = timestamp
    plays_payload["plays"] = update_record_list(
        plays,
        selected["id"],
        updates,
    )
    save_json(PLAYS_FILE, plays_payload)

    card_payload = load_json(
        TODAYS_CARD_FILE,
        {
            "schema_version": "1.2",
            "updated_at": None,
            "plays": [],
        },
    )

    card_plays = card_payload.get("plays", [])
    if isinstance(card_plays, list):
        card_payload["updated_at"] = timestamp
        card_payload["plays"] = update_record_list(
            card_plays,
            selected["id"],
            updates,
        )
        save_json(TODAYS_CARD_FILE, card_payload)

    results_payload = load_json(
        RESULTS_FILE,
        {
            "schema_version": "1.0",
            "updated_at": None,
            "results": [],
        },
    )

    results = results_payload.get("results", [])
    if not isinstance(results, list):
        results = []

    result_record = {
        "id": result_id,
        "play_id": selected["id"],
        "game_id": selected.get("game_id"),
        "date": selected.get("date"),
        "sport": selected.get("sport"),
        "status": result,
        "units_risked": units,
        "units_result": units_result,
        "opening_odds": selected.get("odds"),
        "closing_odds": closing_odds,
        "closing_line": closing_line,
        "final_score": final_score or None,
        "graded_at": timestamp,
        "evaluation_id": selected.get("evaluation_id"),
    }

    existing = {
        item.get("play_id"): item
        for item in results
        if item.get("play_id")
    }
    existing[selected["id"]] = result_record

    results_payload["schema_version"] = "1.0"
    results_payload["updated_at"] = timestamp
    results_payload["results"] = sorted(
        existing.values(),
        key=lambda item: (
            item.get("date") or "",
            item.get("game_id") or "",
            item.get("play_id") or "",
        ),
    )
    save_json(RESULTS_FILE, results_payload)

    sign = "+" if units_result > 0 else ""

    print()
    print("GRADE COMPLETE")
    print(f"{selected.get('play')}: {result.upper()}")
    print(f"Units: {sign}{units_result:.2f}")


if __name__ == "__main__":
    main()
