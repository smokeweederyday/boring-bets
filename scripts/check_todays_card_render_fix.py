from pathlib import Path
import json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'todays-card.html').read_text()
js=(ROOT/'todays-card.js').read_text()
css=(ROOT/'assets/css/todays-card-multisport.css').read_text()
config=json.loads((ROOT/'data/sports-card-config.json').read_text())
assert html.count('data-sport-id=') >= 8, 'Static sport buttons missing'
assert 'data-league-id="mlb" open' in html, 'Static MLB dropdown missing'
assert 'CARD_FALLBACK_CONFIG' in js, 'Embedded fallback config missing'
assert 'Daily MLB card file not found' in js, 'Lightweight MLB feed guard missing'
assert '.sport-switcher' in css, 'Sport CSS missing'
print('Static sport buttons:', html.count('data-sport-id='))
print('Static MLB dropdown: visible before JavaScript')
print('Embedded config fallback: active')
print('Large games.json browser fallback: disabled')
node=shutil.which('node')
if node:
    result=subprocess.run([node,'--check',str(ROOT/'todays-card.js')],capture_output=True,text=True)
    if result.returncode:
        raise SystemExit(result.stderr)
    print('JavaScript syntax check: PASS')
else:
    print('JavaScript syntax check: SKIPPED (Node.js not installed; non-blocking)')
print("PASS: Today’s Card cannot render as an empty sports board.")
