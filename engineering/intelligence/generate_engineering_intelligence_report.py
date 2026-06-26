#!/usr/bin/env python3
"""Generate the Slate Pocket v1R engineering intelligence demo report."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engineering.intelligence.decision_intelligence import build_report  # noqa: E402

REPORT_PATH = REPO_ROOT / "reports" / "slate-pocket-v1r-engineering-intelligence.txt"


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
