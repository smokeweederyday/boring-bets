#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
path=root/'data'/'games.json'
raw=json.loads(path.read_text(encoding='utf-8'))
games=raw.get('games',raw) if isinstance(raw,dict) else raw
checked=0
issues=[]
for game in games:
    lineups=game.get('lineups')
    if not isinstance(lineups,dict): continue
    for side in ('away','home'):
        lineup=lineups.get(side)
        if not isinstance(lineup,dict) or not lineup.get('players'): continue
        checked+=1
        status=lineup.get('status')
        count=len(lineup.get('players') or [])
        comp=lineup.get('completeness') or {}
        mix=lineup.get('matchup_handedness') or {}
        print(f"{game.get('id')} {side}: status={status} players={count} mix={mix} confidence={lineup.get('confidence')}")
        if status not in {'unknown','projected','partial','confirmed'}: issues.append(f'{game.get("id")} {side}: bad status {status}')
        if comp.get('count') != count: issues.append(f'{game.get("id")} {side}: completeness mismatch')
        if count >= 9 and not lineup.get('signature'): issues.append(f'{game.get("id")} {side}: missing signature')
        if mix and (mix.get('lhh',0)+mix.get('rhh',0)+mix.get('unknown',0) != count): issues.append(f'{game.get("id")} {side}: handedness count mismatch')
    if checked>=4: break
if not checked: raise SystemExit('FAIL: no populated lineups found.')
if issues:
    print('FAIL:')
    for issue in issues: print(' -',issue)
    raise SystemExit(1)
print(f'PASS: verified {checked} lineup intelligence records.')
