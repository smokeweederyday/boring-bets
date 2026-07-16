#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mlb.fangraphs import fetch_team_wrc_plus


def main() -> None:
    target_text = sys.argv[1] if len(sys.argv) > 1 else datetime.now().date().isoformat()
    target = datetime.strptime(target_text, "%Y-%m-%d").date()
    rows = fetch_team_wrc_plus(target - timedelta(days=30), target, "all", "overall")
    print(f"FanGraphs returned {len(rows)} MLB team wRC+ rows.")
    if len(rows) < 20:
        raise SystemExit("wRC+ verification failed: provider returned too few teams.")
    print(json.dumps(dict(sorted(rows.items())), indent=2))


if __name__ == "__main__":
    main()
