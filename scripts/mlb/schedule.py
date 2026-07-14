from __future__ import annotations

import json
import urllib.request
from typing import Any


MLB_SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1"
    "&date={date}"
    "&hydrate=probablePitcher,venue"
)

TEAM_ABBR = {
    108: "LAA",
    109: "ARI",
    110: "BAL",
    111: "BOS",
    112: "CHC",
    113: "CIN",
    114: "CLE",
    115: "COL",
    116: "DET",
    117: "HOU",
    118: "KC",
    119: "LAD",
    120: "WSH",
    121: "NYM",
    133: "ATH",
    134: "PIT",
    135: "SD",
    136: "SEA",
    137: "SFG",
    138: "STL",
    139: "TB",
    140: "TEX",
    141: "TOR",
    142: "MIN",
    143: "PHI",
    144: "ATL",
    145: "CWS",
    146: "MIA",
    147: "NYY",
    158: "MIL",
}


def fetch_schedule(date: str) -> dict[str, Any]:
    """Fetch one date of MLB schedule data."""

    url = MLB_SCHEDULE_URL.format(date=date)

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
        return json.loads(response.read())


def parse_schedule(
    raw: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert the MLB response into compact game records."""

    games: list[dict[str, Any]] = []

    for date_block in raw.get("dates", []):
        game_date = date_block.get("date")

        for game in date_block.get("games", []):
            away = game.get("teams", {}).get("away", {})
            home = game.get("teams", {}).get("home", {})

            away_team = away.get("team", {})
            home_team = home.get("team", {})

            away_id = away_team.get("id")
            home_id = home_team.get("id")

            away_abbr = TEAM_ABBR.get(
                away_id,
                away_team.get("abbreviation", "AWAY"),
            )

            home_abbr = TEAM_ABBR.get(
                home_id,
                home_team.get("abbreviation", "HOME"),
            )

            games.append(
                {
                    "mlb_game_pk": game.get("gamePk"),
                    "id": create_game_id(
                        game_date,
                        away_abbr,
                        home_abbr,
                    ),
                    "date": game_date,
                    "game_time": game.get("gameDate"),
                    "status": normalize_status(
                        game.get("status", {})
                    ),
                    "venue": {
                        "id": game.get("venue", {}).get("id"),
                        "name": game.get("venue", {}).get("name"),
                    },
                    "away_team": {
                        "abbr": away_abbr,
                        "name": away_team.get("name"),
                        "team_id": away_id,
                    },
                    "home_team": {
                        "abbr": home_abbr,
                        "name": home_team.get("name"),
                        "team_id": home_id,
                    },
                    "pitchers": {
                        "away": parse_probable_pitcher(
                            away.get("probablePitcher")
                        ),
                        "home": parse_probable_pitcher(
                            home.get("probablePitcher")
                        ),
                    },
                }
            )

    return games


def parse_probable_pitcher(
    pitcher: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize a probable pitcher, or return a safe TBD record."""

    if not pitcher:
        return {
            "id": None,
            "name": "Starter TBD",
            "status": "unknown",
        }

    return {
        "id": pitcher.get("id"),
        "name": pitcher.get("fullName", "Starter TBD"),
        "status": "probable",
    }


def normalize_status(
    status: dict[str, Any],
) -> str:
    """Convert MLB's detailed status into a stable site status."""

    abstract = str(
        status.get("abstractGameState", "")
    ).lower()

    detailed = str(
        status.get("detailedState", "")
    ).lower()

    if abstract == "live":
        return "live"

    if abstract == "final":
        return "final"

    if "postponed" in detailed:
        return "postponed"

    if "cancelled" in detailed:
        return "cancelled"

    return "scheduled"


def create_game_id(
    date: str | None,
    away_abbr: str,
    home_abbr: str,
) -> str:
    return "-".join(
        [
            str(date or "unknown-date"),
            away_abbr.lower(),
            home_abbr.lower(),
        ]
    )