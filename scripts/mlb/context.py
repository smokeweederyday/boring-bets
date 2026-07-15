from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
GAMES_FILE = ROOT / "data/games.json"


def load_games() -> list[dict[str, Any]]:
    if not GAMES_FILE.exists():
        return []

    payload = json.loads(
        GAMES_FILE.read_text(
            encoding="utf-8"
        )
    )

    games = payload.get(
        "games",
        [],
    )

    return (
        games
        if isinstance(games, list)
        else []
    )


def build_context_snapshot(
    game: dict[str, Any],
) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    positives: list[dict[str, Any]] = []
    negatives: list[dict[str, Any]] = []
    information: list[dict[str, Any]] = []

    evaluate_lineups(
        game,
        alerts,
        positives,
        negatives,
        information,
    )

    evaluate_starters(
        game,
        alerts,
        positives,
        negatives,
        information,
    )

    evaluate_pitcher_form(
        game,
        positives,
        negatives,
        information,
    )

    evaluate_offenses(
        game,
        positives,
        negatives,
        information,
    )

    evaluate_bullpens(
        game,
        alerts,
        positives,
        negatives,
        information,
    )

    evaluate_weather(
        game,
        alerts,
        positives,
        negatives,
        information,
    )

    evaluate_market(
        game,
        alerts,
        positives,
        negatives,
        information,
    )

    score = calculate_context_score(
        alerts,
        positives,
        negatives,
    )

    return {
        "version": "2.0",
        "score": score,
        "label": score_label(score),
        "alerts": alerts,
        "positives": positives,
        "negatives": negatives,
        "information": information,
        "sources": {
            "lineups": True,
            "starters": True,
            "pitcher_form": True,
            "offense": True,
            "bullpens": True,
            "weather": True,
            "market": True,
            "travel": False,
            "trade_deadline": False,
            "standings": False,
            "streaks": False,
            "injuries": False,
        },
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def evaluate_lineups(
    game: dict[str, Any],
    alerts: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    lineups = game.get("lineups", {})
    confirmed = 0

    for side, team_key in (
        ("away", "away_team"),
        ("home", "home_team"),
    ):
        team = (
            game.get(team_key, {}).get("abbr")
            or side.upper()
        )

        lineup = lineups.get(side, {})
        players = lineup.get("players", [])

        is_confirmed = (
            lineup.get("status") == "confirmed"
            and isinstance(players, list)
            and len(players) >= 9
        )

        if is_confirmed:
            confirmed += 1
            positives.append(
                context_item(
                    f"{team} LINEUP CONFIRMED",
                    "The batting order is confirmed.",
                    "good",
                    3,
                    team,
                    "lineup",
                )
            )
        else:
            negatives.append(
                context_item(
                    f"{team} LINEUP UNCONFIRMED",
                    "The batting order remains projected or unavailable.",
                    "negative",
                    -3,
                    team,
                    "lineup",
                )
            )

    if confirmed == 0:
        alerts.append(
            context_item(
                "BOTH LINEUPS UNCONFIRMED",
                "Both batting orders remain projected or unavailable.",
                "caution",
                -5,
                None,
                "lineup",
            )
        )
    elif confirmed == 1:
        information.append(
            context_item(
                "ONE LINEUP CONFIRMED",
                "One club has confirmed its batting order.",
                "info",
                0,
                None,
                "lineup",
            )
        )


def evaluate_starters(
    game: dict[str, Any],
    alerts: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    pitchers = game.get("pitchers", {})
    known = 0

    for side, team_key in (
        ("away", "away_team"),
        ("home", "home_team"),
    ):
        team = (
            game.get(team_key, {}).get("abbr")
            or side.upper()
        )

        pitcher = pitchers.get(side, {})

        if pitcher.get("id"):
            known += 1
            positives.append(
                context_item(
                    f"{team} STARTER SET",
                    f"{pitcher.get('name') or 'Probable starter'} is available.",
                    "good",
                    2,
                    team,
                    "starter",
                )
            )
        else:
            negatives.append(
                context_item(
                    f"{team} STARTER TBD",
                    "The probable starter is still unavailable.",
                    "negative",
                    -4,
                    team,
                    "starter",
                )
            )

    if known == 0:
        alerts.append(
            context_item(
                "STARTERS TBD",
                "Neither probable starter is currently available.",
                "warning",
                -8,
                None,
                "starter",
            )
        )
    elif known == 1:
        alerts.append(
            context_item(
                "ONE STARTER TBD",
                "One probable starter is still unavailable.",
                "caution",
                -4,
                None,
                "starter",
            )
        )


def evaluate_pitcher_form(
    game: dict[str, Any],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    for side, team_key in (
        ("away", "away_team"),
        ("home", "home_team"),
    ):
        team = (
            game.get(team_key, {}).get("abbr")
            or side.upper()
        )

        pitcher = game.get("pitchers", {}).get(side, {})
        last_30 = (
            pitcher.get("stats", {})
            .get("last_30", {})
            .get("all", {})
        )

        season = (
            pitcher.get("stats", {})
            .get("season", {})
            .get("all", {})
        )

        era_30 = safe_float(last_30.get("era"))
        whip_30 = safe_float(last_30.get("whip"))
        era_season = safe_float(season.get("era"))

        if era_30 is not None:
            if era_30 <= 3.25:
                positives.append(
                    context_item(
                        f"{team} STARTER FORM",
                        f"{pitcher.get('name') or 'Starter'} owns a {era_30:.2f} ERA over the last 30 days.",
                        "good",
                        5,
                        team,
                        "pitcher_form",
                    )
                )
            elif era_30 >= 5.00:
                negatives.append(
                    context_item(
                        f"{team} STARTER STRUGGLING",
                        f"{pitcher.get('name') or 'Starter'} has a {era_30:.2f} ERA over the last 30 days.",
                        "negative",
                        -6,
                        team,
                        "pitcher_form",
                    )
                )

        if whip_30 is not None and whip_30 >= 1.45:
            negatives.append(
                context_item(
                    f"{team} TRAFFIC CONCERN",
                    f"The starter has a {whip_30:.2f} WHIP over the last 30 days.",
                    "negative",
                    -4,
                    team,
                    "pitcher_form",
                )
            )
        elif whip_30 is not None and whip_30 <= 1.10:
            positives.append(
                context_item(
                    f"{team} CONTROLLED TRAFFIC",
                    f"The starter has a {whip_30:.2f} WHIP over the last 30 days.",
                    "good",
                    3,
                    team,
                    "pitcher_form",
                )
            )

        if (
            era_30 is not None
            and era_season is not None
            and era_30 >= era_season + 1.25
        ):
            negatives.append(
                context_item(
                    f"{team} RECENT REGRESSION",
                    f"The starter's last-30 ERA is {era_30 - era_season:.2f} runs above his season ERA.",
                    "negative",
                    -4,
                    team,
                    "pitcher_form",
                )
            )


def evaluate_offenses(
    game: dict[str, Any],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    for side, team_key in (
        ("away", "away_team"),
        ("home", "home_team"),
    ):
        team = (
            game.get(team_key, {}).get("abbr")
            or side.upper()
        )

        offense = game.get("offense", {}).get(side, {})
        last_30 = (
            offense.get("stats", {})
            .get("last_30", {})
            .get("all", {})
        )

        ops_metric = last_30.get("OPS", {})
        avg_metric = last_30.get("AVG", {})

        ops_rank = safe_int(
            ops_metric.get("vs_hand_rank")
            if isinstance(ops_metric, dict)
            else None
        )

        avg_rank = safe_int(
            avg_metric.get("vs_hand_rank")
            if isinstance(avg_metric, dict)
            else None
        )

        if ops_rank is not None:
            if ops_rank <= 8:
                positives.append(
                    context_item(
                        f"{team} STRONG SPLIT OFFENSE",
                        f"The offense ranks {ordinal(ops_rank)} in OPS against the opposing starter's handedness.",
                        "good",
                        5,
                        team,
                        "offense",
                    )
                )
            elif ops_rank >= 23:
                negatives.append(
                    context_item(
                        f"{team} WEAK SPLIT OFFENSE",
                        f"The offense ranks {ordinal(ops_rank)} in OPS against the opposing starter's handedness.",
                        "negative",
                        -5,
                        team,
                        "offense",
                    )
                )

        if avg_rank is not None and avg_rank >= 23:
            negatives.append(
                context_item(
                    f"{team} CONTACT CONCERN",
                    f"The offense ranks {ordinal(avg_rank)} in average against the opposing starter's handedness.",
                    "negative",
                    -3,
                    team,
                    "offense",
                )
            )


def evaluate_bullpens(
    game: dict[str, Any],
    alerts: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    bullpens = game.get("bullpens", {})

    for side, team_key in (
        ("away", "away_team"),
        ("home", "home_team"),
    ):
        team = (
            game.get(team_key, {}).get("abbr")
            or side.upper()
        )

        bullpen = bullpens.get(side, {})
        used_yesterday = safe_int(
            bullpen.get("used_yesterday")
        )
        back_to_back = safe_int(
            bullpen.get("back_to_back")
        )

        last_30 = (
            bullpen.get("stats", {})
            .get("last_30", {})
            .get("all", {})
        )

        era = safe_float(last_30.get("era"))
        whip = safe_float(last_30.get("whip"))

        if era is not None:
            if era <= 3.40:
                positives.append(
                    context_item(
                        f"{team} BULLPEN FORM",
                        f"The relief unit has a {era:.2f} ERA over the last 30 days.",
                        "good",
                        4,
                        team,
                        "bullpen",
                    )
                )
            elif era >= 4.75:
                negatives.append(
                    context_item(
                        f"{team} BULLPEN QUALITY",
                        f"The relief unit has a {era:.2f} ERA over the last 30 days.",
                        "negative",
                        -6,
                        team,
                        "bullpen",
                    )
                )

        if whip is not None and whip >= 1.40:
            negatives.append(
                context_item(
                    f"{team} BULLPEN TRAFFIC",
                    f"The relief unit has a {whip:.2f} WHIP over the last 30 days.",
                    "negative",
                    -4,
                    team,
                    "bullpen",
                )
            )

        if used_yesterday is not None and used_yesterday >= 5:
            alerts.append(
                context_item(
                    f"{team} BULLPEN TAXED",
                    f"{used_yesterday} relievers were used yesterday.",
                    "warning",
                    -9,
                    team,
                    "bullpen_usage",
                )
            )
        elif used_yesterday is not None and used_yesterday <= 2:
            positives.append(
                context_item(
                    f"{team} BULLPEN RESTED",
                    f"Only {used_yesterday} reliever(s) were used yesterday.",
                    "good",
                    5,
                    team,
                    "bullpen_usage",
                )
            )
        elif used_yesterday is not None:
            negatives.append(
                context_item(
                    f"{team} BULLPEN WORKLOAD",
                    f"{used_yesterday} relievers were used yesterday.",
                    "negative",
                    -2,
                    team,
                    "bullpen_usage",
                )
            )

        if back_to_back is not None and back_to_back >= 3:
            alerts.append(
                context_item(
                    f"{team} BACK-TO-BACK ARMS",
                    f"{back_to_back} relievers have worked on consecutive days.",
                    "warning",
                    -8,
                    team,
                    "bullpen_usage",
                )
            )
        elif back_to_back is not None and back_to_back > 0:
            negatives.append(
                context_item(
                    f"{team} B2B RELIEVERS",
                    f"{back_to_back} reliever(s) have worked on consecutive days.",
                    "negative",
                    -2,
                    team,
                    "bullpen_usage",
                )
            )
        elif back_to_back == 0:
            positives.append(
                context_item(
                    f"{team} NO B2B ARMS",
                    "No relievers are flagged for consecutive-day usage.",
                    "good",
                    2,
                    team,
                    "bullpen_usage",
                )
            )


def evaluate_weather(
    game: dict[str, Any],
    alerts: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    weather = game.get("weather", {})

    if not weather:
        alerts.append(
            context_item(
                "WEATHER PENDING",
                "Game-time weather has not been imported.",
                "caution",
                -3,
                None,
                "weather",
            )
        )
        return

    rain_probability = safe_float(
        weather.get("rain_probability")
    )
    wind_speed = safe_float(
        weather.get("wind_speed")
    )
    temperature = safe_float(
        weather.get("temperature")
    )

    if rain_probability is not None and rain_probability >= 50:
        alerts.append(
            context_item(
                "RAIN RISK",
                f"Rain probability is {round(rain_probability)}% near first pitch.",
                "warning",
                -8,
                None,
                "weather",
            )
        )
    elif rain_probability is not None and rain_probability >= 25:
        negatives.append(
            context_item(
                "WEATHER UNCERTAINTY",
                f"Rain probability is {round(rain_probability)}% near first pitch.",
                "negative",
                -3,
                None,
                "weather",
            )
        )
    elif rain_probability is not None:
        positives.append(
            context_item(
                "LOW RAIN RISK",
                f"Rain probability is {round(rain_probability)}% near first pitch.",
                "good",
                2,
                None,
                "weather",
            )
        )

    if wind_speed is not None and wind_speed >= 15:
        alerts.append(
            context_item(
                "STRONG WIND",
                f"Wind is projected at {wind_speed:.1f} mph.",
                "caution",
                -4,
                None,
                "weather",
            )
        )
    elif wind_speed is not None:
        information.append(
            context_item(
                "WIND",
                f"Wind is projected at {wind_speed:.1f} mph.",
                "info",
                0,
                None,
                "weather",
            )
        )

    if temperature is not None:
        information.append(
            context_item(
                "TEMPERATURE",
                f"Game-time temperature is projected near {round(temperature)}°F.",
                "info",
                0,
                None,
                "weather",
            )
        )


def evaluate_market(
    game: dict[str, Any],
    alerts: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
    information: list[dict[str, Any]],
) -> None:
    market = game.get("market", {})
    moneyline = market.get("moneyline", {})
    best = moneyline.get("best", {})
    consensus = moneyline.get("consensus", {})
    fair = moneyline.get("fair", {})

    away_best = best.get("away")
    home_best = best.get("home")

    if away_best or home_best:
        positives.append(
            context_item(
                "MARKET AVAILABLE",
                "Current sportsbook prices are attached to this game.",
                "good",
                3,
                None,
                "market",
            )
        )
    else:
        alerts.append(
            context_item(
                "MARKET PENDING",
                "Current sportsbook prices are unavailable.",
                "caution",
                -4,
                None,
                "market",
            )
        )
        return

    for side, team_key in (
        ("away", "away_team"),
        ("home", "home_team"),
    ):
        team = (
            game.get(team_key, {}).get("abbr")
            or side.upper()
        )

        best_row = best.get(side) or {}
        best_price = safe_float(
            best_row.get("price")
        )
        fair_price = safe_float(
            fair.get(f"{side}_price")
        )
        consensus_price = safe_float(
            consensus.get(side)
        )

        if (
            best_price is not None
            and fair_price is not None
        ):
            difference = price_difference_cents(
                best_price,
                fair_price,
            )

            if difference >= 12:
                positives.append(
                    context_item(
                        f"{team} PRICE VALUE",
                        f"The best available price is roughly {difference:.0f} cents better than the no-vig fair price.",
                        "good",
                        5,
                        team,
                        "market",
                    )
                )
            elif difference <= -12:
                negatives.append(
                    context_item(
                        f"{team} EXPENSIVE PRICE",
                        f"The best available price is roughly {abs(difference):.0f} cents worse than the no-vig fair price.",
                        "negative",
                        -5,
                        team,
                        "market",
                    )
                )

        if consensus_price is not None:
            information.append(
                context_item(
                    f"{team} CONSENSUS",
                    f"Consensus moneyline: {format_american(consensus_price)}.",
                    "info",
                    0,
                    team,
                    "market",
                )
            )


def calculate_context_score(
    alerts: list[dict[str, Any]],
    positives: list[dict[str, Any]],
    negatives: list[dict[str, Any]],
) -> int:
    score = 60

    for group in (
        positives,
        negatives,
        alerts,
    ):
        score += sum(
            safe_int(item.get("weight")) or 0
            for item in group
        )

    return max(
        0,
        min(
            100,
            score,
        ),
    )


def context_item(
    title: str,
    summary: str,
    level: str,
    weight: int,
    team: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "summary": summary,
        "level": level,
        "weight": weight,
        "team": team,
        "category": category,
    }


def score_label(
    score: int,
) -> str:
    if score >= 85:
        return "CLEAR"
    if score >= 70:
        return "GOOD"
    if score >= 55:
        return "MIXED"
    if score >= 40:
        return "CAUTION"
    return "WARNING"


def price_difference_cents(
    offered: float,
    fair: float,
) -> float:
    return offered - fair


def format_american(
    value: float,
) -> str:
    rounded = round(value)

    return (
        f"+{rounded}"
        if rounded > 0
        else str(rounded)
    )


def ordinal(
    value: int,
) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(
            value % 10,
            "th",
        )

    return f"{value}{suffix}"


def safe_float(
    value: Any,
) -> float | None:
    if value in {
        None,
        "",
        "-",
    }:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def safe_int(
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
            "Usage: python3 scripts/mlb/context.py "
            "<game_id>"
        )

    requested_game_id = sys.argv[1]

    game = next(
        (
            item
            for item in load_games()
            if item.get("id")
            == requested_game_id
        ),
        None,
    )

    if not game:
        raise SystemExit(
            f"Game not found: {requested_game_id}"
        )

    snapshot = build_context_snapshot(
        game
    )

    print(
        json.dumps(
            snapshot,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
