#!/usr/bin/env python3

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT
    / "scripts/mlb/offense.py"
).read_text(encoding="utf-8")

checks = {
    "Arizona Savant alias":
        '"AZ": 109',
    "Cache schema":
        "OFFENSE_CACHE_SCHEMA = 4",
    "Recent cache window":
        "STATCAST_RECENT_CACHE_DAYS = 14",
    "Rank coverage floor":
        "MIN_OFFENSE_RANK_COVERAGE = 10",
    "Memory cache":
        "_STATCAST_DAY_MEMORY_CACHE",
    "Recent cache refresh":
        "and not recent_day",
    "Partial-response protection":
        "len(fetched_teams)",
    "Overall coverage gate":
        "overall_metric_coverage",
    "Handedness coverage gate":
        "split_metric_coverage",
}

errors = []

for label, marker in checks.items():
    if marker not in SOURCE:
        errors.append(
            f"{label} missing: {marker}"
        )

print("OFFENSE CACHE INTEGRITY CHECK")
print("=" * 38)

if errors:
    for error in errors:
        print("FAIL:", error)

    sys.exit(1)

for label in checks:
    print("PASS:", label)
