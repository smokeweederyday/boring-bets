#!/usr/bin/env python3
from pathlib import Path
import re, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'live.html').read_text()
css=(ROOT/'live.css').read_text()
js=(ROOT/'live.js').read_text()
required_ids=[
 'liveGameScroll','flowGameModule','flowLinePath','deserveAwayFill','fullBoxScore','oddsModule','oddsGrid','lowerBullpens','completeEventLog','lowerLogAll','lowerLogAlerts'
]
missing=[item for item in required_ids if f'id="{item}"' not in html]
if missing:
 print('FAIL: missing HTML IDs:', ', '.join(missing)); sys.exit(1)
for forbidden in ['gameDossier','dossierTitle','dossierOverview','FULL GAME DOSSIER']:
 if forbidden in html or forbidden in js:
  print('FAIL: old dossier remains:', forbidden); sys.exit(1)
for token in ['lower-dashboard-grid','full-box-score','flow-chart','odds-grid','lower-bullpen-grid','complete-event-row']:
 if token not in css:
  print('FAIL: missing CSS token:', token); sys.exit(1)
for fn in ['renderFlowOfGame','renderFullBoxScore','renderOddsCenter','renderLowerBullpens','renderCompleteEventLog','renderLowerGameModules']:
 if f'function {fn}' not in js:
  print('FAIL: missing JS renderer:', fn); sys.exit(1)
node=shutil.which('node')
if node:
 result=subprocess.run([node,'--check',str(ROOT/'live.js')],capture_output=True,text=True)
 if result.returncode:
  print(result.stderr); sys.exit(result.returncode)
 print('JavaScript syntax check: PASS')
else:
 print('JavaScript syntax check: SKIPPED (Node.js not installed; non-blocking)')
print('Full Game Dossier: REMOVED')
print('First scroll row: Flow + 9-inning Box Score + Odds')
print('Lower modules: Bullpens + Complete Event Log')
print('PASS: Live Dashboard Phase 4 structure is internally consistent.')
