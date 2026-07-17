#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mlb.lineups import (
    annotate_lineup_for_pitcher,
    classify_lineup_status,
    lineup_signature,
)


def normalize_existing_lineup(
    lineup: dict[str, Any],
    pitcher_throws: str | None,
) -> dict[str, Any]:
    normalized = dict(lineup or {})
    players = [dict(player) for player in (normalized.get("players") or [])]
    players.sort(key=lambda player: (player.get("order") or 99, player.get("name") or ""))
    normalized["players"] = players

    count = len(players)
    existing_status = str(normalized.get("status") or "").lower()
    source_confirmed = existing_status == "confirmed" and count >= 9
    status, status_label, confidence = classify_lineup_status(
        count,
        source_confirmed=source_confirmed,
    )

    normalized["status"] = status
    normalized["status_label"] = status_label
    normalized["completeness"] = {
        "count": count,
        "expected": 9,
        "ratio": round(count / 9, 3) if count else 0.0,
    }
    normalized["confidence"] = confidence
    normalized["signature"] = lineup_signature(players)
    normalized.setdefault("changed_since_last_refresh", False)
    normalized.setdefault("change_count", 0)

    return annotate_lineup_for_pitcher(normalized, pitcher_throws)


def main() -> None:
    path = ROOT / "data" / "games.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    games = raw.get("games", raw) if isinstance(raw, dict) else raw
    if not isinstance(games, list):
        raise SystemExit("games.json does not contain a usable games list.")

    updated = 0
    for game in games:
        lineups = game.get("lineups")
        if not isinstance(lineups, dict):
            continue

        away_pitcher_throws = (
            game.get("pitchers", {}).get("away", {}).get("throws")
        )
        home_pitcher_throws = (
            game.get("pitchers", {}).get("home", {}).get("throws")
        )

        if isinstance(lineups.get("away"), dict) and lineups["away"].get("players"):
            lineups["away"] = normalize_existing_lineup(
                lineups["away"],
                home_pitcher_throws,
            )
            updated += 1

        if isinstance(lineups.get("home"), dict) and lineups["home"].get("players"):
            lineups["home"] = normalize_existing_lineup(
                lineups["home"],
                away_pitcher_throws,
            )
            updated += 1

        game["lineups"] = lineups

    if isinstance(raw, dict):
        raw["games"] = games
        output = raw
    else:
        output = games

    backup = path.with_suffix(".json.before-phase8a-migration")
    if not backup.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Migrated {updated} stored lineup records to the Phase 8A schema.")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
