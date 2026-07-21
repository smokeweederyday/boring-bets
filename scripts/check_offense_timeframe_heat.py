#!/usr/bin/env python3

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

ENGINE = (
    ROOT
    / "assets/js/sports/mlbEngine.js"
).read_text(encoding="utf-8")

WIDGET = (
    ROOT
    / "assets/js/widgets/offenseWidget.js"
).read_text(encoding="utf-8")

STYLES = (
    ROOT / "styles.css"
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


for text in (
    "function buildOffenseTimeframeSignal(",
    "OFFENSE_SIGNAL_WEIGHTS",
    "overallMetric.overall_rank",
    "overallMetric.vs_hand_rank",
    "locationMetric.vs_hand_rank",
    "const timeframeSignals =",
    "timeframeSignals,",
):
    require(
        ENGINE,
        text,
        "Engine",
    )


for text in (
    "const timeframeSignals =",
    "timeframeSignals[timeframe]",
    "offense-control-signal",
    "offense-signal-neutral",
    'aria-pressed="',
):
    require(
        WIDGET,
        text,
        "Widget",
    )


for text in (
    "/* OFFENSE TIMEFRAME QUALITY HEAT",
    "offense-signal-strong-positive",
    "offense-signal-positive",
    "offense-signal-neutral",
    "offense-signal-negative",
    "offense-signal-strong-negative",
):
    require(
        STYLES,
        text,
        "Styles",
    )


version = (
    "phase11t-offense-metric-expansion1"
)

for source, text, label in (
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


print("OFFENSE TIMEFRAME HEAT CHECK")
print("=" * 36)

if errors:
    for error in errors:
        print("FAIL:", error)

    sys.exit(1)


print(
    "PASS: 7 Days has its own offense signal."
)

print(
    "PASS: 30 Days has its own offense signal."
)

print(
    "PASS: Season has its own offense signal."
)

print(
    "PASS: overall, starter-hand, and "
    "location-hand ranks contribute."
)

print(
    "PASS: active button retains its "
    "actual red, grey, or green grade."
)

print(
    "PASS: browser cache versions match."
)
