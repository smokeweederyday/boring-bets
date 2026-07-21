#!/usr/bin/env python3

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

html = (
    ROOT / "game.html"
).read_text(encoding="utf-8")

pitcher = (
    ROOT
    / "assets/js/widgets/pitcherWidget.js"
).read_text(encoding="utf-8")

offense = (
    ROOT
    / "assets/js/widgets/offenseWidget.js"
).read_text(encoding="utf-8")

engine = (
    ROOT
    / "assets/js/sports/mlbEngine.js"
).read_text(encoding="utf-8")

styles = (
    ROOT / "styles.css"
).read_text(encoding="utf-8")

failures = []


pitching = re.search(
    r'<section[^>]+id="pitching"[^>]*>'
    r'(.*?)'
    r'</section>',
    html,
    re.DOTALL,
)

if not pitching:
    failures.append(
        "Pitching section is missing."
    )
else:
    columns = re.findall(
        r'<article[^>]*class="matchup-column"[^>]*>'
        r'(.*?)'
        r'</article>',
        pitching.group(1),
        re.DOTALL,
    )

    if len(columns) != 2:
        failures.append(
            "Pitching section must have two columns."
        )
    else:
        away, home = columns

        if not (
            'id="awayPitcherCard"' in away
            and 'id="awayOffenseCard"' in away
        ):
            failures.append(
                "Away pitcher/offense pairing is broken."
            )

        if not (
            'id="homePitcherCard"' in home
            and 'id="homeOffenseCard"' in home
        ):
            failures.append(
                "Home pitcher/offense pairing is broken."
            )


if "OFFENSE VS STARTER" in offense:
    failures.append(
        "OFFENSE VS STARTER still exists."
    )

if "STARTING PITCHER" in pitcher:
    failures.append(
        "STARTING PITCHER text still exists."
    )

if not re.search(
    r'<div class="pitcher-name-row">'
    r'.*?'
    r'<h2 class="pitcher-name-heading">'
    r'.*?'
    r'</h2>'
    r'.*?'
    r'<span class="pitcher-status-label">',
    pitcher,
    re.DOTALL,
):
    failures.append(
        "Pitcher status is not beside the name."
    )

for label in (
    'return "PROBABLE";',
    'return "CHANGED";',
    'return "CONFIRMED";',
):
    if label not in engine:
        failures.append(
            "Missing status contract: "
            + label
        )

for css_rule in (
    "--game-module-heading-size: 1rem",
    "calc(var(--game-module-heading-size) * 2)",
    ".pitcher-name-row",
    ".pitcher-name-heading",
    ".pitcher-status-label",
):
    if css_rule not in styles:
        failures.append(
            "Missing CSS contract: "
            + css_rule
        )


print("BORING BETS GAME-PAGE MODULE CONTRACT")
print("=" * 42)

if failures:
    for failure in failures:
        print("FAIL:", failure)

    sys.exit(1)

print(
    "PASS: offense modules remain on the correct sides."
)

print(
    "PASS: redundant offense and pitcher labels are removed."
)

print(
    "PASS: pitcher name is twice the offense/bullpen header size."
)

print(
    "PASS: PROBABLE, CHANGED, or CONFIRMED sits beside the name."
)
