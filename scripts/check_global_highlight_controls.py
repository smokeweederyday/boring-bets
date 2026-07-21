#!/usr/bin/env python3

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

html = (
    ROOT / "game.html"
).read_text(
    encoding="utf-8"
)

game_js = (
    ROOT / "game.js"
).read_text(
    encoding="utf-8"
)

preferences = (
    ROOT
    / "assets/js/engine/highlightPreferences.js"
).read_text(
    encoding="utf-8"
)

styles = (
    ROOT / "styles.css"
).read_text(
    encoding="utf-8"
)

offense = (
    ROOT
    / "assets/js/widgets/offenseWidget.js"
).read_text(
    encoding="utf-8"
)

pitcher = (
    ROOT
    / "assets/js/widgets/pitcherWidget.js"
).read_text(
    encoding="utf-8"
)


checks = (
    (
        "Persistent preferences",
        "boringBetsGlobalHighlightPreferencesV3"
        in preferences,
    ),
    (
        "Five minimum",
        "const MIN_RANGE = 5;"
        in preferences
        and 'min="5"'
        in html,
    ),
    (
        "Hundred maximum",
        "const MAX_RANGE = 100;"
        in preferences
        and 'max="100"'
        in html,
    ),
    (
        "Twenty-five preset",
        "range: 25"
        in preferences
        and 'value="25"'
        in html,
    ),
    (
        "Exact typed values",
        "function normalizeRange(value)"
        in preferences
        and "Math.round(\n        numericValue\n      )"
        in preferences
        and 'step="1"'
        in html,
    ),
    (
        "Five-point drag snapping",
        "function normalizeSliderRange(value)"
        in preferences
        and "snapToSliderStep: true"
        in preferences,
    ),
    (
        "Separate input rules",
        "snapToSliderStep = false"
        in preferences
        and "? normalizeSliderRange(value)"
        in preferences,
    ),
    (
        "Editable number box",
        'id="globalHighlightRangeOutput"'
        in html
        and 'type="number"'
        in html,
    ),
    (
        "Gray-white thumb",
        "--highlight-thumb-color"
        in preferences
        and "var(--highlight-thumb-color"
        in styles,
    ),
    (
        "Neutral default",
        'id="globalHighlightNeutral"'
        in html
        and "checked"
        in html,
    ),
    (
        "Bullpen exemption",
        "bullpen-widget-shell"
        in preferences,
    ),
    (
        "Pitcher-name exception",
        "pitcher-name-signal"
        in preferences,
    ),
    (
        "Offense markers",
        "data-global-rank"
        in offense
        and "data-global-signal-score"
        in offense,
    ),
    (
        "Pitcher markers",
        "data-global-rank"
        in pitcher
        and "data-global-signal-score"
        in pitcher,
    ),
    (
        "Game initialization",
        "initializeHighlightControls"
        in game_js,
    ),
    (
        "Cache version",
        "phase11z-exact-typed-spread3"
        in html
        and "phase11z-exact-typed-spread3"
        in game_js,
    ),
)


print(
    "GLOBAL HIGHLIGHT CONTROL CHECK"
)

print(
    "=" * 40
)

failed = []

for label, passed in checks:
    if passed:
        print(
            f"PASS: {label}"
        )
    else:
        failed.append(label)

        print(
            f"FAIL: {label}"
        )

if failed:
    raise SystemExit(
        "\nFailed checks: "
        + ", ".join(failed)
    )
