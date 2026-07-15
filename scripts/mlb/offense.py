from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
import json
import sys
import urllib.parse
import urllib.request


MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

OFFENSE_METRICS = (
    "AVG",
    "wRC+",
    "K%",
    "BB%",
    "OBP",
    "OPS",
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
    params: dict[str, Any] = {
        "stats": stat_type,
        "group": "hitting",
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
    target = datetime.strptime(
        target_date,
        "%Y-%m-%d",
    ).date()

    season = target.year

    season_all = fetch_team_hitting_stats(
        team_id=team_id,
        stat_type="season",
        season=season,
    )

    last_7_all = fetch_team_hitting_stats(
        team_id=team_id,
        stat_type="byDateRange",
        season=season,
        start_date=(
            target - timedelta(days=7)
        ).isoformat(),
        end_date=target.isoformat(),
    )

    last_30_all = fetch_team_hitting_stats(
        team_id=team_id,
        stat_type="byDateRange",
        season=season,
        start_date=(
            target - timedelta(days=30)
        ).isoformat(),
        end_date=target.isoformat(),
    )

    versus_left = fetch_safe_split(
        team_id,
        season,
        "vl",
    )

    versus_right = fetch_safe_split(
        team_id,
        season,
        "vr",
    )

    hand = str(
        opponent_throws or ""
    ).upper()

    versus_hand = (
        versus_left
        if hand == "L"
        else versus_right
        if hand == "R"
        else {}
    )

    return {
        "team_id": team_id,
        "opponent_throws":
            hand or None,
        "stats": {
            "last_7": {
                "all": build_metric_block(
                    last_7_all,
                    versus_hand,
                ),
                "home": {},
                "away": {},
            },
            "last_30": {
                "all": build_metric_block(
                    last_30_all,
                    versus_hand,
                ),
                "home": {},
                "away": {},
            },
            "season": {
                "all": build_metric_block(
                    season_all,
                    versus_hand,
                ),
                "home": {},
                "away": {},
            },
        },
        "raw_splits": {
            "vs_lhp": versus_left,
            "vs_rhp": versus_right,
        },
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
