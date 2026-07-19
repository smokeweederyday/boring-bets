from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "data" / "ballparks" / "index.json"

# Five-point profiles are working field dimensions. They establish a real feet-based
# coordinate contract now; detailed wall surveying can add as many control points as needed.
DIMENSIONS = {
    1: (330, 387, 396, 370, 330),
    2: (333, 374, 410, 373, 318),
    3: (310, 379, 390, 380, 302),
    4: (330, 375, 400, 375, 335),
    5: (325, 370, 400, 375, 325),
    7: (347, 379, 410, 379, 344),
    12: (315, 370, 404, 370, 322),
    14: (328, 375, 400, 375, 328),
    15: (330, 374, 407, 374, 334),
    17: (355, 368, 400, 368, 353),
    19: (347, 390, 415, 375, 350),
    22: (330, 375, 395, 375, 330),
    31: (325, 383, 399, 375, 320),
    32: (344, 371, 400, 374, 345),
    680: (331, 378, 401, 381, 326),
    2392: (315, 362, 409, 373, 326),
    2394: (345, 370, 412, 365, 330),
    2395: (339, 364, 391, 415, 309),
    2529: (330, 380, 403, 380, 325),
    2602: (328, 379, 404, 370, 325),
    2680: (334, 357, 396, 391, 322),
    2681: (329, 374, 401, 369, 330),
    2735: (323, 385, 405, 385, 331),
    2889: (336, 375, 400, 375, 335),
    3289: (335, 358, 408, 375, 330),
    3309: (337, 377, 402, 370, 335),
    3312: (339, 377, 404, 367, 328),
    3313: (318, 399, 408, 385, 314),
    4169: (344, 386, 400, 387, 335),
    4705: (335, 385, 400, 375, 325),
    5325: (329, 372, 407, 374, 326),
    5340: (325, 375, 400, 375, 325),
    5355: (340, 380, 415, 380, 325),
    5445: (335, 375, 400, 375, 335),
}

# Parks with extra control points demonstrate that the schema supports actual wall shape,
# not merely five headline distances.
DETAILED_POINTS = {
    3: [
        ("LF", -45, 310, 37.2), ("GREEN MONSTER", -34, 315, 37.2),
        ("LCF", -24, 379, 17), ("DEEP LCF", -10, 390, 17),
        ("CF", 0, 390, 17), ("RCF", 22, 380, 5), ("RF", 45, 302, 3.5),
    ],
    2395: [
        ("LF", -45, 339, 8), ("LCF", -28, 364, 8), ("CF", 0, 391, 8),
        ("TRIPLES ALLEY", 21, 415, 8), ("RCF", 31, 399, 8), ("RF", 45, 309, 25),
    ],
    2681: [
        ("LF", -45, 329, 10.5), ("LCF", -28, 374, 10.5),
        ("MONTY 1", -18, 387, 12.7), ("MONTY 2", -11, 381, 12.7),
        ("MONTY 3", -5, 409, 19), ("CF", 0, 401, 6),
        ("RCF", 26, 369, 13.25), ("RF", 45, 330, 13.25),
    ],
    3313: [
        ("LF", -45, 318, 8), ("LCF", -25, 399, 8), ("CF", 0, 408, 8),
        ("RCF", 25, 385, 8), ("RF", 45, 314, 8),
    ],
}

VERIFIED = {
    2681: {
        "verification_status": "verified",
        "source_label": "Philadelphia Phillies official ballpark guide",
        "verified_on": "2026-07-19",
        "notes": "Headline distances and published wall heights mapped; detailed wall curve remains editable.",
    },
    7: {
        "verification_status": "verified",
        "source_label": "2026 Kauffman Stadium fence-change announcement",
        "verified_on": "2026-07-19",
        "notes": "2026 headline distances mapped; exact intermediate wall survey remains editable.",
    },
}


def point(label: str, angle_deg: float, distance_ft: float, wall_height_ft: float | None = None) -> dict:
    radians = math.radians(angle_deg)
    return {
        "label": label,
        "angle_deg": angle_deg,
        "distance_ft": distance_ft,
        "x_ft": round(math.sin(radians) * distance_ft, 3),
        "y_ft": round(math.cos(radians) * distance_ft, 3),
        "wall_height_ft": wall_height_ft,
    }


def geometry_for(venue_id: int) -> dict:
    lf, lcf, cf, rcf, rf = DIMENSIONS.get(venue_id, (330, 375, 400, 375, 330))
    raw_points = DETAILED_POINTS.get(
        venue_id,
        [("LF", -45, lf, None), ("LCF", -25, lcf, None), ("CF", 0, cf, None), ("RCF", 25, rcf, None), ("RF", 45, rf, None)],
    )
    verification = VERIFIED.get(
        venue_id,
        {
            "verification_status": "working_profile",
            "source_label": "published headline dimension profile; exact wall calibration pending",
            "verified_on": None,
            "notes": "Use as a dimension-aware working map, not a surveyed wall polygon.",
        },
    )
    return {
        "schema_version": "2.0",
        "coordinate_contract": {
            "origin": "rear point of home plate",
            "units": "feet",
            "x_axis": "negative toward left field; positive toward right field",
            "y_axis": "positive from home plate through center field",
            "field_bearing_reference": "center-field centerline",
        },
        "dimensions_ft": {
            "left_line": lf,
            "left_center": lcf,
            "center": cf,
            "right_center": rcf,
            "right_line": rf,
        },
        "wall_points_feet": [point(*item) for item in raw_points],
        "infield": {
            "basepath_ft": 90,
            "mound_distance_ft": 60.5,
            "base_coordinates_ft": {
                "home": [0, 0], "first": [63.64, 63.64], "second": [0, 127.28], "third": [-63.64, 63.64]
            },
        },
        "verification_status": verification["verification_status"],
        "source_label": verification["source_label"],
        "verified_on": verification["verified_on"],
        "notes": verification["notes"],
    }


def main() -> int:
    payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    payload["schema_version"] = "2.0"
    payload["note"] = "Feet-based field coordinate system. Verified parks are labeled; working profiles remain explicitly calibration-pending."
    for park in payload.get("parks", []):
        park["version"] = "V0.2"
        park["field_geometry"] = geometry_for(int(park["id"]))
        park["status"] = "dimension_mapped" if park["field_geometry"]["verification_status"] == "verified" else "coordinate_ready_calibration_pending"
        individual = ROOT / "data" / "ballparks" / f"venue-{park['id']}.json"
        individual.write_text(json.dumps(park, indent=2) + "\n", encoding="utf-8")
    INDEX_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    verified = sum(1 for park in payload["parks"] if park["field_geometry"]["verification_status"] == "verified")
    print(f"Wrote {len(payload['parks'])} feet-based park profiles ({verified} verified, {len(payload['parks']) - verified} calibration-pending).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
