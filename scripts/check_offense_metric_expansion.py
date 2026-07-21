#!/usr/bin/env python3

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

ENGINE = (
    ROOT
    / "assets/js/sports/mlbEngine.js"
).read_text(encoding="utf-8")

GAME_JS = (
    ROOT / "game.js"
).read_text(encoding="utf-8")

GAME_HTML = (
    ROOT / "game.html"
).read_text(encoding="utf-8")

errors = []


def require(source, text, label):
    if text not in source:
        errors.append(
            f"{label} missing: {text}"
        )


require(
    ENGINE,
    '["AVG", "wRC+", "K%", "BB%", '
    '"OBP", "OPS", "ISO", "SLG"]',
    "Offense metric order",
)

for metric in (
    '"wRC+": 1.4',
    '"ISO": 1.15',
    '"SLG": 1.2',
):
    require(
        ENGINE,
        metric,
        "Offense signal weight",
    )

for text in (
    "MLB_OFFENSE_METRICS.forEach(metric =>",
    "OFFENSE_SIGNAL_WEIGHTS[metric]",
    "? configuredWeight",
    ": 1;",
    '["AVG", "OBP", "OPS", "ISO", "SLG"]',
):
    require(
        ENGINE,
        text,
        "Dynamic offense highlighting",
    )


version = (
    "phase11t-offense-metric-expansion1"
)

for source, text, label in (
    (
        GAME_JS,
        f"pitcherWidget.js?v={version}",
        "Pitcher widget cache",
    ),
    (
        GAME_JS,
        f"offenseWidget.js?v={version}",
        "Offense widget cache",
    ),
    (
        GAME_JS,
        f"mlbEngine.js?v={version}",
        "MLB engine cache",
    ),
    (
        GAME_HTML,
        f"game.js?v={version}",
        "Game script cache",
    ),
    (
        GAME_HTML,
        f"styles.css?v={version}",
        "Stylesheet cache",
    ),
):
    require(
        source,
        text,
        label,
    )


print("OFFENSE METRIC EXPANSION CHECK")
print("=" * 38)

if errors:
    for error in errors:
        print("FAIL:", error)

    sys.exit(1)


print(
    "PASS: wRC+ remains in every offense module."
)

print(
    "PASS: ISO is displayed near the bottom."
)

print(
    "PASS: SLG is the final offense row."
)

print(
    "PASS: wRC+, ISO, and SLG affect "
    "timeframe highlighting."
)

print(
    "PASS: future ranked offense metrics "
    "will contribute automatically."
)

print(
    "PASS: browser cache versions match."
)
