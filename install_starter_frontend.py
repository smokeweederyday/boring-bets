#!/usr/bin/env python3
"""Patch the game-page pitcher label for projected starters."""
from pathlib import Path
from datetime import datetime
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "assets" / "js" / "sports" / "mlbEngine.js"

if not TARGET.exists():
    raise SystemExit(f"Missing {TARGET}")

text = TARGET.read_text(encoding="utf-8")

needle = '''  if (status === "probable") {
    return "PROBABLE STARTER";
  }

  if (status === "bullpen") {'''

replacement = '''  if (status === "probable") {
    return "PROBABLE STARTER";
  }

  if (status === "projected") {
    return "PROJECTED STARTER";
  }

  if (status === "bullpen") {'''

if replacement in text:
    print("Projected starter frontend label already installed.")
elif needle not in text:
    raise SystemExit(
        "Could not find formatPitcherStatus insertion point in "
        "assets/js/sports/mlbEngine.js"
    )
else:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = (
        Path.home()
        / "Desktop"
        / "boring-bets-backups"
        / f"starter-refresh-{stamp}"
    )
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, backup / "mlbEngine.js")
    TARGET.write_text(text.replace(needle, replacement, 1), encoding="utf-8")
    print("Installed PROJECTED STARTER label.")
    print(f"Backup: {backup / 'mlbEngine.js'}")
