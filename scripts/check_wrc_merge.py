#!/usr/bin/env python3
from __future__ import annotations
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mlb.fangraphs import fetch_team_wrc_plus, fetch_raw_team_wrc_rows


def main() -> int:
    target = datetime.strptime(sys.argv[1] if len(sys.argv) > 1 else datetime.now().date().isoformat(), "%Y-%m-%d").date()
    rows = fetch_team_wrc_plus(target - timedelta(days=30), target, "all", "overall")
    print(f"Mapped {len(rows)} FanGraphs rows to MLB team IDs.")
    for team_id, abbr in ((121, "NYM"), (143, "PHI"), (147, "NYY"), (119, "LAD")):
        print(f"{abbr} ({team_id}): {rows.get(team_id, 'MISSING')}")
    if len(rows) < 20 or not any(team_id in rows for team_id in (121,143,147,119)):
        print("FAIL: wRC+ rows were fetched but not mapped to MLB team IDs.")
        raw_rows = fetch_raw_team_wrc_rows(target - timedelta(days=30), target, "all", "overall")
        if raw_rows:
            print("First FanGraphs row keys:", sorted(raw_rows[0].keys()))
            print("First FanGraphs row:", raw_rows[0])
        return 1
    print("PASS: wRC+ is mapped into the MLB ID namespace used by games.json.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
