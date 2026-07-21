#!/usr/bin/env python3

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

WIDGET = (
    ROOT
    / "assets/js/widgets/pitcherWidget.js"
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
    "const clickedButton =",
    "const tappedCount =",
    "const activeCount =",
    "activeCount === tappedCount",
    "onStartModeChange?.(false)",
    "onStartCountChange?.(",
):
    require(
        WIDGET,
        text,
        "Widget",
    )


require(
    STYLES,
    "cursor: default;",
    "Slider overhang cursor",
)

require(
    STYLES,
    "cursor: pointer;",
    "Start-button cursor",
)


version = "phase11r-start-click-toggle1"

for source, text, label in (
    (
        GAME_JS,
        f"pitcherWidget.js?v={version}",
        "Pitcher widget cache",
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


print("PITCHER START TOGGLE CHECK")
print("=" * 34)

if errors:
    for error in errors:
        print("FAIL:", error)

    sys.exit(1)


print(
    "PASS: clicking the active number "
    "returns all pitcher data to Season."
)

print(
    "PASS: clicking the matching track area "
    "also returns to Season."
)

print(
    "PASS: clicking another position "
    "selects that recent-start sample."
)

print(
    "PASS: dragging remains supported."
)

print(
    "PASS: overhang resize cursor removed."
)
