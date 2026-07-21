#!/usr/bin/env python3

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

GAME_JS = (
    ROOT / "game.js"
).read_text(encoding="utf-8")

ENGINE_JS = (
    ROOT / "assets/js/sports/mlbEngine.js"
).read_text(encoding="utf-8")

GAME_HTML = (
    ROOT / "game.html"
).read_text(encoding="utf-8")


failures = []


requirements = (
    (
        "away state defaults to recent starts",
        r"awayPitcherStartMode\s*:\s*true",
        GAME_JS,
    ),
    (
        "home state defaults to recent starts",
        r"homePitcherStartMode\s*:\s*true",
        GAME_JS,
    ),
    (
        "away count defaults to seven",
        r"awayPitcherStartCount\s*:\s*7",
        GAME_JS,
    ),
    (
        "home count defaults to seven",
        r"homePitcherStartCount\s*:\s*7",
        GAME_JS,
    ),
    (
        "engine defaults to recent-start mode",
        r"startMode\s*=\s*true",
        ENGINE_JS,
    ),
    (
        "engine count defaults to seven",
        r"startCount\s*=\s*7",
        ENGINE_JS,
    ),
    (
        "game page uses current cache version",
        r'game\.js\?v=phase11e-last7-default1',
        GAME_HTML,
    ),
    (
        "engine import uses current cache version",
        r'mlbEngine\.js\?v=phase11e-last7-default1',
        GAME_JS,
    ),
)


for label, pattern, source in requirements:
    if not re.search(pattern, source):
        failures.append(label)


for forbidden in (
    "awayPitcherStartMode: false",
    "homePitcherStartMode: false",
):
    if forbidden in GAME_JS:
        failures.append(
            f"old disabled default remains: {forbidden}"
        )


print("PITCHER LAST-SEVEN DEFAULT CONTRACT")
print("=" * 39)

if failures:
    for failure in failures:
        print("FAIL:", failure)

    sys.exit(1)


print("PASS: away pitcher opens on Last 7 Starts.")
print("PASS: home pitcher opens on Last 7 Starts.")
print("PASS: engine fallback also uses Last 7 Starts.")
print("PASS: browser cache versions were updated.")
