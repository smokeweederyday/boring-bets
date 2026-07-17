#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

FILES = {
    "articles.json": {
        "schema_version": "1.0",
        "updated_at": None,
        "articles": [],
    },
    "plays.json": {
        "schema_version": "1.2",
        "updated_at": None,
        "plays": [],
    },
    "results.json": {
        "schema_version": "1.0",
        "updated_at": None,
        "results": [],
    },
    "evaluations.json": {
        "schema_version": "1.0",
        "updated_at": None,
        "evaluations": [],
    },
}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)

    created = []

    for name, default in FILES.items():
        path = DATA / name

        if path.exists():
            print(f"Kept existing data/{name}")
            continue

        path.write_text(
            json.dumps(default, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(name)
        print(f"Created data/{name}")

    print()
    print("Sprint A data foundation is ready.")

    if created:
        print("Created: " + ", ".join(created))


if __name__ == "__main__":
    main()
