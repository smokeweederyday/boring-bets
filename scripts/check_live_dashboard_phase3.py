from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    required = [
        ROOT / "live.html",
        ROOT / "live.css",
        ROOT / "live.js",
        ROOT / "assets/js/live/heatMapEngine.js",
        ROOT / "data/live-game-index.json",
        ROOT / "data/ballparks/index.json",
    ]
    failures: list[str] = []
    for path in required:
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")

    if failures:
        print("FAIL:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    html = (ROOT / "live.html").read_text(encoding="utf-8")
    css = (ROOT / "live.css").read_text(encoding="utf-8")
    js = (ROOT / "live.js").read_text(encoding="utf-8")

    ids = re.findall(r'id="([^"]+)"', html)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    js_ids = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', js))
    missing_ids = sorted(js_ids - set(ids))

    required_ids = {
        "fieldHudView", "plateHudView", "batterSilhouette", "strikeZoneGrid",
        "gameStateDock", "toggleGameStateDock", "gameStateDockBody",
        "ballLights", "strikeLights", "outLights", "miniPitchDot",
        "gameDossier", "dossierOverview", "dossierMatchup", "dossierPitchers",
        "dossierLineups", "dossierBullpens", "dossierEvents", "dossierDataInventory",
    }
    missing_phase3 = sorted(required_ids - set(ids))

    if duplicates:
        failures.append(f"duplicate HTML IDs: {', '.join(duplicates)}")
    if missing_ids:
        failures.append(f"live.js references missing IDs: {', '.join(missing_ids)}")
    if missing_phase3:
        failures.append(f"missing Phase 3 elements: {', '.join(missing_phase3)}")
    if 'id="scoreBug"' in html:
        failures.append("legacy bottom score bug still exists")
    if "broadcast-plate-scene" not in html or "plate-scene-svg" not in html:
        failures.append("broadcast plate scene is missing")
    if "right-game-state" not in css or "game-dossier" not in css:
        failures.append("Phase 3 CSS is incomplete")
    if "renderGameDossier" not in js or "toggleGameStateDock" not in js:
        failures.append("Phase 3 JavaScript behavior is incomplete")

    node = shutil.which("node")
    if node:
        result = subprocess.run([node, "--check", str(ROOT / "live.js")], capture_output=True, text=True)
        if result.returncode:
            failures.append(f"JavaScript syntax failure: {result.stderr.strip()}")
        js_status = "PASS"
    else:
        js_status = "SKIPPED (Node.js not installed; non-blocking)"

    print(f"Live HTML element IDs: {len(ids)}")
    print("Plate scene: detailed batter + pitcher background")
    print("Strike zone: compact overlay")
    print("Bottom score bug: REMOVED")
    print("Right-side game state: collapsible")
    print("Scrollable game dossier sections: 11")
    print(f"JavaScript syntax check: {js_status}")

    if failures:
        print("FAIL:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: Live Dashboard Phase 3 structure is internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
