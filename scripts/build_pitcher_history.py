#!/usr/bin/env python3
"""Build lazy-loaded MLB pitcher-history files for game-page previews."""

from __future__ import annotations

import argparse
import json
import math
import threading
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
GAMES_DIRECTORY = ROOT / "data" / "games"
OUTPUT_DIRECTORY = ROOT / "data" / "pitcher-history"
RUNTIME_ROOT = Path(
    os.environ.get(
        "BORING_BETS_DATA_ROOT",
        str(ROOT / ".runtime-data"),
    )
)
CACHE_DIRECTORY = RUNTIME_ROOT / "pitcher-history-season-cache"
RANK_CACHE_DIRECTORY = (
    RUNTIME_ROOT
    / "pitcher-history-rank-cache"
)

RANK_CACHE_LOCK = threading.Lock()
RANK_CACHE_MEMORY: Dict[int, Dict[str, Any]] = {}

HISTORY_RANK_DIRECTIONS = {
    "ip": True,
    "hits": False,
    "runs": False,
    "earned_runs": False,
    "walks": False,
    "strikeouts": True,
    "home_runs": False,
    "era": False,
    "whip": False,
}


EASTERN = ZoneInfo("America/New_York")
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

TEAM_ABBR_BY_ID = {
    108: "LAA", 109: "AZ", 110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC", 119: "LAD", 120: "WSH", 121: "NYM", 133: "ATH",
    134: "PIT", 135: "SD", 136: "SEA", 137: "SF", 138: "STL",
    139: "TB", 140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CHW", 146: "MIA", 147: "NYY", 158: "MIL",
}

TEAM_ABBR_BY_NAME = {
    "los angeles angels": "LAA",
    "arizona diamondbacks": "AZ",
    "baltimore orioles": "BAL",
    "boston red sox": "BOS",
    "chicago cubs": "CHC",
    "cincinnati reds": "CIN",
    "cleveland guardians": "CLE",
    "colorado rockies": "COL",
    "detroit tigers": "DET",
    "houston astros": "HOU",
    "kansas city royals": "KC",
    "los angeles dodgers": "LAD",
    "washington nationals": "WSH",
    "new york mets": "NYM",
    "athletics": "ATH",
    "oakland athletics": "ATH",
    "pittsburgh pirates": "PIT",
    "san diego padres": "SD",
    "seattle mariners": "SEA",
    "san francisco giants": "SF",
    "st. louis cardinals": "STL",
    "st louis cardinals": "STL",
    "tampa bay rays": "TB",
    "texas rangers": "TEX",
    "toronto blue jays": "TOR",
    "minnesota twins": "MIN",
    "philadelphia phillies": "PHI",
    "atlanta braves": "ATL",
    "chicago white sox": "CHW",
    "miami marlins": "MIA",
    "new york yankees": "NYY",
    "milwaukee brewers": "MIL",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build pitcher-history files for upcoming MLB starters."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(EASTERN).date().isoformat(),
        help="First game date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=14,
        help="Number of future schedule days to inspect.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent pitcher builds.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refetch completed historical seasons.",
    )
    return parser.parse_args()


def get_json(url: str, attempts: int = 3) -> Dict[str, Any]:
    last_error = None

    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "BoringBets/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                value = json.loads(response.read())

            return value if isinstance(value, dict) else {}

        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(attempt)

    raise RuntimeError(f"Unable to fetch {url}: {last_error}")


def to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def innings_to_outs(value: Any) -> int:
    text = str(value or "0.0").strip()

    if "." not in text:
        try:
            return int(text) * 3
        except ValueError:
            return 0

    whole_text, partial_text = text.split(".", 1)

    try:
        whole = int(whole_text)
        partial = int(partial_text[:1] or "0")
    except ValueError:
        return 0

    if partial not in (0, 1, 2):
        partial = 0

    return whole * 3 + partial


def outs_to_innings(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def team_abbreviation(value: Any) -> str:
    if not isinstance(value, dict):
        return ""

    team_id = to_int(value.get("id") or value.get("team_id"))

    if team_id in TEAM_ABBR_BY_ID:
        return TEAM_ABBR_BY_ID[team_id]

    abbreviation = str(
        value.get("abbreviation")
        or value.get("abbr")
        or ""
    ).strip().upper()

    if abbreviation:
        return abbreviation

    name = str(value.get("name") or "").strip().lower()
    return TEAM_ABBR_BY_NAME.get(name, "")



def to_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def rank_cache_path(season: int) -> Path:
    return RANK_CACHE_DIRECTORY / f"{season}.json"


def fetch_season_rank_splits(
    season: int,
    player_pool: str,
) -> List[Dict[str, Any]]:
    limit = 1000
    offset = 0
    splits: List[Dict[str, Any]] = []

    while True:
        params = urllib.parse.urlencode(
            {
                "stats": "season",
                "group": "pitching",
                "season": season,
                "sportIds": 1,
                "playerPool": player_pool,
                "limit": limit,
                "offset": offset,
            }
        )

        document = get_json(
            f"{MLB_API_BASE}/stats?{params}"
        )

        groups = document.get("stats") or []

        if not groups:
            break

        group = groups[0] or {}
        page = [
            split
            for split in group.get("splits") or []
            if isinstance(split, dict)
        ]

        splits.extend(page)

        total = (
            to_int(group.get("totalSplits"))
            or len(splits)
        )

        if (
            not page
            or len(splits) >= total
        ):
            break

        offset += len(page)

    return splits


def normalize_rank_source(
    split: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    stat = split.get("stat") or {}

    outs = (
        to_int(stat.get("outs"))
        or to_int(stat.get("outsPitched"))
        or innings_to_outs(
            stat.get("inningsPitched")
        )
    )

    if outs <= 0:
        return None

    innings = outs / 3
    hits = to_int(stat.get("hits")) or 0
    runs = to_int(stat.get("runs")) or 0
    earned_runs = (
        to_int(stat.get("earnedRuns"))
        or 0
    )
    walks = (
        to_int(stat.get("baseOnBalls"))
        or 0
    )
    strikeouts = (
        to_int(stat.get("strikeOuts"))
        or 0
    )
    home_runs = (
        to_int(stat.get("homeRuns"))
        or 0
    )

    era = to_float(stat.get("era"))

    if era is None and innings:
        era = earned_runs * 9 / innings

    whip = to_float(stat.get("whip"))

    if whip is None and innings:
        whip = (hits + walks) / innings

    return {
        "games_started":
            to_int(stat.get("gamesStarted"))
            or 0,
        "outs": outs,
        "hits": hits,
        "runs": runs,
        "earned_runs": earned_runs,
        "walks": walks,
        "strikeouts": strikeouts,
        "home_runs": home_runs,
        "era": era,
        "whip": whip,
    }


def history_rank_value(
    row: Dict[str, Any],
    metric: str,
    mode: str,
) -> Optional[float]:
    outs = to_int(row.get("outs")) or 0
    starts = (
        to_int(row.get("games_started"))
        or 0
    )

    if metric == "ip":
        if mode == "season":
            return float(outs) if outs else None

        return (
            outs / starts
            if starts > 0
            else None
        )

    counting_fields = {
        "hits",
        "runs",
        "earned_runs",
        "walks",
        "strikeouts",
        "home_runs",
    }

    if metric in counting_fields:
        count = to_float(row.get(metric))

        if count is None:
            return None

        if mode == "season":
            return (
                count * 27 / outs
                if outs > 0
                else None
            )

        return (
            count / starts
            if starts > 0
            else None
        )

    if metric in {"era", "whip"}:
        return to_float(row.get(metric))

    return None


def build_rank_pools(
    rows: List[Dict[str, Any]],
    mode: str,
) -> Dict[str, List[float]]:
    pools = {
        metric: []
        for metric
        in HISTORY_RANK_DIRECTIONS
    }

    for row in rows:
        for metric in pools:
            value = history_rank_value(
                row,
                metric,
                mode,
            )

            if (
                value is not None
                and math.isfinite(value)
            ):
                pools[metric].append(value)

    return pools


def build_year_rank_baseline(
    season: int,
) -> Dict[str, Any]:
    print(
        f"Building pitcher-history rank baseline "
        f"for {season}.",
        flush=True,
    )

    qualified_splits = (
        fetch_season_rank_splits(
            season,
            "QUALIFIED",
        )
    )

    all_splits = fetch_season_rank_splits(
        season,
        "ALL",
    )

    qualified_rows = [
        row
        for split in qualified_splits
        if (
            row := normalize_rank_source(
                split
            )
        )
    ]

    starter_rows = [
        row
        for split in all_splits
        if (
            row := normalize_rank_source(
                split
            )
        )
        and (
            to_int(
                row.get("games_started")
            )
            or 0
        ) > 0
    ]

    return {
        "schema_version": "1.0",
        "season": season,
        "qualified_pitchers":
            len(qualified_rows),
        "starters":
            len(starter_rows),
        "season_pools":
            build_rank_pools(
                qualified_rows,
                "season",
            ),
        "start_pools":
            build_rank_pools(
                starter_rows,
                "start",
            ),
    }


def load_year_rank_baseline(
    season: int,
    current_year: int,
    force: bool,
) -> Dict[str, Any]:
    cached = RANK_CACHE_MEMORY.get(season)

    if cached:
        return cached

    with RANK_CACHE_LOCK:
        cached = RANK_CACHE_MEMORY.get(season)

        if cached:
            return cached

        path = rank_cache_path(season)

        if (
            season < current_year
            and path.exists()
            and not force
        ):
            try:
                document = json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                )

                if isinstance(document, dict):
                    RANK_CACHE_MEMORY[
                        season
                    ] = document

                    return document

            except (
                OSError,
                json.JSONDecodeError,
            ):
                pass

        document = build_year_rank_baseline(
            season
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                document,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )

        RANK_CACHE_MEMORY[season] = document

        return document


def rank_against_pool(
    value: Optional[float],
    pool: List[Any],
    higher_is_better: bool,
) -> Optional[List[Any]]:
    if value is None:
        return None

    clean = []

    for raw_value in pool or []:
        number = to_float(raw_value)

        if number is not None:
            clean.append(number)

    if len(clean) < 2:
        return None

    if higher_is_better:
        better = sum(
            1
            for pool_value in clean
            if pool_value > value
        )
    else:
        better = sum(
            1
            for pool_value in clean
            if pool_value < value
        )

    pool_size = len(clean)

    return [
        max(
            1,
            min(
                better + 1,
                pool_size,
            ),
        ),
        pool_size,
    ]


def attach_history_ranks(
    row: Dict[str, Any],
    season: int,
    mode: str,
    baseline: Dict[str, Any],
) -> None:
    pool_key = (
        "season_pools"
        if mode == "season"
        else "start_pools"
    )

    pools = baseline.get(pool_key) or {}
    ranks: Dict[str, List[Any]] = {}

    for (
        metric,
        higher_is_better,
    ) in HISTORY_RANK_DIRECTIONS.items():
        value = history_rank_value(
            row,
            metric,
            mode,
        )

        result = rank_against_pool(
            value,
            pools.get(metric) or [],
            higher_is_better,
        )

        if result:
            ranks[metric] = [
                result[0],
                result[1],
                season,
                mode,
            ]

    row["ranks"] = ranks


def player_information(pitcher_id: int) -> Dict[str, Any]:
    raw = get_json(f"{MLB_API_BASE}/people/{pitcher_id}")
    people = raw.get("people") or []
    person = people[0] if people else {}

    debut_date = str(person.get("mlbDebutDate") or "")[:10]
    debut_year = to_int(debut_date[:4])
    pitch_hand = person.get("pitchHand") or {}

    return {
        "id": pitcher_id,
        "name": person.get("fullName") or f"Pitcher {pitcher_id}",
        "number": person.get("primaryNumber"),
        "age": person.get("currentAge"),
        "hand": pitch_hand.get("code"),
        "debut_date": debut_date or None,
        "debut_year": debut_year,
        "profile_url": f"pitcher.html?id={pitcher_id}",
        "minor_league_url": f"https://www.milb.com/player/{pitcher_id}",
    }


def season_cache_path(pitcher_id: int, season: int) -> Path:
    return CACHE_DIRECTORY / str(pitcher_id) / f"{season}.json"


def fetch_season_game_log(
    pitcher_id: int,
    season: int,
    current_season: int,
    force: bool,
) -> List[Dict[str, Any]]:
    cache_path = season_cache_path(pitcher_id, season)

    if season < current_season and cache_path.exists() and not force:
        try:
            value = json.loads(cache_path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            pass

    params = urllib.parse.urlencode(
        {
            "stats": "gameLog",
            "group": "pitching",
            "season": season,
        }
    )

    raw = get_json(
        f"{MLB_API_BASE}/people/{pitcher_id}/stats?{params}"
    )

    splits = []

    for group in raw.get("stats") or []:
        for split in group.get("splits") or []:
            if isinstance(split, dict):
                splits.append(split)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(splits, indent=2) + "\n",
        encoding="utf-8",
    )

    return splits


def normalized_game_row(
    split: Dict[str, Any],
    season: int,
    cutoff_date: str,
) -> Optional[Dict[str, Any]]:
    stat = split.get("stat") or {}

    game_date = str(
        split.get("date")
        or split.get("gameDate")
        or ""
    )[:10]

    if not game_date or game_date >= cutoff_date:
        return None

    game = split.get("game") or {}
    opponent = (
        split.get("opponent")
        or split.get("opponentTeam")
        or {}
    )

    home_value = split.get("isHome")

    if isinstance(home_value, bool):
        is_home = home_value
    else:
        home_away = str(
            split.get("homeAway")
            or game.get("homeAway")
            or ""
        ).strip().lower()

        if home_away == "home":
            is_home = True
        elif home_away == "away":
            is_home = False
        else:
            is_home = None

    wins = to_int(stat.get("wins")) or 0
    losses = to_int(stat.get("losses")) or 0

    if wins > 0:
        decision = "W"
    elif losses > 0:
        decision = "L"
    else:
        decision = "ND"

    outs = (
        to_int(stat.get("outs"))
        or to_int(stat.get("outsPitched"))
        or innings_to_outs(stat.get("inningsPitched"))
    )

    hits = to_int(stat.get("hits")) or 0
    runs = to_int(stat.get("runs")) or 0
    earned_runs = to_int(stat.get("earnedRuns")) or 0
    walks = to_int(stat.get("baseOnBalls")) or 0
    strikeouts = to_int(stat.get("strikeOuts")) or 0
    home_runs = to_int(stat.get("homeRuns")) or 0
    games_started = to_int(stat.get("gamesStarted")) or 0

    innings = outs / 3 if outs else 0
    era = round(earned_runs * 9 / innings, 2) if innings else None
    whip = round((hits + walks) / innings, 2) if innings else None

    opponent_abbr = team_abbreviation(opponent)

    return {
        "date": game_date,
        "season": season,
        "game_pk": game.get("gamePk"),
        "is_home": is_home,
        "opponent_abbr": opponent_abbr,
        "opponent_label": (
            opponent_abbr
            if is_home is True
            else f"@{opponent_abbr}"
            if opponent_abbr
            else ""
        ),
        "decision": decision,
        "wins": wins,
        "losses": losses,
        "games_started": games_started,
        "outs": outs,
        "ip": outs_to_innings(outs),
        "hits": hits,
        "runs": runs,
        "earned_runs": earned_runs,
        "walks": walks,
        "strikeouts": strikeouts,
        "home_runs": home_runs,
        "era": era,
        "whip": whip,
    }


def aggregate_rows(
    rows: List[Dict[str, Any]],
    label: str,
) -> Dict[str, Any]:
    totals = {
        "wins": 0,
        "losses": 0,
        "outs": 0,
        "hits": 0,
        "runs": 0,
        "earned_runs": 0,
        "walks": 0,
        "strikeouts": 0,
        "home_runs": 0,
        "games_started": 0,
    }

    for row in rows:
        for key in totals:
            totals[key] += to_int(row.get(key)) or 0

    innings = totals["outs"] / 3 if totals["outs"] else 0

    return {
        "label": label,
        "decision": f"{totals['wins']}-{totals['losses']}",
        "wins": totals["wins"],
        "losses": totals["losses"],
        "games_started": totals["games_started"],
        "outs": totals["outs"],
        "ip": outs_to_innings(totals["outs"]),
        "hits": totals["hits"],
        "runs": totals["runs"],
        "earned_runs": totals["earned_runs"],
        "walks": totals["walks"],
        "strikeouts": totals["strikeouts"],
        "home_runs": totals["home_runs"],
        "era": (
            round(totals["earned_runs"] * 9 / innings, 2)
            if innings
            else None
        ),
        "whip": (
            round(
                (totals["hits"] + totals["walks"]) / innings,
                2,
            )
            if innings
            else None
        ),
    }


def read_pitcher_ids(first_date: str, last_date: str) -> Set[int]:
    pitcher_ids = set()

    for path in sorted(GAMES_DIRECTORY.glob("????-??-??.json")):
        if not (first_date <= path.stem <= last_date):
            continue

        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        for game in document.get("games") or []:
            candidates = []

            pitchers = game.get("pitchers")
            pitchers = (
                pitchers
                if isinstance(pitchers, dict)
                else {}
            )

            for side in ("away", "home"):
                pitcher = pitchers.get(side)

                if isinstance(pitcher, dict):
                    candidates.append(pitcher)

            bullpen_start = game.get(
                "bullpen_start"
            )

            bullpen_start = (
                bullpen_start
                if isinstance(
                    bullpen_start,
                    dict,
                )
                else {}
            )

            for side in ("away", "home"):
                plan = bullpen_start.get(side)

                if not isinstance(plan, dict):
                    continue

                for role in ("opener", "bulk"):
                    pitcher = plan.get(role)

                    if isinstance(pitcher, dict):
                        candidates.append(pitcher)

            for pitcher in candidates:
                pitcher_id = to_int(
                    pitcher.get("id")
                )

                if pitcher_id:
                    pitcher_ids.add(pitcher_id)

    return pitcher_ids


def build_pitcher(
    pitcher_id: int,
    target_date: str,
    force: bool,
) -> Dict[str, Any]:
    current_year = int(target_date[:4])
    person = player_information(pitcher_id)

    debut_year = person.get("debut_year") or max(current_year - 12, 2000)
    all_rows = []
    season_rows = []

    for season in range(int(debut_year), current_year + 1):
        splits = fetch_season_game_log(
            pitcher_id,
            season,
            current_year,
            force,
        )

        normalized = []

        for split in splits:
            row = normalized_game_row(split, season, target_date)
            if row:
                normalized.append(row)

        if not normalized:
            continue

        all_rows.extend(normalized)

        season_summary = aggregate_rows(normalized, str(season))

        if season_summary.get("outs", 0) > 0:
            season_summary["season"] = season
            season_rows.append(season_summary)

    all_rows.sort(
        key=lambda row: (
            row.get("date") or "",
            row.get("game_pk") or 0,
        ),
        reverse=True,
    )

    starts = [
        row
        for row in all_rows
        if (to_int(row.get("games_started")) or 0) > 0
    ]

    recent_seasons = sorted(
        season_rows,
        key=lambda row: row.get("season") or 0,
        reverse=True,
    )[:3]

    years_needed = sorted(
        {
            int(row.get("season"))
            for row in (
                list(recent_seasons)
                + list(starts)
            )
            if to_int(row.get("season"))
        }
    )

    rank_baselines = {}

    for season in years_needed:
        try:
            rank_baselines[season] = (
                load_year_rank_baseline(
                    season,
                    current_year,
                    force,
                )
            )
        except Exception as error:
            print(
                "Pitcher-history rank baseline "
                f"failed for {season}: {error}",
                flush=True,
            )

    for row in recent_seasons:
        season = to_int(row.get("season"))
        baseline = rank_baselines.get(
            season
        )

        if season and baseline:
            attach_history_ranks(
                row,
                season,
                "season",
                baseline,
            )

    for row in starts:
        season = to_int(row.get("season"))
        baseline = rank_baselines.get(
            season
        )

        if season and baseline:
            attach_history_ranks(
                row,
                season,
                "start",
                baseline,
            )

    header_season = next(
        (
            row
            for row in recent_seasons
            if row.get("season") == current_year
        ),
        None,
    )

    if header_season is None:
        header_season = recent_seasons[0] if recent_seasons else {}

    current_season_starts = sum(
        1
        for row in starts
        if row.get("season") == current_year
    )

    debut_year_value = to_int(person.get("debut_year"))

    rookie_candidate = (
        0 < len(starts) < 7
        and current_season_starts > 0
        and (
            debut_year_value is None
            or debut_year_value >= current_year - 1
        )
    )

    return {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        "as_of": target_date,
        "pitcher": {
            **person,
            "record": header_season.get("decision") or "0-0",
            "era": header_season.get("era"),
            "season": header_season.get("season"),
        },
        "recent_seasons": recent_seasons,
        "last_starts": starts[:7],
        "starts": starts,
        "career_start_count": len(starts),
        "rookie_candidate": rookie_candidate,
    }



def ensure_payload_history_ranks(
    payload: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    as_of = str(
        payload.get("as_of")
        or datetime.now(EASTERN)
            .date()
            .isoformat()
    )

    try:
        current_year = int(as_of[:4])
    except (TypeError, ValueError):
        current_year = datetime.now(
            EASTERN
        ).year

    recent_seasons = (
        payload.get("recent_seasons")
        or []
    )

    starts = (
        payload.get("starts")
        or []
    )

    years_needed = sorted(
        {
            season
            for row in (
                list(recent_seasons)
                + list(starts)
            )
            if (
                season := to_int(
                    row.get("season")
                )
            )
        }
    )

    baselines = {}

    for season in years_needed:
        try:
            baselines[season] = (
                load_year_rank_baseline(
                    season,
                    current_year,
                    force,
                )
            )
        except Exception as error:
            print(
                "Unable to load pitcher-history "
                f"rank baseline for {season}: "
                f"{error}",
                flush=True,
            )

    for row in recent_seasons:
        season = to_int(
            row.get("season")
        )

        baseline = baselines.get(season)

        if season and baseline:
            attach_history_ranks(
                row,
                season,
                "season",
                baseline,
            )

    for row in starts:
        season = to_int(
            row.get("season")
        )

        baseline = baselines.get(season)

        if season and baseline:
            attach_history_ranks(
                row,
                season,
                "start",
                baseline,
            )

    # last_starts must contain the newly ranked
    # versions of the same first seven starts.
    payload["last_starts"] = [
        dict(row)
        for row in starts[:7]
    ]

    # Clamp older rank formats too.
    for row in (
        list(recent_seasons)
        + list(starts)
        + list(
            payload.get("last_starts")
            or []
        )
    ):
        ranks = row.get("ranks") or {}

        for rank_value in ranks.values():
            if (
                isinstance(rank_value, list)
                and len(rank_value) >= 2
            ):
                try:
                    rank = int(rank_value[0])
                    pool_size = int(
                        rank_value[1]
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if pool_size > 0:
                    rank_value[0] = max(
                        1,
                        min(
                            rank,
                            pool_size,
                        ),
                    )

            elif isinstance(
                rank_value,
                dict,
            ):
                try:
                    rank = int(
                        rank_value.get("rank")
                        or 0
                    )

                    pool_size = int(
                        rank_value.get(
                            "pool_size"
                        )
                        or rank_value.get(
                            "poolSize"
                        )
                        or 0
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                if rank > 0 and pool_size > 0:
                    rank_value["rank"] = max(
                        1,
                        min(
                            rank,
                            pool_size,
                        ),
                    )

    payload["schema_version"] = "1.1"

    return payload


def write_pitcher_file(
    pitcher_id: int,
    payload: Dict[str, Any],
) -> None:
    payload = ensure_payload_history_ranks(
        payload,
        False,
    )
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    destination = OUTPUT_DIRECTORY / f"{pitcher_id}.json"
    temporary = destination.with_suffix(".json.tmp")

    temporary.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def main() -> int:
    args = parse_args()

    first = datetime.strptime(args.date, "%Y-%m-%d").date()
    last = first + timedelta(days=args.days_ahead)

    pitcher_ids = sorted(
        read_pitcher_ids(
            first.isoformat(),
            last.isoformat(),
        )
    )

    print(
        "Pitcher history candidates:",
        len(pitcher_ids),
        flush=True,
    )

    if not pitcher_ids:
        return 0

    failures = 0

    with ThreadPoolExecutor(
        max_workers=max(1, min(args.workers, 8))
    ) as executor:
        futures = {
            executor.submit(
                build_pitcher,
                pitcher_id,
                args.date,
                args.force,
            ): pitcher_id
            for pitcher_id in pitcher_ids
        }

        completed = 0

        for future in as_completed(futures):
            pitcher_id = futures[future]
            completed += 1

            try:
                payload = future.result()
                write_pitcher_file(pitcher_id, payload)

                print(
                    f"Pitcher history {completed}/{len(futures)}: "
                    f"{payload['pitcher']['name']} "
                    f"({len(payload['starts'])} career starts)",
                    flush=True,
                )

            except Exception as error:
                failures += 1
                print(
                    f"Pitcher history failed {pitcher_id}: {error}",
                    flush=True,
                )

    print()
    print("Pitcher history build complete.")
    print("Files:", len(pitcher_ids) - failures)
    print("Failures:", failures)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
