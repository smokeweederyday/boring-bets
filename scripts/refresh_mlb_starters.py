#!/usr/bin/env python3
"""Fast MLB starter refresh for Boring Bets.

Checks MLB schedule/live feeds for probable and confirmed starters, creates
clearly labeled conservative rotation projections only when MLB has not posted
a probable, enriches new or changed pitchers immediately, and rewrites only
affected date shards.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
GAMES_FILE = DATA / "games.json"
CHANGE_LOG = CACHE / "mlb-starter-changes.jsonl"
STATUS_FILE = CACHE / "mlb-starter-refresh-status.json"
SCHEDULE_LOCK = CACHE / "scheduled-refresh.lock"
STARTER_LOCK = CACHE / "mlb-starter-refresh.lock"
EASTERN = ZoneInfo("America/New_York")
MLB_API = "https://statsapi.mlb.com/api/v1"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mlb.pitchers import build_pitcher_snapshot  # noqa: E402
from mlb.pitchers import apply_league_pitcher_cache  # noqa: E402


def parse_args() -> argparse.Namespace:
    today = datetime.now(EASTERN).date().isoformat()
    parser = argparse.ArgumentParser(
        description="Refresh projected, probable, and confirmed MLB starters quickly."
    )
    parser.add_argument("--date", default=today)
    parser.add_argument("--days-ahead", type=int, default=7)
    parser.add_argument("--no-projections", action="store_true")
    parser.add_argument("--force-snapshots", action="store_true")
    parser.add_argument("--skip-card-data", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_json(url: str, timeout: int = 45) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Boring Bets/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def atomic_write_json(path: Path, payload: Any, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        if compact:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(str(temporary), str(path))


def load_master() -> Dict[str, Any]:
    payload = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("games"), list):
        raise ValueError("data/games.json must contain a games list")
    return payload


def acquire_lock(force: bool) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)

    if SCHEDULE_LOCK.exists():
        details = SCHEDULE_LOCK.read_text(encoding="utf-8", errors="replace").strip()
        raise SystemExit(
            "A full scheduled refresh is active; starter refresh skipped safely.\n"
            f"Lock: {SCHEDULE_LOCK}\n{details}"
        )

    if STARTER_LOCK.exists():
        if not force:
            details = STARTER_LOCK.read_text(
                encoding="utf-8", errors="replace"
            ).strip()
            raise SystemExit(
                "Another starter refresh may be active.\n"
                f"Lock: {STARTER_LOCK}\n{details}\n"
                "Use --force only after confirming no starter updater is running."
            )
        STARTER_LOCK.unlink()

    STARTER_LOCK.write_text(
        json.dumps({"pid": os.getpid(), "started_at": iso_now()}, indent=2) + "\n",
        encoding="utf-8",
    )


def release_lock() -> None:
    try:
        STARTER_LOCK.unlink()
    except FileNotFoundError:
        pass


def fetch_schedule(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "sportId": 1,
            "startDate": start_date,
            "endDate": end_date,
            "hydrate": "probablePitcher,team,venue",
            "gameType": "R",
        }
    )
    raw = get_json(f"{MLB_API}/schedule?{query}", timeout=60)
    games: List[Dict[str, Any]] = []
    for date_block in raw.get("dates", []):
        games.extend(date_block.get("games", []))
    return games


def int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def team_id_from_game(game: Dict[str, Any], side: str) -> Optional[int]:
    team = game.get(f"{side}_team") or {}
    return int_or_none(team.get("team_id") or team.get("id"))


def team_name_from_game(game: Dict[str, Any], side: str) -> str:
    team = game.get(f"{side}_team") or {}
    return str(team.get("abbr") or team.get("name") or side.upper())


def official_probable(schedule_game: Dict[str, Any], side: str) -> Optional[Dict[str, Any]]:
    side_payload = (schedule_game.get("teams") or {}).get(side) or {}
    probable = side_payload.get("probablePitcher") or {}
    pitcher_id = int_or_none(probable.get("id"))
    if not pitcher_id:
        return None
    return {
        "id": pitcher_id,
        "name": probable.get("fullName") or "Starter",
        "status": "probable",
        "source": "MLB schedule probablePitcher",
    }


def status_text(schedule_game: Dict[str, Any]) -> str:
    status = schedule_game.get("status") or {}
    return str(
        status.get("detailedState")
        or status.get("abstractGameState")
        or ""
    )


def confirmed_from_live_feed(
    game_pk: int,
    side: str,
    schedule_status: str,
) -> Optional[Dict[str, Any]]:
    normalized = schedule_status.lower()
    if not any(
        token in normalized
        for token in ("live", "in progress", "final", "game over", "completed")
    ):
        return None

    try:
        raw = get_json(
            f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",
            timeout=30,
        )
    except Exception as error:
        print(f"Live confirmation unavailable for {game_pk}: {error}")
        return None

    team_box = (
        ((raw.get("liveData") or {}).get("boxscore") or {})
        .get("teams", {})
        .get(side, {})
    )
    players = team_box.get("players") or {}

    for player in players.values():
        pitching = ((player.get("stats") or {}).get("pitching") or {})
        if (int_or_none(pitching.get("gamesStarted")) or 0) < 1:
            continue
        person = player.get("person") or {}
        pitcher_id = int_or_none(person.get("id"))
        if pitcher_id:
            return {
                "id": pitcher_id,
                "name": person.get("fullName") or "Starter",
                "status": "confirmed",
                "source": "MLB live boxscore",
            }

    pitcher_ids = team_box.get("pitchers") or []
    if pitcher_ids:
        first_id = int_or_none(pitcher_ids[0])
        if first_id:
            player = players.get(f"ID{first_id}") or {}
            person = player.get("person") or {}
            return {
                "id": first_id,
                "name": person.get("fullName") or "Starter",
                "status": "confirmed",
                "source": "MLB live pitching order",
            }
    return None


def pitcher_complete(pitcher: Dict[str, Any]) -> bool:
    """Return True after the complete snapshot builder has run.

    A pitcher making his first MLB start can legitimately have an empty
    Last Starts sample. The structural presence of every requested count is
    therefore the completeness marker, not whether Last 1 contains values.
    """
    if not pitcher.get("id"):
        return False
    stats = pitcher.get("stats")
    if not isinstance(stats, dict):
        return False
    last_starts = stats.get("last_starts")
    if not isinstance(last_starts, dict):
        return False
    return all(str(count) in last_starts for count in (1, 3, 7, 10, 20))


def fetch_snapshot_with_retries(
    pitcher_id: int,
    target_date: str,
    pitcher_name: str,
    attempts: int = 2,
) -> Dict[str, Any]:
    """Build one snapshot without allowing one MLB timeout to kill the slate."""
    last_error: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            return build_pitcher_snapshot(pitcher_id, target_date)
        except Exception as error:
            last_error = error
            print(
                f"Snapshot attempt {attempt}/{attempts} failed for "
                f"{pitcher_name} ({pitcher_id}): {error}"
            )
            if attempt < attempts:
                time.sleep(2.0)
    raise RuntimeError(
        f"Snapshot unavailable after {attempts} attempts for "
        f"{pitcher_name} ({pitcher_id})"
    ) from last_error



def pitching_outs(value: Any) -> int:
    if isinstance(value, dict):
        direct = int_or_none(value.get("outs"))
        if direct is not None:
            return direct

        innings = value.get("inningsPitched")
    else:
        innings = value

    text = str(innings or "0").strip()

    try:
        whole, _, remainder = text.partition(".")
        return max(
            0,
            int(whole or 0) * 3
            + int(remainder or 0),
        )
    except (TypeError, ValueError):
        return 0


def pitcher_season_summary(
    pitcher: Dict[str, Any],
) -> Dict[str, Any]:
    stats = pitcher.get("stats")
    stats = stats if isinstance(stats, dict) else {}

    season = stats.get("season")
    if not isinstance(season, dict):
        season = pitcher.get("season")

    season = season if isinstance(season, dict) else {}

    if isinstance(season.get("all"), dict):
        return season.get("all") or {}

    return season


def likely_opener_profile(
    pitcher: Dict[str, Any],
) -> bool:
    season = pitcher_season_summary(pitcher)

    games = int_or_none(
        season.get("games")
    ) or 0

    starts = int_or_none(
        season.get("games_started")
        or season.get("gamesStarted")
    ) or 0

    if games >= 8 and starts <= 3:
        return (starts / max(games, 1)) <= 0.30

    last_30 = pitcher.get("last_30")
    last_30 = (
        last_30
        if isinstance(last_30, dict)
        else {}
    )

    recent_starts = int_or_none(
        last_30.get("games_started")
        or last_30.get("gamesStarted")
    ) or 0

    return recent_starts <= 1 and games >= 8


def likely_bulk_profile(
    pitcher: Dict[str, Any],
) -> bool:
    season = pitcher_season_summary(pitcher)

    starts = int_or_none(
        season.get("games_started")
        or season.get("gamesStarted")
    ) or 0

    if starts >= 5:
        return True

    stats = pitcher.get("stats")
    stats = stats if isinstance(stats, dict) else {}

    last_starts = stats.get("last_starts")
    last_starts = (
        last_starts
        if isinstance(last_starts, dict)
        else {}
    )

    sample = last_starts.get("7")
    sample = sample if isinstance(sample, dict) else {}

    all_sample = sample.get("all")
    all_sample = (
        all_sample
        if isinstance(all_sample, dict)
        else sample
    )

    used = int_or_none(
        all_sample.get("starts_used")
        or all_sample.get("games_started")
    ) or 0

    return used >= 3


def complete_identity_snapshot(
    identity: Dict[str, Any],
    target_date: str,
    snapshot_cache: Dict[
        Tuple[int, str],
        Dict[str, Any]
    ],
    status: str,
    source: str,
) -> Optional[Dict[str, Any]]:
    pitcher_id = int_or_none(identity.get("id"))

    if not pitcher_id:
        return None

    key = (pitcher_id, target_date)

    if key not in snapshot_cache:
        name = str(
            identity.get("name")
            or pitcher_id
        )

        try:
            snapshot_cache[key] = (
                fetch_snapshot_with_retries(
                    pitcher_id,
                    target_date,
                    name,
                )
            )
        except Exception as error:
            snapshot_cache[key] = {
                "__snapshot_error__": str(error),
            }

    cached = snapshot_cache.get(key) or {}

    if cached.get("__snapshot_error__"):
        snapshot = copy.deepcopy(identity)
        snapshot["snapshot_status"] = "pending"
        snapshot["snapshot_error"] = cached.get(
            "__snapshot_error__"
        )
    else:
        snapshot = copy.deepcopy(cached)

    snapshot["id"] = pitcher_id
    snapshot["name"] = (
        identity.get("name")
        or snapshot.get("name")
        or "Pitcher"
    )
    snapshot["status"] = status
    snapshot["source"] = source

    return snapshot


def likely_bullpen_plan_from_transition(
    previous: Dict[str, Any],
    replacement: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    previous_id = int_or_none(previous.get("id"))
    replacement_id = int_or_none(
        replacement.get("id")
    )

    if (
        not previous_id
        or not replacement_id
        or previous_id == replacement_id
    ):
        return None

    previous_status = str(
        previous.get("status") or ""
    ).lower()

    if previous_status not in (
        "probable",
        "confirmed",
    ):
        return None

    if not likely_opener_profile(replacement):
        return None

    if not likely_bulk_profile(previous):
        return None

    return {
        "detected": True,
        "confidence": "likely",
        "status": "likely",
        "source":
            "Starter assignment changed from a "
            "starter-profile pitcher to a "
            "reliever-profile pitcher.",
        "opener": copy.deepcopy(replacement),
        "bulk": copy.deepcopy(previous),
        "updated_at": iso_now(),
    }


def likely_bullpen_plan_from_history(
    current: Dict[str, Any],
    target_date: str,
    snapshot_cache: Dict[
        Tuple[int, str],
        Dict[str, Any]
    ],
) -> Optional[Dict[str, Any]]:
    if not likely_opener_profile(current):
        return None

    history = current.get("starter_history")
    history = (
        history
        if isinstance(history, list)
        else []
    )

    if not history:
        return None

    latest = history[-1]
    latest = (
        latest
        if isinstance(latest, dict)
        else {}
    )

    previous = latest.get("previous")
    previous = (
        previous
        if isinstance(previous, dict)
        else {}
    )

    previous_id = int_or_none(
        previous.get("id")
    )

    current_id = int_or_none(
        current.get("id")
    )

    if (
        not previous_id
        or previous_id == current_id
    ):
        return None

    bulk = complete_identity_snapshot(
        previous,
        target_date,
        snapshot_cache,
        "probable",
        "Previous MLB probable pitcher",
    )

    if (
        not bulk
        or not likely_bulk_profile(bulk)
    ):
        return None

    return {
        "detected": True,
        "confidence": "likely",
        "status": "likely",
        "source":
            "Probable-pitcher history indicates "
            "an opener and expected bulk pitcher.",
        "opener": copy.deepcopy(current),
        "bulk": bulk,
        "updated_at": iso_now(),
    }


def confirmed_bullpen_plan_from_live_feed(
    game_pk: int,
    side: str,
    schedule_status: str,
    target_date: str,
    snapshot_cache: Dict[
        Tuple[int, str],
        Dict[str, Any]
    ],
) -> Optional[Dict[str, Any]]:
    normalized = str(
        schedule_status or ""
    ).lower()

    if not any(
        token in normalized
        for token in (
            "live",
            "in progress",
            "final",
            "game over",
            "completed",
        )
    ):
        return None

    try:
        raw = get_json(
            "https://statsapi.mlb.com/"
            f"api/v1.1/game/{game_pk}/feed/live",
            timeout=30,
        )
    except Exception as error:
        print(
            "Bullpen-start confirmation "
            f"unavailable for {game_pk}: {error}"
        )
        return None

    team_box = (
        ((raw.get("liveData") or {})
        .get("boxscore") or {})
        .get("teams", {})
        .get(side, {})
    )

    players = team_box.get("players") or {}
    pitching_order = team_box.get("pitchers") or []

    appearances = []

    for raw_id in pitching_order:
        pitcher_id = int_or_none(raw_id)

        if not pitcher_id:
            continue

        player = (
            players.get(f"ID{pitcher_id}")
            or {}
        )

        person = player.get("person") or {}
        pitching = (
            (player.get("stats") or {})
            .get("pitching")
            or {}
        )

        appearances.append({
            "id": pitcher_id,
            "name":
                person.get("fullName")
                or "Pitcher",
            "outs": pitching_outs(pitching),
            "games_started":
                int_or_none(
                    pitching.get("gamesStarted")
                )
                or 0,
        })

    if len(appearances) < 2:
        return None

    opener_index = 0

    for index, appearance in enumerate(
        appearances
    ):
        if appearance.get("games_started", 0) >= 1:
            opener_index = index
            break

    opener_game = appearances[opener_index]
    followers = appearances[opener_index + 1:]

    if not followers:
        return None

    bulk_game = max(
        followers,
        key=lambda appearance:
            appearance.get("outs", 0),
    )

    opener_outs = int(
        opener_game.get("outs") or 0
    )

    bulk_outs = int(
        bulk_game.get("outs") or 0
    )

    if (
        opener_outs > 6
        or bulk_outs < 6
        or bulk_outs <= opener_outs
    ):
        return None

    opener = complete_identity_snapshot(
        opener_game,
        target_date,
        snapshot_cache,
        "confirmed",
        "MLB live boxscore opener",
    )

    bulk = complete_identity_snapshot(
        bulk_game,
        target_date,
        snapshot_cache,
        "confirmed",
        "MLB live boxscore bulk pitcher",
    )

    if not opener or not bulk:
        return None

    return {
        "detected": True,
        "confidence": "confirmed",
        "status": "confirmed",
        "source": "MLB live pitching order",
        "opener": opener,
        "bulk": bulk,
        "opener_game_outs": opener_outs,
        "bulk_game_outs": bulk_outs,
        "updated_at": iso_now(),
    }

def compact_pitcher(pitcher: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": pitcher.get("id"),
        "name": pitcher.get("name"),
        "status": pitcher.get("status"),
        "source": pitcher.get("source"),
        "first_seen_at": pitcher.get("first_seen_at"),
    }


def merge_starter(
    existing: Dict[str, Any],
    candidate: Dict[str, Any],
    target_date: str,
    snapshot_cache: Dict[Tuple[int, str], Dict[str, Any]],
    force_snapshot: bool,
) -> Tuple[Dict[str, Any], bool, str]:
    now = iso_now()
    old_id = int_or_none(existing.get("id"))
    new_id = int_or_none(candidate.get("id"))
    if not new_id:
        return existing, False, "no candidate"

    old_status = str(existing.get("status") or "unknown")
    new_status = str(candidate.get("status") or "projected")
    precedence = {"unknown": 0, "projected": 1, "probable": 2, "confirmed": 3}

    changed_identity = old_id is not None and old_id != new_id
    same_identity = old_id == new_id

    if same_identity and precedence.get(new_status, 0) < precedence.get(old_status, 0):
        new_status = old_status

    if old_status == "confirmed" and new_status != "confirmed" and not changed_identity:
        return existing, False, "confirmed retained"

    needs_snapshot = (
        force_snapshot
        or changed_identity
        or not same_identity
        or not pitcher_complete(existing)
    )

    snapshot_error: Optional[str] = None
    if needs_snapshot:
        key = (new_id, target_date)
        if key not in snapshot_cache:
            pitcher_name = str(candidate.get("name") or new_id)
            print(
                f"Fetching complete pitcher snapshot: "
                f"{pitcher_name} ({new_id}) for {target_date}"
            )
            try:
                snapshot_cache[key] = fetch_snapshot_with_retries(
                    new_id,
                    target_date,
                    pitcher_name,
                )
            except Exception as error:
                snapshot_cache[key] = {
                    "__snapshot_error__": str(error),
                }

        cached_snapshot = snapshot_cache[key]
        snapshot_error = cached_snapshot.get("__snapshot_error__")
        if snapshot_error:
            # Publish the starter identity/status immediately, retain any prior
            # statistics, and let the next three-minute cycle retry enrichment.
            merged = copy.deepcopy(existing)
        else:
            merged = copy.deepcopy(cached_snapshot)
    else:
        merged = copy.deepcopy(existing)

    merged["id"] = new_id
    merged["name"] = candidate.get("name") or merged.get("name") or "Starter"
    merged["status"] = new_status
    merged["source"] = candidate.get("source")
    merged["last_checked_at"] = now
    merged["first_seen_at"] = existing.get("first_seen_at") or now
    merged["changed_since_last_refresh"] = bool(changed_identity)

    if snapshot_error:
        merged["snapshot_status"] = "pending"
        merged["snapshot_error"] = snapshot_error
        merged["snapshot_last_failed_at"] = now
    elif pitcher_complete(merged):
        merged["snapshot_status"] = "complete"
        merged.pop("snapshot_error", None)
        merged.pop("snapshot_last_failed_at", None)

    if new_status == "projected":
        merged["projected_at"] = existing.get("projected_at") or now
        merged["projection_method"] = candidate.get("projection_method")
        merged["projection_confidence"] = candidate.get("projection_confidence")
    elif new_status == "probable":
        merged["probable_at"] = existing.get("probable_at") or now
        merged.pop("projection_method", None)
        merged.pop("projection_confidence", None)
    elif new_status == "confirmed":
        merged["confirmed_at"] = existing.get("confirmed_at") or now
        merged.pop("projection_method", None)
        merged.pop("projection_confidence", None)

    if changed_identity:
        previous = compact_pitcher(existing)
        merged["previous_pitcher"] = previous
        merged["changed_at"] = now
        history = list(existing.get("starter_history") or [])
        history.append(
            {
                "changed_at": now,
                "previous": previous,
                "replacement": compact_pitcher(merged),
            }
        )
        merged["starter_history"] = history[-20:]
        reason = "starter changed"
    elif not same_identity:
        reason = "starter added"
    elif needs_snapshot and not snapshot_error:
        reason = "snapshot repaired"
    elif old_status != new_status:
        reason = "status upgraded"
    elif snapshot_error:
        # An already-listed starter remains incomplete. Do not abort or rebuild
        # the date solely for a repeated transient failure; the watcher retries.
        return merged, False, "snapshot pending"
    else:
        return merged, False, "unchanged"

    if snapshot_error:
        reason += "; snapshot pending"

    return merged, True, reason


def build_team_history(
    games: Sequence[Dict[str, Any]]
) -> Dict[int, List[Dict[str, Any]]]:
    history: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for game in games:
        game_date = str(game.get("date") or "")
        if not game_date:
            continue
        for side in ("away", "home"):
            team_id = team_id_from_game(game, side)
            pitcher = ((game.get("pitchers") or {}).get(side) or {})
            pitcher_id = int_or_none(pitcher.get("id"))
            if not team_id or not pitcher_id:
                continue
            history[team_id].append(
                {
                    "date": game_date,
                    "pitcher_id": pitcher_id,
                    "name": pitcher.get("name") or "Starter",
                }
            )
    for rows in history.values():
        rows.sort(key=lambda row: row["date"])
    return history


def choose_rotation_projection(
    team_id: int,
    target_date: str,
    history: Dict[int, List[Dict[str, Any]]],
    assigned: Dict[Tuple[int, str], set],
) -> Optional[Dict[str, Any]]:
    target = date.fromisoformat(target_date)
    recent_by_pitcher: Dict[int, Dict[str, Any]] = {}

    for row in history.get(team_id, []):
        if row["date"] >= target_date:
            continue
        pitcher_id = int(row["pitcher_id"])
        prior = recent_by_pitcher.get(pitcher_id)
        if prior is None or row["date"] > prior["date"]:
            recent_by_pitcher[pitcher_id] = row

    candidates = []
    already_assigned = assigned[(team_id, target_date)]

    for row in recent_by_pitcher.values():
        pitcher_id = int(row["pitcher_id"])
        if pitcher_id in already_assigned:
            continue
        rest_days = (target - date.fromisoformat(row["date"])).days
        if 4 <= rest_days <= 9:
            candidates.append((rest_days, pitcher_id, row))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1]))
    rest_days, pitcher_id, row = candidates[0]
    assigned[(team_id, target_date)].add(pitcher_id)

    return {
        "id": pitcher_id,
        "name": row.get("name") or "Projected Starter",
        "status": "projected",
        "source": "Boring Bets rotation inference",
        "projection_method": "most-rested recent starter",
        "projection_confidence": "medium" if rest_days <= 6 else "low",
    }


def append_virtual_start(
    team_id: Optional[int],
    target_date: str,
    candidate: Optional[Dict[str, Any]],
    history: Dict[int, List[Dict[str, Any]]],
) -> None:
    if not team_id or not candidate or not candidate.get("id"):
        return
    history[team_id].append(
        {
            "date": target_date,
            "pitcher_id": int(candidate["id"]),
            "name": candidate.get("name") or "Starter",
        }
    )
    history[team_id].sort(key=lambda row: row["date"])


def load_rank_cache(target_date: str) -> Optional[Dict[str, Any]]:
    """Load the exact rank cache, or the newest safe prior-date cache.

    Future-date probable starters should not lose Last Starts handedness merely
    because the expensive league cache has not yet been built for that date.
    A prior-date cache is stale-by-label rather than fabricated and is only used
    for the current/future starter watcher.
    """
    exact = CACHE / f"mlb-pitcher-ranks-v5-{target_date}.json"
    candidates = [exact] if exact.exists() else []

    if not candidates:
        for path in CACHE.glob("mlb-pitcher-ranks-v5-*.json"):
            cache_date = path.stem.replace("mlb-pitcher-ranks-v5-", "")
            if cache_date <= target_date:
                candidates.append(path)
        candidates.sort(reverse=True)

    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cache_date = str(payload.get("date") or "")
            if path != exact:
                print(
                    f"Using latest pitcher rank cache {cache_date or path.name} "
                    f"for {target_date}."
                )
            return payload
        except Exception as error:
            print(f"Could not load pitcher rank cache {path.name}: {error}")
    return None


def update_public_shard(
    master_payload: Dict[str, Any],
    all_games: Sequence[Dict[str, Any]],
    target_date: str,
) -> None:
    shard_path = DATA / "games" / f"{target_date}.json"
    date_games = [game for game in all_games if game.get("date") == target_date]

    existing: Any = None
    if shard_path.exists():
        try:
            existing = json.loads(shard_path.read_text(encoding="utf-8"))
        except Exception:
            existing = None

    if isinstance(existing, dict):
        payload = existing
        payload["games"] = date_games
        payload["updated_at"] = iso_now()
    elif isinstance(existing, list):
        payload = date_games
    else:
        payload = {
            "schema_version": master_payload.get("schema_version"),
            "date": target_date,
            "updated_at": iso_now(),
            "games": date_games,
        }

    atomic_write_json(shard_path, payload, compact=False)


def rebuild_card_date(target_date: str) -> bool:
    script = SCRIPTS / "build_todays_card_data.py"
    if not script.exists():
        print("Today’s Card builder missing; skipping card shard.")
        return False
    completed = subprocess.run(
        [sys.executable, "-u", str(script), "--date", target_date],
        cwd=str(ROOT),
        check=False,
    )
    if completed.returncode != 0:
        print(f"WARNING: Today’s Card rebuild failed for {target_date}.")
        return False
    return True


def write_change_log(events: Sequence[Dict[str, Any]]) -> None:
    if not events:
        return
    CHANGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CHANGE_LOG.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    try:
        first = date.fromisoformat(args.date)
    except ValueError as error:
        raise SystemExit("Use --date YYYY-MM-DD") from error

    if args.days_ahead < 0 or args.days_ahead > 14:
        raise SystemExit("--days-ahead must be between 0 and 14")

    acquire_lock(args.force)
    started_at = iso_now()

    try:
        end = first + timedelta(days=args.days_ahead)
        schedule_games = fetch_schedule(first.isoformat(), end.isoformat())
        master = load_master()
        games: List[Dict[str, Any]] = master["games"]

        by_pk: Dict[int, Dict[str, Any]] = {}
        for game in games:
            game_pk = int_or_none(game.get("mlb_game_pk"))
            if game_pk:
                by_pk[game_pk] = game

        team_history = build_team_history(games)
        assigned: Dict[Tuple[int, str], set] = defaultdict(set)
        snapshot_cache: Dict[Tuple[int, str], Dict[str, Any]] = {}
        affected_dates = set()
        events: List[Dict[str, Any]] = []
        checked_slots = 0
        changed_slots = 0

        schedule_games.sort(
            key=lambda item: (
                str(item.get("gameDate") or ""),
                int_or_none(item.get("gamePk")) or 0,
            )
        )

        for schedule_game in schedule_games:
            game_pk = int_or_none(schedule_game.get("gamePk"))
            if not game_pk:
                continue
            stored = by_pk.get(game_pk)
            if not stored:
                print(f"Schedule game {game_pk} is not in games.json; skipped.")
                continue

            target_date = str(stored.get("date") or "")[:10]
            if not target_date:
                continue

            detailed_status = status_text(schedule_game)
            pitchers = copy.deepcopy(stored.get("pitchers") or {})

            for side in ("away", "home"):
                checked_slots += 1
                existing = copy.deepcopy(pitchers.get(side) or {})
                if existing:
                    existing["changed_since_last_refresh"] = False

                candidate = confirmed_from_live_feed(
                    game_pk,
                    side,
                    detailed_status,
                )
                if candidate is None:
                    candidate = official_probable(schedule_game, side)

                team_id = team_id_from_game(stored, side)

                if candidate is None and not args.no_projections and team_id:
                    existing_status = str(existing.get("status") or "unknown")
                    if not (
                        existing.get("id")
                        and existing_status in ("probable", "confirmed")
                    ):
                        candidate = choose_rotation_projection(
                            team_id,
                            target_date,
                            team_history,
                            assigned,
                        )

                if candidate is None:
                    pitchers[side] = existing
                    continue

                updated, changed, reason = merge_starter(
                    existing,
                    candidate,
                    target_date,
                    snapshot_cache,
                    args.force_snapshots,
                )
                pitchers[side] = updated

                bullpen_plan = (
                    confirmed_bullpen_plan_from_live_feed(
                        game_pk,
                        side,
                        detailed_status,
                        target_date,
                        snapshot_cache,
                    )
                )

                if bullpen_plan is None:
                    bullpen_plan = (
                        likely_bullpen_plan_from_transition(
                            existing,
                            updated,
                        )
                    )

                if bullpen_plan is None:
                    bullpen_plan = (
                        likely_bullpen_plan_from_history(
                            updated,
                            target_date,
                            snapshot_cache,
                        )
                    )

                if bullpen_plan:
                    stored.setdefault(
                        "bullpen_start",
                        {},
                    )[side] = bullpen_plan

                    updated[
                        "bullpen_start_detected"
                    ] = True

                    updated[
                        "bullpen_start_confidence"
                    ] = bullpen_plan.get(
                        "confidence"
                    )

                append_virtual_start(
                    team_id,
                    target_date,
                    candidate,
                    team_history,
                )

                if changed:
                    changed_slots += 1
                    affected_dates.add(target_date)
                    event = {
                        "recorded_at": iso_now(),
                        "game_pk": game_pk,
                        "game_id": stored.get("id"),
                        "date": target_date,
                        "side": side,
                        "team": team_name_from_game(stored, side),
                        "reason": reason,
                        "previous": compact_pitcher(existing),
                        "current": compact_pitcher(updated),
                    }
                    events.append(event)
                    print(
                        f"{target_date} {stored.get('id')} {side}: "
                        f"{existing.get('name') or 'TBD'} -> {updated.get('name')} "
                        f"[{updated.get('status')}; {reason}]"
                    )

            stored["pitchers"] = pitchers
            stored["starter_refresh"] = {
                "checked_at": iso_now(),
                "source": "MLB schedule/live feed + labeled rotation inference",
            }

        for target_date in sorted(affected_dates):
            rank_cache = load_rank_cache(target_date)
            if rank_cache:
                date_games = [
                    game for game in games if game.get("date") == target_date
                ]
                apply_league_pitcher_cache(date_games, rank_cache)

        if not args.dry_run and affected_dates:
            master["games"] = games
            master["starter_refresh"] = {
                "started_at": started_at,
                "finished_at": iso_now(),
                "first_date": first.isoformat(),
                "last_date": end.isoformat(),
                "affected_dates": sorted(affected_dates),
            }
            atomic_write_json(GAMES_FILE, master, compact=True)

            for target_date in sorted(affected_dates):
                update_public_shard(master, games, target_date)
                if not args.skip_card_data:
                    rebuild_card_date(target_date)

            write_change_log(events)

        status_payload = {
            "started_at": started_at,
            "finished_at": iso_now(),
            "dry_run": bool(args.dry_run),
            "first_date": first.isoformat(),
            "last_date": end.isoformat(),
            "schedule_games": len(schedule_games),
            "starter_slots_checked": checked_slots,
            "starter_slots_changed": changed_slots,
            "affected_dates": sorted(affected_dates),
            "events": events,
        }
        if not args.dry_run:
            atomic_write_json(STATUS_FILE, status_payload, compact=False)

        print()
        print("MLB starter refresh finished.")
        print(f"Schedule games checked: {len(schedule_games)}")
        print(f"Starter slots checked: {checked_slots}")
        print(f"Starter slots changed/repaired: {changed_slots}")
        print(f"Affected dates: {', '.join(sorted(affected_dates)) or 'none'}")
        print(
            "Projections are labeled rotation inferences. "
            "MLB probable/confirmed starters always take precedence."
        )
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
