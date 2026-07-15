from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
import json
import sys
import urllib.parse
import urllib.request


MLB_API_BASE = "https://statsapi.mlb.com/api/v1"


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


def fetch_team_pitching_stats(
    team_id: int,
    stat_type: str,
    season: int,
    start_date: str | None = None,
    end_date: str | None = None,
    sit_code: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "stats": stat_type,
        "group": "pitching",
        "season": season,
    }

    if start_date:
        params["startDate"] = start_date

    if end_date:
        params["endDate"] = end_date

    if sit_code:
        params["sitCodes"] = sit_code

    query = urllib.parse.urlencode(
        params
    )

    raw = get_json(
        f"{MLB_API_BASE}/teams/"
        f"{team_id}/stats?{query}"
    )

    return parse_pitching_stat_block(
        raw
    )


def parse_pitching_stat_block(
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

        return normalize_pitching_stat(
            stat
        )

    return {}


def normalize_pitching_stat(
    stat: dict[str, Any],
) -> dict[str, Any]:
    return {
        "era": to_float(
            stat.get("era")
        ),
        "whip": to_float(
            stat.get("whip")
        ),
        "fip": None,
        "innings_pitched":
            stat.get("inningsPitched"),
        "games": to_int(
            stat.get("gamesPlayed")
            or stat.get("gamesPitched")
        ),
        "wins": to_int(
            stat.get("wins")
        ),
        "losses": to_int(
            stat.get("losses")
        ),
        "saves": to_int(
            stat.get("saves")
        ),
        "save_opportunities": to_int(
            stat.get("saveOpportunities")
        ),
        "strikeouts": to_int(
            stat.get("strikeOuts")
        ),
        "walks": to_int(
            stat.get("baseOnBalls")
        ),
        "hits": to_int(
            stat.get("hits")
        ),
        "home_runs": to_int(
            stat.get("homeRuns")
        ),
        "earned_runs": to_int(
            stat.get("earnedRuns")
        ),
    }


def fetch_relief_split(
    team_id: int,
    season: int,
) -> dict[str, Any]:
    return fetch_team_pitching_stats(
        team_id=team_id,
        stat_type="statSplits",
        season=season,
        sit_code="rp",
    )


def fetch_team_games(
    team_id: int,
    game_date: str,
) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "sportId": 1,
            "teamId": team_id,
            "date": game_date,
        }
    )

    raw = get_json(
        f"{MLB_API_BASE}/schedule?{params}"
    )

    games: list[dict[str, Any]] = []

    for date_block in raw.get(
        "dates",
        [],
    ):
        games.extend(
            date_block.get(
                "games",
                [],
            )
        )

    return games


def fetch_boxscore(
    game_pk: int,
) -> dict[str, Any]:
    return get_json(
        f"{MLB_API_BASE}/game/"
        f"{game_pk}/boxscore"
    )


def find_team_side(
    boxscore: dict[str, Any],
    team_id: int,
) -> str | None:
    teams = boxscore.get(
        "teams",
        {},
    )

    for side in ("away", "home"):
        side_team_id = (
            teams
            .get(side, {})
            .get("team", {})
            .get("id")
        )

        if side_team_id == team_id:
            return side

    return None


def extract_relief_appearances(
    boxscore: dict[str, Any],
    team_id: int,
) -> list[dict[str, Any]]:
    side = find_team_side(
        boxscore,
        team_id,
    )

    if not side:
        return []

    team_box = (
        boxscore
        .get("teams", {})
        .get(side, {})
    )

    pitcher_ids = team_box.get(
        "pitchers",
        [],
    )

    players = team_box.get(
        "players",
        {},
    )

    appearances = []

    for pitcher_id in pitcher_ids:
        player = players.get(
            f"ID{pitcher_id}",
            {},
        )

        pitching = (
            player
            .get("stats", {})
            .get("pitching", {})
        )

        games_started = to_int(
            pitching.get("gamesStarted")
        ) or 0

        outs = to_int(
            pitching.get("outs")
        ) or 0

        batters_faced = to_int(
            pitching.get("battersFaced")
        ) or 0

        if (
            games_started > 0
            or (
                outs <= 0
                and batters_faced <= 0
            )
        ):
            continue

        person = player.get(
            "person",
            {},
        )

        appearances.append(
            {
                "id": pitcher_id,
                "name": person.get(
                    "fullName",
                    f"Pitcher {pitcher_id}",
                ),
                "outs": outs,
                "innings_pitched":
                    pitching.get(
                        "inningsPitched"
                    ),
                "pitches": to_int(
                    pitching.get(
                        "numberOfPitches"
                    )
                ),
                "batters_faced":
                    batters_faced,
            }
        )

    return appearances


def fetch_relief_usage_for_date(
    team_id: int,
    game_date: str,
) -> list[dict[str, Any]]:
    appearances_by_id: dict[
        int,
        dict[str, Any],
    ] = {}

    for game in fetch_team_games(
        team_id,
        game_date,
    ):
        status = str(
            game
            .get("status", {})
            .get("abstractGameState", "")
        ).lower()

        if status not in {
            "final",
            "live",
        }:
            continue

        game_pk = game.get(
            "gamePk"
        )

        if not game_pk:
            continue

        try:
            boxscore = fetch_boxscore(
                int(game_pk)
            )
        except Exception as error:
            print(
                f"Could not load boxscore "
                f"{game_pk}: {error}"
            )
            continue

        for appearance in (
            extract_relief_appearances(
                boxscore,
                team_id,
            )
        ):
            appearances_by_id[
                appearance["id"]
            ] = appearance

    return list(
        appearances_by_id.values()
    )


def build_bullpen_usage(
    team_id: int,
    target_date: str,
) -> dict[str, Any]:
    target = datetime.strptime(
        target_date,
        "%Y-%m-%d",
    ).date()

    yesterday = (
        target - timedelta(days=1)
    ).isoformat()

    two_days_ago = (
        target - timedelta(days=2)
    ).isoformat()

    used_yesterday = (
        fetch_relief_usage_for_date(
            team_id,
            yesterday,
        )
    )

    used_two_days_ago = (
        fetch_relief_usage_for_date(
            team_id,
            two_days_ago,
        )
    )

    yesterday_ids = {
        pitcher["id"]
        for pitcher in used_yesterday
    }

    two_days_ago_ids = {
        pitcher["id"]
        for pitcher in used_two_days_ago
    }

    back_to_back_ids = (
        yesterday_ids
        & two_days_ago_ids
    )

    return {
        "used_yesterday":
            len(yesterday_ids),
        "back_to_back":
            len(back_to_back_ids),
        "fresh_leverage":
            None,
        "usage": {
            "yesterday_date":
                yesterday,
            "two_days_ago_date":
                two_days_ago,
            "used_yesterday":
                used_yesterday,
            "used_two_days_ago":
                used_two_days_ago,
            "back_to_back_pitcher_ids":
                sorted(
                    back_to_back_ids
                ),
        },
    }


def build_bullpen_snapshot(
    team_id: int,
    target_date: str,
) -> dict[str, Any]:
    target = datetime.strptime(
        target_date,
        "%Y-%m-%d",
    ).date()

    season = target.year

    season_relief = fetch_relief_split(
        team_id,
        season,
    )

    last_7 = fetch_team_pitching_stats(
        team_id=team_id,
        stat_type="byDateRange",
        season=season,
        start_date=(
            target - timedelta(days=7)
        ).isoformat(),
        end_date=target.isoformat(),
        sit_code="rp",
    )

    last_30 = fetch_team_pitching_stats(
        team_id=team_id,
        stat_type="byDateRange",
        season=season,
        start_date=(
            target - timedelta(days=30)
        ).isoformat(),
        end_date=target.isoformat(),
        sit_code="rp",
    )

    try:
        usage = build_bullpen_usage(
            team_id,
            target_date,
        )
    except Exception as error:
        print(
            "Bullpen usage unavailable "
            f"for team {team_id}: {error}"
        )

        usage = {
            "used_yesterday": None,
            "back_to_back": None,
            "fresh_leverage": None,
            "usage": {},
        }

    return {
        "team_id": team_id,
        "stats": {
            "last_7": {
                "all": last_7,
                "home": {},
                "away": {},
            },
            "last_30": {
                "all": last_30,
                "home": {},
                "away": {},
            },
            "season": {
                "all": season_relief,
                "home": {},
                "away": {},
            },
        },
        "used_yesterday":
            usage.get(
                "used_yesterday"
            ),
        "back_to_back":
            usage.get(
                "back_to_back"
            ),
        "fresh_leverage":
            usage.get(
                "fresh_leverage"
            ),
        "usage":
            usage.get(
                "usage",
                {},
            ),
        "notes": "",
        "details_url": "#",
    }


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
            "Usage: python3 scripts/mlb/bullpen.py "
            "<team_id> [YYYY-MM-DD]"
        )

    team_id = int(
        sys.argv[1]
    )

    target_date = (
        sys.argv[2]
        if len(sys.argv) > 2
        else date.today().isoformat()
    )

    snapshot = build_bullpen_snapshot(
        team_id,
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
