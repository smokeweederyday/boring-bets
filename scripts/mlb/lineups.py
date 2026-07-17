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


def expected_batting_side(bats: str | None, pitcher_throws: str | None) -> str | None:
    bats_code = str(bats or "").upper()
    throws_code = str(pitcher_throws or "").upper()
    if bats_code in ("L", "R"):
        return bats_code
    if bats_code == "S":
        if throws_code == "R":
            return "L"
        if throws_code == "L":
            return "R"
    return None


def lineup_signature(players: list[dict[str, Any]]) -> str:
    ordered = sorted(players, key=lambda player: (player.get("order") or 99))
    return "|".join(
        f"{player.get('order') or 0}:{player.get('id') or player.get('name') or '?'}"
        for player in ordered[:9]
    )


def classify_lineup_status(player_count: int, source_confirmed: bool = False) -> tuple[str, str, float]:
    if player_count <= 0:
        return "unknown", "Lineup Unknown", 0.0
    if source_confirmed and player_count >= 9:
        return "confirmed", "Confirmed Lineup", 1.0
    if player_count >= 9:
        return "projected", "Projected Lineup", 0.75
    return "partial", f"Partial Lineup ({player_count}/9)", round(min(0.7, player_count / 9), 2)


def annotate_lineup_for_pitcher(
    lineup: dict[str, Any],
    pitcher_throws: str | None,
) -> dict[str, Any]:
    annotated = dict(lineup or {})
    players = []
    left = right = unknown = switch = 0
    for raw_player in annotated.get("players") or []:
        player = dict(raw_player)
        bats = normalize_bats(player.get("bats"))
        matchup_bats = expected_batting_side(bats, pitcher_throws)
        player["bats"] = bats
        player["matchup_bats"] = matchup_bats
        player["is_switch_hitter"] = bats == "S"
        if bats == "S":
            switch += 1
        if matchup_bats == "L":
            left += 1
        elif matchup_bats == "R":
            right += 1
        else:
            unknown += 1
        players.append(player)

    annotated["players"] = players
    annotated["opposing_pitcher_throws"] = str(pitcher_throws or "").upper() or None
    annotated["matchup_handedness"] = {
        "lhh": left,
        "rhh": right,
        "unknown": unknown,
        "switch_hitters": switch,
        "counted": left + right,
    }
    annotated["signature"] = lineup_signature(players)
    return annotated

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

    player_count = len(parsed_players)
    # A battingOrder supplied by MLB's live game feed is authoritative once all
    # nine positions are present. Partial orders are explicitly marked partial.
    status, status_label, confidence = classify_lineup_status(
        player_count,
        source_confirmed=player_count >= 9,
    )

    return {
        "team": (
            team.get("abbreviation")
            or team.get("name")
        ),
        "team_id": team.get("id"),
        "status": status,
        "status_label": status_label,
        "completeness": {
            "count": player_count,
            "expected": 9,
            "ratio": round(player_count / 9, 3) if player_count else 0.0,
        },
        "confidence": confidence,
        "source": "MLB live game feed",
        "last_updated": datetime.now(
            timezone.utc
        ).isoformat(),
        "players": parsed_players,
        "signature": lineup_signature(parsed_players),
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
