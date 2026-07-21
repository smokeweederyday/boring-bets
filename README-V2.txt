Boring Bets starter refresh v2

Fixes:
- A single MLB API timeout no longer aborts the full starter slate.
- Snapshot requests retry twice, then publish the starter identity with snapshot_status=pending.
- The next watcher cycle automatically retries pending/incomplete snapshots.
- First-career starters with a complete but empty Last Starts sample are no longer treated as broken.
- Future dates may use the newest safe prior-date pitcher-rank cache for handedness/rank display.
