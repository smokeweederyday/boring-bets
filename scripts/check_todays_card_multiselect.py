#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> int:
    html = (ROOT / "todays-card.html").read_text(encoding="utf-8")
    js = (ROOT / "todays-card.js").read_text(encoding="utf-8")
    css = (ROOT / "assets/css/todays-card-multisport.css").read_text(encoding="utf-8")
    config = json.loads((ROOT / "data/sports-card-config.json").read_text(encoding="utf-8"))

    sport_count = html.count('data-sport-id="')
    configured_sports = len(config.get("sports", []))
    configured_leagues = sum(len(sport.get("leagues", [])) for sport in config.get("sports", []))

    require(configured_sports == 8, "expected eight configured sports")
    require(sport_count >= 9, "static eight-sport row and MLB fallback were not found")
    require('aria-pressed="true"' in html, "sport buttons are not multi-select controls")
    require('selectedSportIds: new Set' in js, "multi-select sport state is missing")
    require('toggleSport' in js, "sport toggle behavior is missing")
    require('sports", [...cardState.selectedSportIds]' in js, "multi-sport URL persistence is missing")
    require('has-many-sports' in js and 'has-many-sports' in css, "side-by-side selected sport boards are missing")
    require('multisport-date-previous' in html and 'multisport-date-next' in html, "date arrows are missing")
    require('background: var(--green' in css, "green date-arrow treatment is missing")
    require('Baseball leagues' not in html, "redundant Baseball leagues header remains")
    require('<p class="kicker">BASEBALL</p>' not in html, "redundant Baseball header remains")
    require('data/cards/${encodeURIComponent(date)}/${encodeURIComponent(leagueId)}.json' in js, "future league feed contract is missing")

    node = shutil.which("node")
    if node:
        result = subprocess.run([node, "--check", str(ROOT / "todays-card.js")], capture_output=True, text=True)
        require(result.returncode == 0, result.stderr.strip() or "JavaScript syntax check failed")
        node_result = "PASS"
    else:
        node_result = "SKIPPED (Node.js not installed; non-blocking)"

    print(f"Sport selectors: {configured_sports} multi-select buttons")
    print(f"League dropdowns configured: {configured_leagues}")
    print("Green date arrows: restored inside dedicated date strip")
    print("Redundant Baseball headers: removed")
    print("Selected sports: render together on one day board")
    print(f"JavaScript syntax check: {node_result}")
    print("PASS: Today’s Card Multi-Select Slate Board is internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
