#!/usr/bin/env python3
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import json
import re

ROOT = Path(__file__).resolve().parents[1]

GAMES_FILE = ROOT / "data/games.json"
ARTICLES_FILE = ROOT / "data/articles.json"
PLAYS_FILE = ROOT / "data/plays.json"
TODAYS_CARD_FILE = ROOT / "data/todays-card.json"


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise SystemExit(f"Could not read {path.name}: {error}")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default not in {None, ""} else ""
    value = input(f"{label}{suffix}: ").strip()
    return default if not value and default is not None else value


def prompt_yes_no(label: str, default: bool = False) -> bool:
    default_label = "Y/n" if default else "y/N"

    while True:
        value = input(f"{label} [{default_label}]: ").strip().lower()

        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False

        print("Please enter y or n.")


def prompt_multiline(label: str) -> str:
    print()
    print(label)
    print("Paste your text. Type END on its own line when finished.")

    lines: list[str] = []

    while True:
        line = input()

        if line.strip() == "END":
            break

        lines.append(line)

    return "\n".join(lines).strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "entry"


def choose_game(
    games: list[dict[str, Any]],
    target_date: str,
) -> dict[str, Any]:
    eligible = [
        game for game in games
        if game.get("date") == target_date
    ]

    eligible.sort(
        key=lambda game: (
            game.get("game_time") or "",
            game.get("id") or "",
        )
    )

    if not eligible:
        raise SystemExit(
            f"No games found for {target_date}. "
            "Run update_games.py for that date first."
        )

    print()
    print(f"Games for {target_date}")
    print("-" * 40)

    for index, game in enumerate(eligible, start=1):
        away = game.get("away_team", {}).get("abbr") or "AWAY"
        home = game.get("home_team", {}).get("abbr") or "HOME"
        print(f"{index}. {away} @ {home}")

    while True:
        selected = prompt("Choose game number")

        try:
            number = int(selected)
        except ValueError:
            print("Enter one of the listed numbers.")
            continue

        if 1 <= number <= len(eligible):
            return eligible[number - 1]

        print("Enter one of the listed numbers.")


def upsert(
    records: list[dict[str, Any]],
    incoming: dict[str, Any],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    found = False

    for record in records:
        if record.get("id") == incoming["id"]:
            merged = dict(record)
            merged.update(incoming)
            output.append(merged)
            found = True
        else:
            output.append(record)

    if not found:
        output.append(incoming)

    output.sort(
        key=lambda item: (
            item.get("date") or "",
            item.get("game_id") or "",
            item.get("id") or "",
        )
    )

    return output


def publish_article(
    game: dict[str, Any],
    target_date: str,
) -> dict[str, Any] | None:
    if not prompt_yes_no("Publish an article", default=True):
        return None

    away = game.get("away_team", {}).get("abbr") or "Away"
    home = game.get("home_team", {}).get("abbr") or "Home"

    title = prompt(
        "Article title",
        f"{away} at {home} — Game Analysis",
    )

    summary = prompt("Short summary", "")
    body = prompt_multiline("Article body")

    if not body:
        raise SystemExit("Article body cannot be empty.")

    article_id = f"{game['id']}-{slugify(title)[:48]}"
    timestamp = datetime.now(timezone.utc).isoformat()

    article = {
        "id": article_id,
        "game_id": game["id"],
        "date": target_date,
        "sport": game.get("sport", "MLB"),
        "title": title,
        "author": prompt("Author", "Mark"),
        "summary": summary,
        "tags": ["MLB", away, home],
        "body": body,
        "status": "published",
        "published_at": timestamp,
        "updated_at": timestamp,
    }

    payload = load_json(
        ARTICLES_FILE,
        {
            "schema_version": "1.0",
            "updated_at": None,
            "articles": [],
        },
    )

    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        articles = []

    payload["schema_version"] = "1.0"
    payload["updated_at"] = timestamp
    payload["articles"] = upsert(articles, article)

    save_json(ARTICLES_FILE, payload)
    return article


def publish_play(
    game: dict[str, Any],
    target_date: str,
) -> dict[str, Any] | None:
    if not prompt_yes_no("Publish an official play", default=False):
        return None

    play_name = prompt("Play")

    if not play_name:
        raise SystemExit("Play cannot be empty.")

    odds = prompt("Odds", "-110")
    units_text = prompt("Units", "1.0")
    rating_text = prompt("Rating (1-5)", "3")

    try:
        units = float(units_text)
    except ValueError:
        raise SystemExit("Units must be a number.")

    try:
        rating = int(rating_text)
    except ValueError:
        raise SystemExit("Rating must be a whole number.")

    if not 1 <= rating <= 5:
        raise SystemExit("Rating must be between 1 and 5.")

    analysis = prompt_multiline("Play analysis")
    away_team = game.get("away_team", {})
    home_team = game.get("home_team", {})
    timestamp = datetime.now(timezone.utc).isoformat()

    play = {
        "id": f"{game['id']}-{slugify(play_name)[:52]}",
        "game_id": game["id"],
        "date": target_date,
        "sport": game.get("sport", "MLB"),
        "game": (
            f"{away_team.get('name') or away_team.get('abbr')} "
            f"at {home_team.get('name') or home_team.get('abbr')}"
        ),
        "away_team": away_team.get("abbr"),
        "away_team_id": away_team.get("team_id"),
        "home_team": home_team.get("abbr"),
        "home_team_id": home_team.get("team_id"),
        "play": play_name,
        "odds": odds,
        "units": units,
        "rating": rating,
        "handicapper": prompt("Handicapper", "Mark"),
        "is_best_bet": prompt_yes_no("Best bet", default=False),
        "tags": ["MLB"],
        "analysis": analysis,
        "status": "published",
        "published_at": timestamp,
        "result": "pending",
        "units_result": None,
        "final_score": None,
        "graded_at": None,
        "closing_odds": None,
        "closing_line": None,
        "evaluation_id": None,
        "result_id": None,
    }

    archive = load_json(
        PLAYS_FILE,
        {
            "schema_version": "1.2",
            "updated_at": None,
            "plays": [],
        },
    )

    archived_plays = archive.get("plays", [])
    if not isinstance(archived_plays, list):
        archived_plays = []

    archive["schema_version"] = "1.2"
    archive["updated_at"] = timestamp
    archive["plays"] = upsert(archived_plays, play)
    save_json(PLAYS_FILE, archive)

    card = load_json(
        TODAYS_CARD_FILE,
        {
            "schema_version": "1.2",
            "date": target_date,
            "status": "published",
            "updated_at": timestamp,
            "notes": "",
            "plays": [],
        },
    )

    card_plays = card.get("plays", [])
    if not isinstance(card_plays, list):
        card_plays = []

    if card.get("date") != target_date:
        card_plays = []

    card["schema_version"] = "1.2"
    card["date"] = target_date
    card["status"] = "published"
    card["updated_at"] = timestamp
    card["plays"] = upsert(card_plays, play)
    save_json(TODAYS_CARD_FILE, card)

    return play


def main() -> None:
    games_payload = load_json(GAMES_FILE, {"games": []})
    games = games_payload.get("games", [])

    if not isinstance(games, list):
        games = []

    target_date = prompt("Date", date.today().isoformat())
    game = choose_game(games, target_date)

    print()
    print(f"Selected: {game['id']}")

    article = publish_article(game, target_date)
    play = publish_play(game, target_date)

    print()
    print("=" * 44)
    print("PUBLISH COMPLETE")
    print("=" * 44)
    print(
        "Article: "
        + (article["title"] if article else "Not published")
    )
    print(
        "Official play: "
        + (play["play"] if play else "Not published")
    )
    print()
    print("Refresh the matching Game Center page.")


if __name__ == "__main__":
    main()
