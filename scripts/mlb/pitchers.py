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


def fetch_pitcher_profile(
    pitcher_id: int,
) -> dict[str, Any]:
    """Fetch biographical information for one pitcher."""

    raw = get_json(
        f"{MLB_API_BASE}/people/{pitcher_id}"
    )

    people = raw.get("people", [])

    if not people:
        return {
            "id": pitcher_id,
            "name": "Starter TBD",
            "age": None,
            "throws": None,
        }

    person = people[0]

    pitch_hand = person.get(
        "pitchHand",
        {},
    )

    return {
        "id": person.get(
            "id",
            pitcher_id,
        ),
        "name": person.get(
            "fullName",
            "Starter TBD",
        ),
        "age": person.get(
            "currentAge"
        ),
        "throws": pitch_hand.get(
            "code"
        ),
    }


def fetch_pitching_stats(
    pitcher_id: int,
    stat_type: str,
    season: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    Fetch one MLB pitching-stat split.

    Supported initial stat types:
    - season
    - byDateRange
    """

    params: dict[str, Any] = {
        "stats": stat_type,
        "group": "pitching",
        "season": season,
    }

    if start_date:
        params["startDate"] = start_date

    if end_date:
        params["endDate"] = end_date

    query = urllib.parse.urlencode(
        params
    )

    raw = get_json(
        f"{MLB_API_BASE}/people/"
        f"{pitcher_id}/stats?{query}"
    )

    return parse_pitching_stat_block(raw)


def parse_pitching_stat_block(
    raw: dict[str, Any],
) -> dict[str, Any]:
    stats_groups = raw.get(
        "stats",
        [],
    )

    for group in stats_groups:
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

        return {
            "era": to_float(
                stat.get("era")
            ),
            "whip": to_float(
                stat.get("whip")
            ),
            "fip": None,
            "xfip": None,
            "avg_against": to_float(
                stat.get("avg")
                or stat.get("avgAgainst")
            ),
            "innings_pitched":
                stat.get("inningsPitched"),
            "games_started": to_int(
                stat.get("gamesStarted")
            ),
            "strikeouts": to_int(
                stat.get("strikeOuts")
            ),
            "walks": to_int(
                stat.get("baseOnBalls")
            ),
            "home_runs": to_int(
                stat.get("homeRuns")
            ),
        }

    return {}


def build_pitcher_snapshot(
    pitcher_id: int,
    target_date: str,
) -> dict[str, Any]:
    """
    Build the first useful Boring Bets pitcher object:
    profile + season + last 7 days + last 30 days.
    """

    target = datetime.strptime(
        target_date,
        "%Y-%m-%d",
    ).date()

    season = target.year

    profile = fetch_pitcher_profile(
        pitcher_id
    )

    season_stats = fetch_pitching_stats(
        pitcher_id=pitcher_id,
        stat_type="season",
        season=season,
    )

    last_7_stats = fetch_pitching_stats(
        pitcher_id=pitcher_id,
        stat_type="byDateRange",
        season=season,
        start_date=(
            target - timedelta(days=7)
        ).isoformat(),
        end_date=target.isoformat(),
    )

    last_30_stats = fetch_pitching_stats(
        pitcher_id=pitcher_id,
        stat_type="byDateRange",
        season=season,
        start_date=(
            target - timedelta(days=30)
        ).isoformat(),
        end_date=target.isoformat(),
    )

    return {
        **profile,
        "status": "probable",
        "profile_url": (
            f"pitcher.html?id={pitcher_id}"
        ),
        "stats": {
            "last_7": {
                "all": last_7_stats,
                "home": {},
                "away": {},
            },
            "last_30": {
                "all": last_30_stats,
                "home": {},
                "away": {},
            },
            "season": {
                "all": season_stats,
                "home": {},
                "away": {},
            },
            "vs_lhh": {},
            "vs_rhh": {},
        },
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
            "Usage: python3 scripts/mlb/pitchers.py "
            "<pitcher_id> [YYYY-MM-DD]"
        )

    pitcher_id = int(
        sys.argv[1]
    )

    target_date = (
        sys.argv[2]
        if len(sys.argv) > 2
        else date.today().isoformat()
    )

    snapshot = build_pitcher_snapshot(
        pitcher_id,
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
