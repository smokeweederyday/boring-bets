from __future__ import annotations

from collections import defaultdict
from typing import Any
import json
import urllib.request


MLB_LIVE_API_BASE = "https://statsapi.mlb.com/api/v1.1/game"


HIT_BASES = {
    "single": 1,
    "double": 2,
    "triple": 3,
    "home_run": 4,
}

WALK_EVENTS = {
    "walk",
    "intent_walk",
}

STRIKEOUT_EVENTS = {
    "strikeout",
    "strikeout_double_play",
}

SAC_FLY_EVENTS = {
    "sac_fly",
}

SAC_BUNT_EVENTS = {
    "sac_bunt",
}

HIT_BY_PITCH_EVENTS = {
    "hit_by_pitch",
}

NON_AT_BAT_EVENTS = (
    WALK_EVENTS
    | SAC_FLY_EVENTS
    | SAC_BUNT_EVENTS
    | HIT_BY_PITCH_EVENTS
    | {"catcher_interf"}
)


def fetch_live_game(game_pk: int) -> dict[str, Any]:
    url = f"{MLB_LIVE_API_BASE}/{game_pk}/feed/live"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BoringBets/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def empty_totals(
    batter_id: int,
    pitcher_id: int,
    batter_name: str | None = None,
    pitcher_name: str | None = None,
) -> dict[str, Any]:
    return {
        "batter_id": batter_id,
        "batter_name": batter_name,
        "pitcher_id": pitcher_id,
        "pitcher_name": pitcher_name,
        "plate_appearances": 0,
        "at_bats": 0,
        "hits": 0,
        "singles": 0,
        "doubles": 0,
        "triples": 0,
        "home_runs": 0,
        "total_bases": 0,
        "strikeouts": 0,
        "walks": 0,
        "intentional_walks": 0,
        "hit_by_pitch": 0,
        "sac_flies": 0,
        "sac_bunts": 0,
        "catcher_interference": 0,
    }


def add_plate_appearance(
    totals: dict[str, Any],
    event_type: str,
) -> None:
    totals["plate_appearances"] += 1

    if event_type not in NON_AT_BAT_EVENTS:
        totals["at_bats"] += 1

    if event_type in HIT_BASES:
        bases = HIT_BASES[event_type]
        totals["hits"] += 1
        totals["total_bases"] += bases

        if event_type == "single":
            totals["singles"] += 1
        elif event_type == "double":
            totals["doubles"] += 1
        elif event_type == "triple":
            totals["triples"] += 1
        elif event_type == "home_run":
            totals["home_runs"] += 1

    if event_type in STRIKEOUT_EVENTS:
        totals["strikeouts"] += 1

    if event_type in WALK_EVENTS:
        totals["walks"] += 1

    if event_type == "intent_walk":
        totals["intentional_walks"] += 1

    if event_type in HIT_BY_PITCH_EVENTS:
        totals["hit_by_pitch"] += 1

    if event_type in SAC_FLY_EVENTS:
        totals["sac_flies"] += 1

    if event_type in SAC_BUNT_EVENTS:
        totals["sac_bunts"] += 1

    if event_type == "catcher_interf":
        totals["catcher_interference"] += 1


def calculate_rates(
    totals: dict[str, Any],
) -> dict[str, Any]:
    row = dict(totals)

    pa = int(row.get("plate_appearances") or 0)
    ab = int(row.get("at_bats") or 0)
    hits = int(row.get("hits") or 0)
    walks = int(row.get("walks") or 0)
    hbp = int(row.get("hit_by_pitch") or 0)
    sac_flies = int(row.get("sac_flies") or 0)
    total_bases = int(row.get("total_bases") or 0)
    strikeouts = int(row.get("strikeouts") or 0)

    avg = hits / ab if ab else None

    obp_denominator = (
        ab
        + walks
        + hbp
        + sac_flies
    )

    obp = (
        (hits + walks + hbp) / obp_denominator
        if obp_denominator
        else None
    )

    slg = total_bases / ab if ab else None

    row["avg"] = round(avg, 3) if avg is not None else None
    row["obp"] = round(obp, 3) if obp is not None else None
    row["slg"] = round(slg, 3) if slg is not None else None
    row["ops"] = (
        round(obp + slg, 3)
        if obp is not None and slg is not None
        else None
    )
    row["strikeout_rate"] = round(strikeouts / pa, 3) if pa else None
    row["walk_rate"] = round(walks / pa, 3) if pa else None
    row["available"] = pa > 0

    return row


def summarize_game_matchups(
    raw_game: dict[str, Any],
) -> dict[tuple[int, int], dict[str, Any]]:
    totals_by_matchup: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    plays = (
        raw_game
        .get("liveData", {})
        .get("plays", {})
        .get("allPlays", [])
    )

    for play in plays:
        result = play.get("result") or {}

        if result.get("type") != "atBat":
            continue

        event_type = str(
            result.get("eventType") or ""
        ).strip()

        matchup = play.get("matchup") or {}
        batter = matchup.get("batter") or {}
        pitcher = matchup.get("pitcher") or {}

        batter_id = batter.get("id")
        pitcher_id = pitcher.get("id")

        if not batter_id or not pitcher_id or not event_type:
            continue

        key = (int(batter_id), int(pitcher_id))

        if key not in totals_by_matchup:
            totals_by_matchup[key] = empty_totals(
                batter_id=int(batter_id),
                pitcher_id=int(pitcher_id),
                batter_name=batter.get("fullName"),
                pitcher_name=pitcher.get("fullName"),
            )

        add_plate_appearance(
            totals_by_matchup[key],
            event_type,
        )

    return {
        key: calculate_rates(totals)
        for key, totals in totals_by_matchup.items()
    }
