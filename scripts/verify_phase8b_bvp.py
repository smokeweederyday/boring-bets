#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
raw=json.loads((root/'data/games.json').read_text())
games=raw.get('games',raw)
checked=0; issues=[]
for game in reversed(games):
    bvp=game.get('pitcher_vs_lineup',{})
    for key in ('away_pitcher','home_pitcher'):
        rows=bvp.get(key,{}).get('batters',{})
        if not rows: continue
        available=[r for r in rows.values() if r.get('available')]
        print(game.get('id'),key,'batters=',len(rows),'available=',len(available))
        for row in available[:3]:
            print(' ',row.get('name'),row.get('plate_appearances'),'PA',row.get('strikeouts'),'K',row.get('walks'),'BB',row.get('avg'),'AVG',row.get('ops'),'OPS')
            if row.get('plate_appearances',0)<0: issues.append('negative PA')
        checked+=1
        if checked>=2: break
    if checked>=2: break
if checked==0: issues.append('No pitcher_vs_lineup batter records found.')
if issues:
    print('FAIL:'); [print(' -',x) for x in issues]; raise SystemExit(1)
print('PASS: batter-vs-pitcher lineup records are present.')
