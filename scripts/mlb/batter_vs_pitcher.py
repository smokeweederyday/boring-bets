from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


def fetch_batter_vs_pitcher(batter_id: int, pitcher_id: int) -> dict[str, Any]:
    """Fetch career batter-vs-pitcher hitting totals from MLB Stats API."""
    params = urllib.parse.urlencode({
        "stats": "vsPlayer",
        "group": "hitting",
        "opposingPlayerId": pitcher_id,
    })
    url = f"{MLB_API_BASE}/people/{batter_id}/stats?{params}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BoringBets/1.0", "Accept": "application/json"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = json.loads(response.read())
            return normalize_bvp_response(raw, batter_id, pitcher_id)
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in (429, 500, 502, 503, 504):
                break
        except Exception as error:
            last_error = error
        time.sleep(1.5 * (2 ** attempt))
    return empty_bvp(batter_id, pitcher_id, str(last_error or "unavailable"))


def normalize_bvp_response(raw: dict[str, Any], batter_id: int, pitcher_id: int) -> dict[str, Any]:
    stat: dict[str, Any] = {}
    for group in raw.get("stats", []):
        splits = group.get("splits", [])
        if splits:
            stat = splits[0].get("stat") or {}
            break

    pa = integer(stat.get("plateAppearances"))
    if pa is None:
        # MLB occasionally omits PA in small BvP responses. Derive it from
        # terminal outcomes when possible.
        pa = sum(
            integer(stat.get(key)) or 0
            for key in ("atBats", "baseOnBalls", "hitByPitch", "sacFlies", "sacBunts")
        )
    return {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "plate_appearances": pa,
        "strikeouts": integer(stat.get("strikeOuts")) or 0,
        "walks": integer(stat.get("baseOnBalls")) or 0,
        "avg": number(stat.get("avg")),
        "ops": number(stat.get("ops")),
        "hits": integer(stat.get("hits")),
        "at_bats": integer(stat.get("atBats")),
        "total_bases": integer(stat.get("totalBases")),
        "hit_by_pitch": integer(stat.get("hitByPitch")) or 0,
        "sac_flies": integer(stat.get("sacFlies")) or 0,
        "obp": number(stat.get("obp")),
        "slg": number(stat.get("slg")),
        "source": "MLB Stats API career vsPlayer",
        "available": bool(pa or stat),
    }


def build_bvp_for_game(game: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"away_pitcher": {}, "home_pitcher": {}}
    matchups = (
        ("away_pitcher", game.get("pitchers", {}).get("away", {}), game.get("lineups", {}).get("home", {})),
        ("home_pitcher", game.get("pitchers", {}).get("home", {}), game.get("lineups", {}).get("away", {})),
    )
    for key, pitcher, lineup in matchups:
        pitcher_id = integer(pitcher.get("id"))
        players = [p for p in lineup.get("players", []) if integer(p.get("id"))]
        if not pitcher_id or not players:
            continue
        workers = max(1, min(int(os.getenv("BORING_BETS_BVP_WORKERS", "5")), 8))
        rows: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(fetch_batter_vs_pitcher, int(player["id"]), pitcher_id): player
                for player in players[:9]
            }
            for future in as_completed(futures):
                player = futures[future]
                try:
                    row = future.result()
                except Exception as error:
                    row = empty_bvp(int(player["id"]), pitcher_id, str(error))
                row["name"] = player.get("name") or "Unknown hitter"
                row["order"] = player.get("order")
                rows[str(player["id"])] = row
        result[key] = {
            "pitcher_id": pitcher_id,
            "pitcher_name": pitcher.get("name"),
            "batters": rows,
            "source": "MLB Stats API career vsPlayer",
        }
    return result


def empty_bvp(batter_id: int, pitcher_id: int, error: str | None = None) -> dict[str, Any]:
    return {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "plate_appearances": 0,
        "strikeouts": 0,
        "walks": 0,
        "avg": None,
        "ops": None,
        "hits": None,
        "at_bats": None,
        "total_bases": None,
        "hit_by_pitch": 0,
        "sac_flies": 0,
        "obp": None,
        "slg": None,
        "available": False,
        "source": "MLB Stats API career vsPlayer",
        "error": error,
    }


def integer(value: Any) -> int | None:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def number(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None
