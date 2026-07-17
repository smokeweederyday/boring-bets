#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAMES_PATH = ROOT / "data" / "games.json"


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


raw = json.loads(GAMES_PATH.read_text(encoding="utf-8"))
games = raw.get("games", raw) if isinstance(raw, dict) else raw

checked = 0
issues = []

for game in games:
    bvp = game.get("pitcher_vs_lineup") or {}

    for key in ("away_pitcher", "home_pitcher"):
        record = bvp.get(key) or {}
        batters = record.get("batters") or {}

        if not isinstance(batters, dict) or not batters:
            continue

        checked += 1

        totals = {
            "pa": 0,
            "k": 0,
            "bb": 0,
            "hits": 0,
            "at_bats": 0,
            "total_bases": 0,
            "hit_by_pitch": 0,
            "sac_flies": 0,
        }

        hitters_with_history = 0

        for batter_id, row in batters.items():
            if not isinstance(row, dict):
                issues.append(f"{game.get('id')} {key} {batter_id}: invalid batter record")
                continue

            pa = int(number(row.get("plate_appearances")) or 0)
            if not row.get("available") or pa <= 0:
                continue

            hitters_with_history += 1

            required = (
                "strikeouts",
                "walks",
                "hits",
                "at_bats",
                "total_bases",
                "hit_by_pitch",
                "sac_flies",
            )

            for field in required:
                if field not in row:
                    issues.append(
                        f"{game.get('id')} {key} {batter_id}: missing {field}"
                    )

            totals["pa"] += pa
            totals["k"] += int(number(row.get("strikeouts")) or 0)
            totals["bb"] += int(number(row.get("walks")) or 0)
            totals["hits"] += int(number(row.get("hits")) or 0)
            totals["at_bats"] += int(number(row.get("at_bats")) or 0)
            totals["total_bases"] += int(number(row.get("total_bases")) or 0)
            totals["hit_by_pitch"] += int(number(row.get("hit_by_pitch")) or 0)
            totals["sac_flies"] += int(number(row.get("sac_flies")) or 0)

        ab = totals["at_bats"]
        avg = totals["hits"] / ab if ab else None

        obp_den = (
            totals["at_bats"]
            + totals["bb"]
            + totals["hit_by_pitch"]
            + totals["sac_flies"]
        )
        obp = (
            totals["hits"]
            + totals["bb"]
            + totals["hit_by_pitch"]
        ) / obp_den if obp_den else None

        slg = totals["total_bases"] / ab if ab else None
        ops = obp + slg if obp is not None and slg is not None else None

        print(
            f"{game.get('id')} {key}: "
            f"batters={len(batters)} "
            f"with_history={hitters_with_history} "
            f"PA={totals['pa']} "
            f"K={totals['k']} "
            f"BB={totals['bb']} "
            f"AVG={avg if avg is not None else '—'} "
            f"OPS={ops if ops is not None else '—'}"
        )

        if checked >= 2:
            break

    if checked >= 2:
        break

if checked == 0:
    raise SystemExit("FAIL: no BvP lineup records found.")

if issues:
    print("\nFAIL:")
    for issue in issues[:20]:
        print(f" - {issue}")
    raise SystemExit(1)

print(
    f"\nPASS: verified {checked} pitcher-vs-lineup records "
    "and calculated combined lineup history."
)
