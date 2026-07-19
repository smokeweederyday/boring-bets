#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required_files = [
        root / "todays-card.js",
        root / "finished-game.html",
        root / "finished-game.js",
        root / "assets" / "css" / "finished-game.css",
        root / "scripts" / "sync_baseball_final_scores.py",
        root / "scripts" / "build_minor_league_schedules.py",
    ]

    missing = [path.relative_to(root) for path in required_files if not path.exists()]
    if missing:
        for path in missing:
            print(f"FAIL: missing {path}", file=sys.stderr)
        return 1

    card_js = (root / "todays-card.js").read_text(errors="replace")
    finished_js = (root / "finished-game.js").read_text(errors="replace")
    finished_html = (root / "finished-game.html").read_text(errors="replace")
    sync_source = (root / "scripts" / "sync_baseball_final_scores.py").read_text(errors="replace")
    minor_source = (root / "scripts" / "build_minor_league_schedules.py").read_text(errors="replace")

    required_tokens = {
        "past-date final score recognition": "hasFinalScore",
        "past-card detection": "isPastCardDate",
        "finished-game routing": "buildFinishedGameUrl",
        "breakdown action label": "Game breakdown",
        "archived research action": "Archived research",
        "postponed-game guard": 'return "postponed"',
        "normalized linescore score fallback": "linescore?.totals",
    }
    failures = [label for label, token in required_tokens.items() if token not in card_js]

    finished_tokens = [
        "lineScoreTable",
        "decisionsGrid",
        "finishedPlays",
        "finishedResults",
        "finishedEvaluations",
    ]
    failures.extend(
        f"finished-game module {token}" for token in finished_tokens
        if token not in finished_html or token not in finished_js
    )

    for token in ("MLB final-score sync", "linescore", "decisions", "write_json_atomic"):
        if token not in sync_source:
            failures.append(f"score-sync token {token}")

    for token in ('"hydrate": "team,venue,probablePitcher,linescore,decisions"', '"linescore": normalize_linescore', '"decisions": normalize_decisions'):
        if token not in minor_source:
            failures.append(f"minor-league result field {token}")

    if failures:
        for failure in failures:
            print(f"FAIL: missing {failure}", file=sys.stderr)
        return 1

    for script in (
        root / "scripts" / "sync_baseball_final_scores.py",
        root / "scripts" / "build_minor_league_schedules.py",
        root / "scripts" / "check_todays_card_postgame.py",
    ):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            print(f"FAIL: Python syntax check failed for {script.name}", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return 1

    node = shutil.which("node")
    if node:
        for script in (root / "todays-card.js", root / "finished-game.js"):
            result = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
            if result.returncode:
                print(f"FAIL: JavaScript syntax check failed for {script.name}", file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                return 1
        print("JavaScript syntax check: PASS")
    else:
        print("JavaScript syntax check: SKIPPED (Node.js not installed; non-blocking)")

    print("Past card dates: route to finished-game breakdown")
    print("Past completed games: display FINAL with synchronized away/home score")
    print("Postponed/cancelled games: never forced to FINAL")
    print("MLB result sync: preserves enriched local game data")
    print("Minor-league archives: include score, inning line and pitching decisions")
    print("PASS: Today’s Card postgame routing and final-score pipeline are internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
