#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

CHECKS = {
    "data/games.json": "games",
    "data/articles.json": "articles",
    "data/plays.json": "plays",
    "data/results.json": "results",
    "data/evaluations.json": "evaluations",
    "data/todays-card.json": "plays",
}


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise RuntimeError(str(error))


def main() -> None:
    failures = 0

    print("BORING BETS — SPRINT A CHECK")
    print("=" * 44)

    for relative, collection in CHECKS.items():
        path = ROOT / relative

        if not path.exists():
            print(f"FAIL  {relative} is missing")
            failures += 1
            continue

        try:
            payload = load(path)
        except RuntimeError as error:
            print(f"FAIL  {relative} is invalid JSON: {error}")
            failures += 1
            continue

        records = payload.get(collection, [])

        if not isinstance(records, list):
            print(
                f"FAIL  {relative} has no list named {collection}"
            )
            failures += 1
            continue

        print(
            f"PASS  {relative}: {len(records)} record(s)"
        )

    print()
    if failures:
        print(f"{failures} check(s) failed.")
        sys.exit(1)

    print("All Sprint A data files passed.")


if __name__ == "__main__":
    main()
