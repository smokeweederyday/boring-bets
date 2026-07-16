#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

ROOT = Path(__file__).resolve().parents[1]

PLAYS_FILE = ROOT / "data/plays.json"
RESULTS_FILE = ROOT / "data/results.json"
EVALUATIONS_FILE = ROOT / "data/evaluations.json"


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


def prompt_yes_no(label: str, default: bool = True) -> bool:
    default_label = "Y/n" if default else "y/N"

    while True:
        value = input(f"{label} [{default_label}]: ").strip().lower()

        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False

        print("Please enter y or n.")


def prompt_multiline(label: str) -> str:
    print()
    print(label)
    print("Type END on its own line when finished.")

    lines: list[str] = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines).strip()


def choose_result(
    results: list[dict[str, Any]],
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    evaluated_ids = {
        evaluation.get("play_id")
        for evaluation in evaluations
        if evaluation.get("play_id")
        and str(evaluation.get("status") or "").lower() != "pending"
    }

    candidates = [
        result for result in results
        if result.get("play_id")
        and result.get("play_id") not in evaluated_ids
        and str(result.get("status") or "pending").lower() != "pending"
    ]

    if not candidates:
        raise SystemExit("No graded, unevaluated plays found.")

    candidates.sort(
        key=lambda result: (
            result.get("date") or "",
            result.get("game_id") or "",
            result.get("play_id") or "",
        )
    )

    print("Graded plays awaiting evaluation")
    print("-" * 50)

    for index, result in enumerate(candidates, start=1):
        print(
            f"{index}. {result.get('date')} · "
            f"{result.get('play_id')} · "
            f"{str(result.get('status')).upper()} · "
            f"{result.get('units_result')}u"
        )

    while True:
        value = input("Choose play number: ").strip()

        try:
            number = int(value)
        except ValueError:
            print("Enter one of the listed numbers.")
            continue

        if 1 <= number <= len(candidates):
            return candidates[number - 1]

        print("Enter one of the listed numbers.")


def main() -> None:
    plays_payload = load_json(
        PLAYS_FILE,
        {"plays": []},
    )
    results_payload = load_json(
        RESULTS_FILE,
        {"results": []},
    )
    evaluations_payload = load_json(
        EVALUATIONS_FILE,
        {
            "schema_version": "1.0",
            "updated_at": None,
            "evaluations": [],
        },
    )

    plays = plays_payload.get("plays", [])
    results = results_payload.get("results", [])
    evaluations = evaluations_payload.get("evaluations", [])

    if not isinstance(plays, list):
        plays = []
    if not isinstance(results, list):
        results = []
    if not isinstance(evaluations, list):
        evaluations = []

    selected_result = choose_result(results, evaluations)
    play_id = selected_result["play_id"]

    selected_play = next(
        (
            play for play in plays
            if play.get("id") == play_id
        ),
        {},
    )

    good_decision = prompt_yes_no(
        "Was this a good decision",
        default=True,
    )

    would_bet_again = prompt_yes_no(
        "Would you make the bet again",
        default=True,
    )

    decision_quality = input(
        "Decision grade [A+, A, A-, B+, etc.]: "
    ).strip() or None

    model_quality = input(
        "Model/research grade [optional]: "
    ).strip() or None

    variance = input(
        "Variance [low/medium/high]: "
    ).strip().lower() or None

    summary = prompt_multiline(
        "Evaluation summary"
    )

    lessons_text = prompt_multiline(
        "Lessons, one per line"
    )

    lessons = [
        line.strip()
        for line in lessons_text.splitlines()
        if line.strip()
    ]

    reviewed_by = input(
        "Reviewed by [Mark]: "
    ).strip() or "Mark"

    timestamp = datetime.now(timezone.utc).isoformat()
    evaluation_id = (
        selected_play.get("evaluation_id")
        or f"evaluation-{play_id}"
    )

    evaluation = {
        "id": evaluation_id,
        "play_id": play_id,
        "result_id": selected_result.get("id"),
        "game_id": selected_result.get("game_id"),
        "date": selected_result.get("date"),
        "sport": selected_result.get("sport"),
        "status": "completed",
        "decision_quality": decision_quality,
        "model_quality": model_quality,
        "good_decision": good_decision,
        "would_bet_again": would_bet_again,
        "variance": variance,
        "summary": summary,
        "lessons": lessons,
        "reviewed_by": reviewed_by,
        "reviewed_at": timestamp,
    }

    by_play = {
        item.get("play_id"): item
        for item in evaluations
        if item.get("play_id")
    }
    by_play[play_id] = evaluation

    evaluations_payload["schema_version"] = "1.0"
    evaluations_payload["updated_at"] = timestamp
    evaluations_payload["evaluations"] = sorted(
        by_play.values(),
        key=lambda item: (
            item.get("date") or "",
            item.get("game_id") or "",
            item.get("play_id") or "",
        ),
    )
    save_json(EVALUATIONS_FILE, evaluations_payload)

    for play in plays:
        if play.get("id") == play_id:
            play["evaluation_id"] = evaluation_id

    plays_payload["updated_at"] = timestamp
    plays_payload["plays"] = plays
    save_json(PLAYS_FILE, plays_payload)

    for result in results:
        if result.get("play_id") == play_id:
            result["evaluation_id"] = evaluation_id

    results_payload["updated_at"] = timestamp
    results_payload["results"] = results
    save_json(RESULTS_FILE, results_payload)

    print()
    print("EVALUATION COMPLETE")
    print(f"Play: {selected_play.get('play') or play_id}")
    print(
        "Decision: "
        + ("GOOD" if good_decision else "BAD")
    )


if __name__ == "__main__":
    main()
