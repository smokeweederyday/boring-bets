#!/usr/bin/env python3
"""Create and migrate readable stadium-name image folders."""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENUES_JSON = ROOT / "data" / "venues.json"
DEST = ROOT / "assets" / "images" / "stadiums" / "venues"


def slugify(value):
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def collect_venues(value, found):
    if isinstance(value, dict):
        venue_id = (
            value.get("id")
            or value.get("venue_id")
            or value.get("venueId")
        )
        name = (
            value.get("name")
            or value.get("venue_name")
            or value.get("venueName")
        )

        if venue_id is not None and name:
            text_id = str(venue_id).strip()
            text_name = str(name).strip()

            if text_id.isdigit() and text_name:
                found[text_id] = text_name

        for child in value.values():
            collect_venues(child, found)

    elif isinstance(value, list):
        for child in value:
            collect_venues(child, found)


def main():
    DEST.mkdir(parents=True, exist_ok=True)

    if not VENUES_JSON.exists():
        raise SystemExit(f"Missing {VENUES_JSON}")

    data = json.loads(VENUES_JSON.read_text(encoding="utf-8"))
    venues = {}
    collect_venues(data, venues)

    used_folders = {}
    index = []

    for venue_id, name in sorted(
        venues.items(),
        key=lambda item: (item[1].lower(), int(item[0])),
    ):
        base_slug = slugify(name) or f"venue-{venue_id}"
        folder_slug = base_slug

        if (
            folder_slug in used_folders
            and used_folders[folder_slug] != venue_id
        ):
            folder_slug = f"{base_slug}-{venue_id}"

        used_folders[folder_slug] = venue_id

        folder = DEST / folder_slug
        folder.mkdir(parents=True, exist_ok=True)

        numeric_folder = DEST / venue_id

        if numeric_folder.exists() and numeric_folder != folder:
            for source in numeric_folder.iterdir():
                target = folder / source.name

                if source.is_file() and not target.exists():
                    shutil.copy2(source, target)
                elif source.is_dir() and not target.exists():
                    shutil.copytree(source, target)

            shutil.rmtree(numeric_folder)

        manifest = {
            "venue_id": venue_id,
            "venue_name": name,
            "folder": folder_slug,
            "preferred_format": "webp",
            "recommended_size": {
                "width": 1916,
                "height": 821,
            },
        }

        (folder / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        index.append(manifest)

    (DEST / "venue-index.json").write_text(
        json.dumps(index, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"PASS: prepared {len(index)} stadium-name folders in {DEST}"
    )


# BORING BETS: BUILD UNIVERSAL VENUE IMAGE INDEX V1
if __name__ == "__main__":
    main()
    from build_venue_image_index import main as build_venue_index
    build_venue_index()
