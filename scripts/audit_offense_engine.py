#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "nym-phi-sample.json"
raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
games = raw.get("games", raw)
issues=[]
for game in games:
    print(f"Game: {game.get('id')}")
    for side in ("away","home"):
        team=game.get(f"{side}_team",{}).get("abbr",side)
        stats=game.get("offense",{}).get(side,{}).get("stats",{})
        print(f"\n{team}")
        signatures={"all_vs":[],"loc_vs":[],"overall":[]}
        for tf in ("last_7","last_30","season"):
            all_block=stats.get(tf,{}).get("all",{}).get("AVG",{})
            loc_block=stats.get(tf,{}).get(side,{}).get("AVG",{})
            row=(all_block.get("overall"),all_block.get("overall_rank"),all_block.get("vs_hand"),all_block.get("vs_hand_rank"),loc_block.get("vs_hand"),loc_block.get("vs_hand_rank"))
            print(tf,row)
            signatures["overall"].append(row[:2])
            signatures["all_vs"].append(row[2:4])
            signatures["loc_vs"].append(row[4:6])
        if len(set(signatures["overall"])) == 1:
            issues.append(f"{team}: overall AVG/rank static across all timeframes")
        if len(set(signatures["all_vs"])) == 1:
            issues.append(f"{team}: vs-hand AVG/rank static across all timeframes")
        if len(set(signatures["loc_vs"])) == 1:
            issues.append(f"{team}: {side}-vs-hand AVG/rank static across all timeframes")

print("\nAUDIT RESULT")
for issue in issues:
    print(" -",issue)
if any("vs-hand" in x for x in issues):
    print("FAIL: handedness timeframes are not date-bounded.")
    raise SystemExit(1)
print("PASS: no static handedness reuse detected in sample.")
