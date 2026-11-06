#!/usr/bin/env python
"""Aggregate metrics with bootstrap 95% CIs.

    python scripts/analyze.py --logs results/logs --out results/summaries

Reports aggregate metrics only. It never prints trajectories, messages or tool
calls, so it is safe to run on attack logs before the policy freeze (Phase 1).

Safety and audit-threshold calibration use ControlArena's analysis utilities;
that wiring is built in step 2/5 against docs/CONTROLARENA_API_NOTES.md.
Runs tagged draft_policy are excluded from main results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--logs", type=Path, default=REPO / "results" / "logs")
    p.add_argument("--out", type=Path, default=REPO / "results" / "summaries")
    p.add_argument("--n-boot", type=int, default=10_000)
    p.add_argument("--include-draft", action="store_true")
    p.parse_args(argv)
    raise NotImplementedError("Log loading is built in step 2 after the ControlArena API check.")


if __name__ == "__main__":
    raise SystemExit(main())
