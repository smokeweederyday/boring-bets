#!/usr/bin/env python3

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "data" / "games.json"

if not path.exists():
    raise SystemExit(f"Could not find games data at: {path}")

raw = json.loads(path.read_text(encoding="utf-8"))
games = raw.get("games", []) if isinstance(raw, dict) else raw

if not isinstance(games, list):
    raise SystemExit("games.json does not contain a usable games list.")

timeframes = ("last_7", "last_30", "season")
issues = []
checked = 0

for game in games:
    offense = game.get("offense")
    if not isinstance(offense, dict):
        continue

    for side in ("away", "home"):
        module = offense.get(side)
        if not isinstance(module, dict):
            continue

        stats = module.get("stats", {})
        team = game.get(f"{side}_team", {}).get("abbr", side.upper())
        location = "away" if side == "away" else "home"

        print(f"\n{game.get('id', 'unknown game')} — {team}")

        for timeframe in timeframes:
            period = stats.get(timeframe, {})
            overall = period.get("all", {})
            matchup_location = period.get(location, {})

            overall_avg = overall.get("AVG", {}).get("overall")
            overall_rank = overall.get("AVG", {}).get("overall_rank")

            hand_avg = overall.get("AVG", {}).get("vs_hand")
            hand_rank = overall.get("AVG", {}).get("vs_hand_rank")

            location_hand_avg = matchup_location.get("AVG", {}).get("vs_hand")
            location_hand_rank = matchup_location.get("AVG", {}).get("vs_hand_rank")

            print(
                f"{timeframe}: "
                f"overall={overall_avg} rank={overall_rank} | "
                f"vs hand={hand_avg} rank={hand_rank} | "
                f"{location} vs hand={location_hand_avg} "
                f"rank={location_hand_rank}"
            )

            if location_hand_avg is None:
                issues.append(
                    f"{team} {timeframe}: missing {location} vs starter-hand AVG"
                )

            if location_hand_rank is None:
                issues.append(
                    f"{team} {timeframe}: missing {location} vs starter-hand rank"
                )

            checked += 1

    if checked >= 6:
        break

if checked == 0:
    raise SystemExit("No enriched offense modules were found.")

if issues:
    print("\nFAIL:")
    for issue in issues[:20]:
        print(f" - {issue}")
    raise SystemExit(1)

print(
    f"\nPASS: checked {checked} offense timeframe/location-hand blocks."
)
