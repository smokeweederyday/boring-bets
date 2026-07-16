from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os


MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

OFFENSE_METRICS = (
    "AVG",
    "OBP",
    "SLG",
    "OPS",
    "wRC+",
    "BB%",
    "K%",
)


def get_json(
    url: str,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Boring Bets/1.0"
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        return json.loads(
            response.read()
        )


def fetch_team_hitting_stats(
    team_id: int,
    stat_type: str,
    season: int,
    start_date: str | None = None,
    end_date: str | None = None,
    sit_code: str | None = None,
) -> dict[str, Any]:
    effective_stat_type = "statSplits" if sit_code else stat_type
    params: dict[str, Any] = {
        "stats": effective_stat_type,
        "group": "hitting",
        "season": season,
    }

    if start_date:
        params["startDate"] = start_date

    if end_date:
        params["endDate"] = end_date

    if sit_code:
        # MLB expects a single comma-separated situation expression. Repeated
        # sitCodes parameters are treated as separate splits and the old parser
        # then selected only the first one, making Home/Away appear identical.
        params["sitCodes"] = ",".join(
            part.strip() for part in sit_code.split(",") if part.strip()
        )

    query = urllib.parse.urlencode(params)

    raw = get_json(
        f"{MLB_API_BASE}/teams/"
        f"{team_id}/stats?{query}"
    )

    return parse_team_hitting_block(
        raw
    )


def parse_team_hitting_block(
    raw: dict[str, Any],
) -> dict[str, Any]:
    for group in raw.get(
        "stats",
        [],
    ):
        splits = group.get(
            "splits",
            [],
        )

        if not splits:
            continue

        stat = splits[0].get(
            "stat",
            {},
        )

        return normalize_team_hitting_stat(
            stat
        )

    return {}


def normalize_team_hitting_stat(
    stat: dict[str, Any],
) -> dict[str, Any]:
    plate_appearances = to_float(
        stat.get("plateAppearances")
    )

    strikeouts = to_float(
        stat.get("strikeOuts")
    )

    walks = to_float(
        stat.get("baseOnBalls")
    )

    return {
        "AVG": to_float(
            stat.get("avg")
        ),
        "wRC+": None,
        "K%": rate_percent(
            strikeouts,
            plate_appearances,
        ),
        "BB%": rate_percent(
            walks,
            plate_appearances,
        ),
        "OBP": to_float(
            stat.get("obp")
        ),
        "SLG": to_float(
            stat.get("slg")
        ),
        "OPS": to_float(
            stat.get("ops")
        ),
        "plate_appearances":
            to_int(
                stat.get("plateAppearances")
            ),
        "runs":
            to_int(
                stat.get("runs")
            ),
        "home_runs":
            to_int(
                stat.get("homeRuns")
            ),
        "strikeouts":
            to_int(
                stat.get("strikeOuts")
            ),
        "walks":
            to_int(
                stat.get("baseOnBalls")
            ),
    }


def fetch_safe_split(
    team_id: int,
    season: int,
    sit_code: str,
) -> dict[str, Any]:
    try:
        return fetch_team_hitting_stats(
            team_id=team_id,
            stat_type="statSplits",
            season=season,
            sit_code=sit_code,
        )
    except Exception as error:
        print(
            f"Team split {sit_code} unavailable "
            f"for team {team_id}: {error}"
        )
        return {}



MLB_TEAM_IDS = (
    108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
    118, 119, 120, 121, 133, 134, 135, 136, 137, 138,
    139, 140, 141, 142, 143, 144, 145, 146, 147, 158,
)



def fetch_team_hitting_game_log(team_id: int, season: int) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({
        "stats": "gameLog",
        "group": "hitting",
        "season": season,
    })
    raw = get_json(f"{MLB_API_BASE}/teams/{team_id}/stats?{params}")
    rows: list[dict[str, Any]] = []
    for group in raw.get("stats", []):
        for split in group.get("splits", []):
            stat = split.get("stat") or {}
            game = split.get("game") or {}
            home_away = (
                split.get("homeAway")
                or game.get("homeAway")
                or split.get("isHome")
            )
            if isinstance(home_away, bool):
                is_home = home_away
            elif isinstance(home_away, str):
                is_home = home_away.lower() == "home"
            else:
                is_home = None
            rows.append({
                "date": split.get("date") or split.get("gameDate"),
                "is_home": is_home,
                "stat": stat,
            })
    return rows


def aggregate_team_game_log(
    rows: list[dict[str, Any]],
    start_date: str | None,
    end_date: str | None,
    location: str,
) -> dict[str, Any]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    totals = {
        "atBats": 0.0, "hits": 0.0, "baseOnBalls": 0.0,
        "hitByPitch": 0.0, "sacFlies": 0.0, "totalBases": 0.0,
        "strikeOuts": 0.0, "plateAppearances": 0.0,
        "runs": 0.0, "homeRuns": 0.0,
    }
    games = 0
    for row in rows:
        raw_date = row.get("date")
        try:
            current = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        if start and current < start:
            continue
        if end and current > end:
            continue
        is_home = row.get("is_home")
        if location == "home" and is_home is not True:
            continue
        if location == "away" and is_home is not False:
            continue
        stat = row.get("stat") or {}
        for key in totals:
            value = to_float(stat.get(key))
            if value is not None:
                totals[key] += value
        games += 1
    if games == 0:
        return {}
    ab, hits = totals["atBats"], totals["hits"]
    bb, hbp, sf = totals["baseOnBalls"], totals["hitByPitch"], totals["sacFlies"]
    pa = totals["plateAppearances"]
    avg = hits / ab if ab else None
    obp_den = ab + bb + hbp + sf
    obp = (hits + bb + hbp) / obp_den if obp_den else None
    slg = totals["totalBases"] / ab if ab else None
    return {
        "AVG": avg,
        "OBP": obp,
        "SLG": slg,
        "OPS": (obp + slg) if obp is not None and slg is not None else None,
        "wRC+": None,
        "BB%": rate_percent(bb, pa),
        "K%": rate_percent(totals["strikeOuts"], pa),
        "plate_appearances": int(pa),
        "runs": int(totals["runs"]),
        "home_runs": int(totals["homeRuns"]),
        "strikeouts": int(totals["strikeOuts"]),
        "walks": int(bb),
        "games": games,
    }


def fetch_all_team_game_logs(season: int) -> dict[int, list[dict[str, Any]]]:
    workers = max(2, min(int(os.getenv("BORING_BETS_MLB_FETCH_WORKERS", "10")), 16))
    result: dict[int, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_team_hitting_game_log, team_id, season): team_id
            for team_id in MLB_TEAM_IDS
        }
        for future in as_completed(futures):
            team_id = futures[future]
            try:
                result[team_id] = future.result()
            except Exception as error:
                print(f"Team game log unavailable for {team_id}: {error}")
                result[team_id] = []
    return result

def fetch_league_hitting_stats(
    stat_type: str,
    season: int,
    start_date: str | None = None,
    end_date: str | None = None,
    sit_codes: list[str] | None = None,
) -> dict[int, dict[str, Any]]:
    """Fetch one comparable team-level snapshot for all 30 MLB clubs.

    MLB's league `/stats` endpoint does not reliably return team rows for these
    filters. We therefore query the 30 team endpoints in parallel. This is
    slower on the first run but correct, and the completed matrix is cached.
    """
    workers = max(2, min(int(os.getenv("BORING_BETS_MLB_FETCH_WORKERS", "10")), 16))
    codes = list(sit_codes or [])

    def fetch_one(team_id: int) -> tuple[int, dict[str, Any]]:
        return team_id, fetch_team_hitting_stats(
            team_id=team_id,
            stat_type=stat_type,
            season=season,
            start_date=start_date,
            end_date=end_date,
            sit_code=",".join(codes) if codes else None,
        )

    teams: dict[int, dict[str, Any]] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_one, team_id): team_id for team_id in MLB_TEAM_IDS}
        for future in as_completed(futures):
            team_id = futures[future]
            try:
                fetched_team_id, stats = future.result()
                teams[fetched_team_id] = stats
            except Exception as error:
                errors.append(f"{team_id}: {error}")

    if errors:
        print(f"League matrix request warnings ({len(errors)}): " + "; ".join(errors[:3]))

    # Keep all 30 team IDs in the pool even when a club has no qualifying PA
    # for a narrow window. Such teams receive null values, not a fake rank.
    for team_id in MLB_TEAM_IDS:
        teams.setdefault(team_id, {})
    return teams


def rank_league_rows(rows: dict[int, dict[str, Any]]) -> dict[int, dict[str, int | None]]:
    directions = {"AVG": True, "OBP": True, "SLG": True, "OPS": True, "wRC+": True, "BB%": True, "K%": False}
    result: dict[int, dict[str, int | None]] = {team_id: {} for team_id in rows}
    for metric, higher_is_better in directions.items():
        values = [(team_id, stats.get(metric)) for team_id, stats in rows.items()]
        values = [(team_id, float(value)) for team_id, value in values if isinstance(value, (int, float))]
        values.sort(key=lambda item: item[1], reverse=higher_is_better)
        previous_value = None
        previous_rank = 0
        for index, (team_id, value) in enumerate(values, start=1):
            rank = previous_rank if previous_value == value else index
            result.setdefault(team_id, {})[metric] = rank
            previous_value, previous_rank = value, rank
    return result


def _cache_path(target_date: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    cache_dir = root / "data" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"mlb-offense-rank-matrix-{target_date}.json"


def _matrix_is_complete(cache: dict[str, Any]) -> bool:
    try:
        for timeframe in ("last_7", "last_30", "season"):
            for location in ("all", "home", "away"):
                for hand in ("overall", "vs_lhp", "vs_rhp"):
                    pool = cache[timeframe][location][hand]
                    if int(pool.get("team_pool", 0)) != 30:
                        return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def build_league_offense_cache(target_date: str) -> dict[str, Any]:
    """Build exact 30-team comparison pools for all UI filter combinations."""
    cache_path = _cache_path(target_date)
    if cache_path.exists() and os.getenv("BORING_BETS_REBUILD_RANK_CACHE") != "1":
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if _matrix_is_complete(cached):
                print(f"Using cached 30-team offense matrix: {cache_path.name}")
                return cached
        except (OSError, json.JSONDecodeError):
            pass

    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    season = target.year
    windows = {
        "last_7": ("byDateRange", target - timedelta(days=7), target),
        "last_30": ("byDateRange", target - timedelta(days=30), target),
        "season": ("season", None, None),
    }
    locations = {"all": [], "home": ["h"], "away": ["a"]}
    hands = {"overall": [], "vs_lhp": ["vl"], "vs_rhp": ["vr"]}
    cache: dict[str, Any] = {}
    print("Fetching all 30 team game logs for offense All/Home/Away...")
    team_game_logs = fetch_all_team_game_logs(season)
    total_pools = len(windows) * len(locations) * len(hands)
    completed = 0
    for timeframe, (stat_type, start, end) in windows.items():
        cache[timeframe] = {}
        for location, location_codes in locations.items():
            cache[timeframe][location] = {}
            for hand_key, hand_codes in hands.items():
                completed += 1
                print(f"  Rank pool {completed}/{total_pools}: {timeframe} / {location} / {hand_key}")
                if hand_key == "overall":
                    rows = {
                        team_id: aggregate_team_game_log(
                            team_game_logs.get(team_id, []),
                            start.isoformat() if start else None,
                            (end or target).isoformat(),
                            location,
                        )
                        for team_id in MLB_TEAM_IDS
                    }
                else:
                    rows = fetch_league_hitting_stats(
                        stat_type=stat_type,
                        season=season,
                        start_date=start.isoformat() if start else None,
                        end_date=end.isoformat() if end else None,
                        sit_codes=location_codes + hand_codes,
                    )

                if len(rows) != 30:
                    raise RuntimeError(
                        f"Rank matrix incomplete for {timeframe}/{location}/{hand_key}: "
                        f"expected 30 team IDs, received {len(rows)}"
                    )
                nonempty = sum(1 for value in rows.values() if value)
                cache[timeframe][location][hand_key] = {
                    "stats": rows,
                    "ranks": rank_league_rows(rows),
                    "team_pool": 30,
                    "coverage": nonempty,
                    "scope": "all_30_mlb_teams",
                }

    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    return cache


def apply_league_offense_cache(
    snapshot: dict[str, Any],
    league_cache: dict[str, Any],
) -> dict[str, Any]:
    team_id = int(snapshot["team_id"])
    opponent_hand = str(snapshot.get("opponent_throws") or "").upper()
    hand_key = "vs_lhp" if opponent_hand == "L" else "vs_rhp" if opponent_hand == "R" else "overall"
    stats_root: dict[str, Any] = {}
    for timeframe in ("last_7", "last_30", "season"):
        stats_root[timeframe] = {}
        for location in ("all", "home", "away"):
            overall_pool = league_cache.get(timeframe, {}).get(location, {}).get("overall", {})
            split_pool = league_cache.get(timeframe, {}).get(location, {}).get(hand_key, {})
            overall_stats = overall_pool.get("stats", {})
            split_stats = split_pool.get("stats", {})
            overall_rank_map = overall_pool.get("ranks", {})
            split_rank_map = split_pool.get("ranks", {})

            # Fresh Python dictionaries use integer team IDs, while cached
            # JSON reloads them as strings. Support both representations.
            overall = overall_stats.get(team_id, overall_stats.get(str(team_id), {}))
            versus = split_stats.get(team_id, split_stats.get(str(team_id), {}))
            overall_ranks = overall_rank_map.get(
                team_id, overall_rank_map.get(str(team_id), {})
            )
            split_ranks = split_rank_map.get(
                team_id, split_rank_map.get(str(team_id), {})
            )
            block = build_metric_block(overall, versus)
            for metric, row in block.items():
                row["overall_rank"] = overall_ranks.get(metric)
                row["overall_rank_coverage"] = overall_pool.get("team_pool")
                row["vs_hand_rank"] = split_ranks.get(metric)
                row["vs_hand_rank_coverage"] = split_pool.get("team_pool")
            stats_root[timeframe][location] = block
    snapshot["stats"] = stats_root
    snapshot["rank_scope"] = "all_30_mlb_teams_exact_active_filters"
    return snapshot


def build_metric_block(
    overall: dict[str, Any],
    versus_hand: dict[str, Any],
) -> dict[str, Any]:
    block: dict[str, Any] = {}

    for metric in OFFENSE_METRICS:
        block[metric] = {
            "overall":
                overall.get(metric),
            "overall_rank":
                None,
            "vs_hand":
                versus_hand.get(metric),
            "vs_hand_rank":
                None,
        }

    return block


def build_team_offense_snapshot(
    team_id: int,
    opponent_throws: str | None,
    target_date: str,
) -> dict[str, Any]:
    return {
        "team_id": team_id,
        "opponent_throws": str(opponent_throws or "").upper() or None,
        "stats": {},
        "raw_splits": {},
        "source": "MLB Stats API team game logs + stat splits",
        "as_of": target_date,
    }


def rate_percent(
    numerator: float | None,
    denominator: float | None,
) -> float | None:
    if (
        numerator is None
        or denominator is None
        or denominator <= 0
    ):
        return None

    return (
        numerator
        / denominator
        * 100
    )


def to_float(
    value: Any,
) -> float | None:
    if value in {
        None,
        "",
        "-",
        ".---",
    }:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def to_int(
    value: Any,
) -> int | None:
    if value in {
        None,
        "",
        "-",
    }:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python3 scripts/mlb/offense.py "
            "<team_id> [L|R] [YYYY-MM-DD]"
        )

    team_id = int(
        sys.argv[1]
    )

    opponent_throws = (
        sys.argv[2]
        if len(sys.argv) > 2
        else None
    )

    target_date = (
        sys.argv[3]
        if len(sys.argv) > 3
        else date.today().isoformat()
    )

    snapshot = build_team_offense_snapshot(
        team_id,
        opponent_throws,
        target_date,
    )

    print(
        json.dumps(
            snapshot,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
