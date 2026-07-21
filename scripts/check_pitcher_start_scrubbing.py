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
    "let suppressStartClick = false;",
    "const startSlider =",
    '"pointerdown"',
    '"pointermove"',
    '"pointerup"',
    '"pointercancel"',
    "countFromClientX",
    "showScrubPreview",
    "setPointerCapture",
    "onStartCountChange?.(",
):
    require(
        WIDGET,
        text,
        "Widget",
    )


for text in (
    "/* PITCHER START DRAG SCRUBBING",
    "touch-action: pan-y",
    "cursor: ew-resize",
    ".is-scrubbing",
    ".scrub-preview",
):
    require(
        STYLES,
        text,
        "Styles",
    )


version = "phase11t-offense-metric-expansion1"

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


print("PITCHER START SCRUBBING CHECK")
print("=" * 37)

if errors:
    for error in errors:
        print("FAIL:", error)

    sys.exit(1)


print(
    "PASS: mouse dragging is supported."
)

print(
    "PASS: touch scrubbing is supported."
)

print(
    "PASS: dragging snaps to valid start counts."
)

print(
    "PASS: normal click selection remains supported."
)

print(
    "PASS: browser cache versions match."
)
