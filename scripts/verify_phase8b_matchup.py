#!/usr/bin/env python3
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
path=root/'data'/'games.json'
raw=json.loads(path.read_text())
games=raw.get('games',raw) if isinstance(raw,dict) else raw
checked=0
issues=[]
for game in games:
    if not isinstance(game.get('lineups'),dict) or not isinstance(game.get('pitchers'),dict) or not isinstance(game.get('offense'),dict):
        continue
    for pitcher_side,lineup_side,offense_side in [('away','home','home'),('home','away','away')]:
        lineup=game['lineups'].get(lineup_side,{})
        pitcher=game['pitchers'].get(pitcher_side,{})
        offense=game['offense'].get(offense_side,{})
        players=lineup.get('players') or []
        mix=lineup.get('matchup_handedness') or {}
        print(f"{game.get('id')} {pitcher_side}: pitcher={pitcher.get('name')} lineup={len(players)} mix={mix}")
        if len(players) not in range(1,10): issues.append(f"{game.get('id')} {pitcher_side}: no usable lineup")
        if not pitcher.get('throws'): issues.append(f"{game.get('id')} {pitcher_side}: missing pitcher hand")
        if not offense.get('stats'): issues.append(f"{game.get('id')} {pitcher_side}: missing offense stats")
        if not mix: issues.append(f"{game.get('id')} {pitcher_side}: missing matchup handedness")
        checked+=1
        if checked>=4: break
    if checked>=4: break
if issues:
    print('FAIL:')
    for issue in issues: print(' -',issue)
    raise SystemExit(1)
print(f'PASS: verified {checked} lineup-aware matchup inputs.')
