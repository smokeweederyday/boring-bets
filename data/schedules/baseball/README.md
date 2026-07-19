# Baseball season schedules

`build_minor_league_schedules.py` writes one compact season archive per affiliated level:

- `data/schedules/baseball/<season>/triple-a.json`
- `data/schedules/baseball/<season>/double-a.json`
- `data/schedules/baseball/<season>/high-a.json`
- `data/schedules/baseball/<season>/single-a.json`
- `data/schedules/baseball/<season>/rookie.json`

Today’s Card opens only the selected league file and filters its events to the active card date. A date-specific refresh also writes a lightweight daily shard under `data/cards/YYYY-MM-DD/`.
