#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> int:
    html_path = ROOT / "todays-card.html"
    js_path = ROOT / "todays-card.js"
    css_path = ROOT / "assets/css/todays-card-multisport.css"
    config_path = ROOT / "data/sports-card-config.json"

    for path in (html_path, js_path, css_path, config_path):
        require(path.exists(), f"missing {path.relative_to(ROOT)}")

    html = html_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    required_ids = {
        "sportSwitcher",
        "sportWorkspace",
        "cardDateNavigation",
        "totalGames",
        "totalLive",
        "totalPlays",
        "activeLeagues",
    }
    for element_id in required_ids:
        require(f'id="{element_id}"' in html, f"missing HTML element #{element_id}")

    require("assets/css/todays-card-multisport.css" in html, "new stylesheet is not linked")
    require("todays-card.js" in html, "todays-card.js is not linked")
    require("data/live-games/" in js, "MLB daily-file fast path is missing")
    require("data/cards/" in js, "future league-feed path is missing")
    require("compact-event-grid" in css, "compact event grid styles are missing")
    require("league-dropdown" in css, "league dropdown styles are missing")

    sports = config.get("sports", [])
    require(len(sports) >= 8, "expected at least eight sport selectors")

    sport_ids = {sport.get("id") for sport in sports}
    for expected in {"baseball", "basketball", "football", "hockey", "soccer", "tennis", "combat", "golf"}:
        require(expected in sport_ids, f"missing sport {expected}")

    hockey = next(sport for sport in sports if sport.get("id") == "hockey")
    hockey_leagues = {league.get("id") for league in hockey.get("leagues", [])}
    for expected in {"nhl", "ahl", "echl", "ohl", "whl", "qmjhl", "ncaa-hockey", "ushl", "pwhl"}:
        require(expected in hockey_leagues, f"missing hockey league {expected}")

    baseball = next(sport for sport in sports if sport.get("id") == "baseball")
    mlb = next((league for league in baseball.get("leagues", []) if league.get("id") == "mlb"), None)
    require(mlb is not None and mlb.get("feed") == "active", "MLB must remain the active connected feed")

    node = shutil.which("node")
    if node:
        result = subprocess.run([node, "--check", str(js_path)], capture_output=True, text=True)
        require(result.returncode == 0, result.stderr.strip() or "JavaScript syntax check failed")
        node_status = "PASS"
    else:
        node_status = "SKIPPED (Node.js not installed; non-blocking)"

    total_leagues = sum(len(sport.get("leagues", [])) for sport in sports)
    print(f"Sport selectors: {len(sports)}")
    print(f"League dropdowns configured: {total_leagues}")
    print(f"Hockey leagues configured: {len(hockey.get('leagues', []))}")
    print("MLB game cards: compact multi-column layout")
    print("Future feed contract: data/cards/YYYY-MM-DD/<league>.json")
    print(f"JavaScript syntax check: {node_status}")
    print("PASS: Today’s Card Multi-Sport Shell is internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
