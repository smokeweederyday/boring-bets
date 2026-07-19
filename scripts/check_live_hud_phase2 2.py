from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    required = [
        ROOT / "live.html",
        ROOT / "live.css",
        ROOT / "live.js",
        ROOT / "assets/js/live/heatMapEngine.js",
        ROOT / "data/heatmaps/schema.json",
        ROOT / "data/ballparks/index.json",
        ROOT / "scripts/build_ballpark_geometry.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        print("FAIL: missing required files:")
        for item in missing:
            print(f"- {item}")
        return 1

    failures: list[str] = []
    html = (ROOT / "live.html").read_text(encoding="utf-8")
    javascript = (ROOT / "live.js").read_text(encoding="utf-8")
    engine = (ROOT / "assets/js/live/heatMapEngine.js").read_text(encoding="utf-8")
    html_ids = re.findall(r'id="([^"]+)"', html)
    duplicates = sorted({item for item in html_ids if html_ids.count(item) > 1})
    js_ids = set(re.findall(r'\$\("([^"]+)"\)', javascript))
    missing_ids = sorted(js_ids - set(html_ids))

    parks_payload = load_json(ROOT / "data/ballparks/index.json")
    parks = parks_payload.get("parks", [])
    verified = 0
    working = 0
    for park in parks:
        geometry = park.get("field_geometry") or {}
        contract = geometry.get("coordinate_contract") or {}
        points = geometry.get("wall_points_feet") or []
        if contract.get("units") != "feet":
            failures.append(f"park {park.get('id')} does not use feet")
            break
        if len(points) < 5:
            failures.append(f"park {park.get('id')} has fewer than five wall control points")
            break
        for point in points:
            if not all(key in point for key in ("x_ft", "y_ft", "distance_ft")):
                failures.append(f"park {park.get('id')} has an incomplete wall point")
                break
        if geometry.get("verification_status") == "verified":
            verified += 1
        else:
            working += 1

    heat_schema = load_json(ROOT / "data/heatmaps/schema.json")
    if heat_schema.get("matrix_contract", {}).get("grid") != "5x5":
        failures.append("heat-map grid contract is not 5x5")
    if "plate_x" not in heat_schema.get("pitch_coordinate_contract", {}).get("source_fields", []):
        failures.append("heat-map coordinate contract is missing plate_x")

    for required_id in ("fieldHudView", "plateHudView", "strikeZoneGrid", "fieldViewButton", "plateViewButton", "autoViewButton"):
        if required_id not in html_ids:
            failures.append(f"missing Phase 2 HUD element: {required_id}")

    if duplicates:
        failures.append(f"duplicate HTML IDs: {', '.join(duplicates)}")
    if missing_ids:
        failures.append(f"live.js references missing HTML IDs: {', '.join(missing_ids)}")
    if "prototype_not_statcast_connected" not in engine:
        failures.append("heat-map engine is missing its prototype disclosure status")

    node = shutil.which("node")
    if node:
        for script in (ROOT / "live.js", ROOT / "assets/js/live/heatMapEngine.js"):
            result = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
            if result.returncode:
                failures.append(f"JavaScript syntax failure in {script.relative_to(ROOT)}: {result.stderr.strip()}")
        javascript_check = "PASS (Node.js syntax check)"
    else:
        javascript_check = "SKIPPED (Node.js is not installed; non-blocking)"

    print(f"Ballpark profiles: {len(parks)}")
    print(f"Verified dimension profiles: {verified}")
    print(f"Calibration-pending profiles: {working}")
    print(f"Wall control points: {sum(len((park.get('field_geometry') or {}).get('wall_points_feet') or []) for park in parks)}")
    print(f"Live HTML element IDs: {len(html_ids)}")
    print("HUD views: Field + Plate + Auto")
    print("Heat-map layers: Batter + Pitcher + Live + Combined")
    print(f"JavaScript syntax check: {javascript_check}")

    if failures:
        print("FAIL:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: Live HUD Phase 2 coordinate systems and heat-map framework are internally consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
