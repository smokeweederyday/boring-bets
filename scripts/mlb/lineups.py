from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json
import sys
import urllib.request


MLB_API_BASE = "https://statsapi.mlb.com/api/v1.1"


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


def fetch_live_game(
    game_pk: int,
) -> dict[str, Any]:
    return get_json(
        f"{MLB_API_BASE}/game/"
        f"{game_pk}/feed/live"
    )


def normalize_batting_order(
    value: Any,
) -> int | None:
    try:
        number = int(value)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if number >= 100:
        return number // 100

    if 1 <= number <= 9:
        return number

    return None


def normalize_bats(
    value: Any,
) -> str | None:
    if isinstance(value, dict):
        code = value.get("code")

        if code:
            return str(code).upper()

    if isinstance(value, str):
        cleaned = value.strip().upper()

        if cleaned:
            return cleaned

    return None


def extract_player_bats(
    boxscore_player: dict[str, Any],
    game_player: dict[str, Any],
) -> str | None:
    """
    MLB usually stores batting side in gameData.players,
    not inside the team boxscore player object.
    """

    candidates = (
        game_player.get("batSide"),
        game_player
        .get("person", {})
        .get("batSide"),
        boxscore_player.get("batSide"),
        boxscore_player
        .get("person", {})
        .get("batSide"),
    )

    for candidate in candidates:
        bats = normalize_bats(
            candidate
        )

        if bats:
            return bats

    return None


def parse_lineup_side(
    team_box: dict[str, Any],
    team: dict[str, Any],
    game_players: dict[str, Any],
) -> dict[str, Any]:
    boxscore_players = team_box.get(
        "players",
        {},
    )

    batting_order = team_box.get(
        "battingOrder",
        [],
    )

    parsed_players = []

    for index, player_id in enumerate(
        batting_order
    ):
        player_key = f"ID{player_id}"

        boxscore_player = (
            boxscore_players.get(
                player_key,
                {},
            )
        )

        game_player = (
            game_players.get(
                player_key,
                {},
            )
        )

        person = (
            game_player
            or boxscore_player.get(
                "person",
                {},
            )
        )

        all_positions = (
            boxscore_player.get(
                "allPositions"
            )
            or []
        )

        position = (
            boxscore_player.get(
                "position",
                {},
            )
            or (
                all_positions[0]
                if all_positions
                else {}
            )
        )

        batting_order_value = (
            boxscore_player
            .get("stats", {})
            .get("batting", {})
            .get("battingOrder")
        )

        order = (
            normalize_batting_order(
                batting_order_value
            )
            or index + 1
        )

        parsed_players.append(
            {
                "id": (
                    game_player.get("id")
                    or person.get("id")
                    or player_id
                ),
                "name": (
                    game_player.get(
                        "fullName"
                    )
                    or person.get(
                        "fullName"
                    )
                    or f"Player {player_id}"
                ),
                "position": (
                    position.get(
                        "abbreviation"
                    )
                    or position.get(
                        "code"
                    )
                    or "—"
                ),
                "bats": extract_player_bats(
                    boxscore_player,
                    game_player,
                ),
                "order": order,
            }
        )

    parsed_players.sort(
        key=lambda player: (
            player.get("order") or 99,
            player.get("name") or "",
        )
    )

    confirmed = (
        len(parsed_players) >= 9
    )

    return {
        "team": (
            team.get("abbreviation")
            or team.get("name")
        ),
        "team_id": team.get("id"),
        "status": (
            "confirmed"
            if confirmed
            else "projected"
        ),
        "status_label": (
            "Confirmed Lineup"
            if confirmed
            else "Projected Lineup"
        ),
        "last_updated": datetime.now(
            timezone.utc
        ).isoformat(),
        "players": parsed_players,
    }


def build_lineup_snapshot(
    game_pk: int,
) -> dict[str, Any]:
    raw = fetch_live_game(
        game_pk
    )

    game_data = raw.get(
        "gameData",
        {},
    )

    live_data = raw.get(
        "liveData",
        {},
    )

    teams = game_data.get(
        "teams",
        {},
    )

    game_players = game_data.get(
        "players",
        {},
    )

    boxscore_teams = (
        live_data
        .get("boxscore", {})
        .get("teams", {})
    )

    away_team = teams.get(
        "away",
        {},
    )

    home_team = teams.get(
        "home",
        {},
    )

    return {
        "mlb_game_pk": game_pk,
        "away": parse_lineup_side(
            boxscore_teams.get(
                "away",
                {},
            ),
            away_team,
            game_players,
        ),
        "home": parse_lineup_side(
            boxscore_teams.get(
                "home",
                {},
            ),
            home_team,
            game_players,
        ),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python3 scripts/mlb/lineups.py "
            "<mlb_game_pk>"
        )

    game_pk = int(
        sys.argv[1]
    )

    snapshot = build_lineup_snapshot(
        game_pk
    )

    print(
        json.dumps(
            snapshot,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
