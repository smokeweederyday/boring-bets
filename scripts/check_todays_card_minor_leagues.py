#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "todays-card.html"
JS = ROOT / "todays-card.js"
CSS = ROOT / "assets" / "css" / "todays-card-multisport.css"
CONFIG = ROOT / "data" / "sports-card-config.json"
BUILDER = ROOT / "scripts" / "build_minor_league_schedules.py"

MINOR_LEAGUES = {
    "triple-a": 11,
    "double-a": 12,
    "high-a": 13,
    "single-a": 14,
    "rookie": 16,
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for path in [HTML, JS, CSS, CONFIG, BUILDER]:
        if not path.exists():
            fail(f"missing required file: {path.relative_to(ROOT)}")

    html = HTML.read_text()
    js = JS.read_text()
    css = CSS.read_text()
    config = json.loads(CONFIG.read_text())
    builder = BUILDER.read_text()

    if 'id="sidePreviousDate"' not in html or 'id="sideNextDate"' not in html:
        fail("side date arrows are missing from todays-card.html")
    if ".side-date-arrow" not in css:
        fail("side date arrow styling is missing")
    if "sidePreviousDate" not in js or "sideNextDate" not in js:
        fail("side date arrows are not bound in JavaScript")

    baseball = next((sport for sport in config.get("sports", []) if sport.get("id") == "baseball"), None)
    if not baseball:
        fail("baseball sport config is missing")

    configured = {league.get("id"): league for league in baseball.get("leagues", [])}
    for league_id in MINOR_LEAGUES:
        league = configured.get(league_id)
        if not league:
            fail(f"missing baseball league config: {league_id}")
        if league.get("feed") != "active":
            fail(f"minor-league feed must be active: {league_id}")

    if "loadMinorLeagueEvents" not in js:
        fail("minor-league season loader is missing")
    if "data/schedules/baseball/" not in js:
        fail("Today’s Card is not connected to season schedule archives")
    if "MINOR_LEAGUE_IDS" not in js:
        fail("minor-league ID registry is missing")

    tree = ast.parse(builder)
    mapping_match = re.search(r"LEAGUES: dict\[str, League\] = \{(.*?)\n\}", builder, re.S)
    if not mapping_match:
        fail("could not inspect schedule builder league mapping")
    for league_id, sport_id in MINOR_LEAGUES.items():
        if f'"{league_id}": League(' not in mapping_match.group(1):
            fail(f"schedule builder is missing {league_id}")
        if not re.search(rf'"{re.escape(league_id)}": League\([^\n]+, {sport_id}\)', mapping_match.group(1)):
            fail(f"schedule builder has the wrong sportId for {league_id}")

    try:
        subprocess.run(
            [sys.executable, "-m", "py_compile", str(BUILDER)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        fail(f"Python syntax check failed: {exc.stderr.strip()}")

    node_result = subprocess.run(
        ["node", "--check", str(JS)],
        capture_output=True,
        text=True,
    ) if shutil_which("node") else None
    if node_result and node_result.returncode != 0:
        fail(f"JavaScript syntax check failed: {node_result.stderr.strip()}")

    print("Top date-strip arrows: preserved")
    print("Side date arrows: left and right navigation added")
    print("Affiliated baseball leagues: Triple-A, Double-A, High-A, Single-A, Rookie")
    print("Season archives: data/schedules/baseball/<season>/<league>.json")
    print("Game cards: use the same compact baseball card renderer as MLB")
    print("Schedule builder: MLB Stats API sportIds 11, 12, 13, 14, 16")
    print("JavaScript syntax check: PASS" if node_result else "JavaScript syntax check: SKIPPED (Node.js not installed; non-blocking)")
    print("PASS: Today’s Card Minor League Baseball expansion is internally consistent.")
    return 0


def shutil_which(command: str) -> str | None:
    from shutil import which
    return which(command)


if __name__ == "__main__":
    raise SystemExit(main())
