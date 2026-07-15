#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
STYLES = ROOT / "styles.css"

MARKER = "/* BORING BETS CONTEXT V2 UI */"

CSS = r"""

/* BORING BETS CONTEXT V2 UI */

.context-columns-v2 {
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
}

.context-negative {
  border-left-color: #ff8e62;
  background: rgba(255, 142, 98, 0.08);
}

.context-negative strong {
  color: #ffb08d;
}

.context-item-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.context-team-tag {
  flex: 0 0 auto;
  padding: 2px 5px;
  color: var(--teal);
  font-family: var(--font-data);
  font-size: 0.52rem;
  border: 1px solid rgba(24, 216, 216, 0.24);
  border-radius: 999px;
}

.context-group h3 {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.context-group h3 span {
  color: var(--muted);
}

@media (max-width: 1050px) {
  .context-columns-v2 {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .context-columns-v2 {
    grid-template-columns: 1fr;
  }
}
"""


def main() -> None:
    if not STYLES.exists():
        raise SystemExit(
            "Run this from the Boring Bets project."
        )

    text = STYLES.read_text(
        encoding="utf-8"
    )

    if MARKER in text:
        print(
            "Context V2 styles already installed."
        )
        return

    backup = STYLES.with_suffix(
        ".css.before-context-v2"
    )

    if not backup.exists():
        shutil.copy2(
            STYLES,
            backup,
        )

    STYLES.write_text(
        text.rstrip()
        + "\n"
        + CSS
        + "\n",
        encoding="utf-8",
    )

    print(
        "Installed Context V2 styles."
    )


if __name__ == "__main__":
    main()
