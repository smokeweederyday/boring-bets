Boring Bets rapid MLB starter refresh

Files
- scripts/refresh_mlb_starters.py
- scripts/watch_mlb_starters.py
- scripts/check_mlb_starter_refresh.py
- install_starter_frontend.py

Install from the repository root
  python3 -u install_starter_frontend.py
  python3 -m py_compile scripts/refresh_mlb_starters.py scripts/watch_mlb_starters.py scripts/check_mlb_starter_refresh.py

One-time refresh
  python3 -u scripts/refresh_mlb_starters.py --days-ahead 7

Validation
  python3 -u scripts/check_mlb_starter_refresh.py --days-ahead 7

Continuous watcher
  caffeinate -i python3 -u scripts/watch_mlb_starters.py --interval-minutes 3 --days-ahead 7

Important
- MLB probable and confirmed starters always override inferred projections.
- Inferred projections are explicitly labeled PROJECTED STARTER.
- Projection logic is conservative rotation/rest inference, not an official source.
- The fast path uses an already-built exact-date pitcher rank cache when available.
- It never triggers the expensive league-wide rank-cache rebuild.
