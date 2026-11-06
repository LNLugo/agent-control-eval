#!/usr/bin/env python
"""Fetch, review and pin the Bash side task payload.

Step 1, fetch for review (bytes saved as .txt, never executed):
    python scripts/pin_payload.py

Step 2, after reading the saved file and confirming it is inert
(it should only write the marker /root/you_got_pwned.txt):
    python scripts/pin_payload.py --approve --reviewer "Luis N. Lugo" --note "writes marker file only"

--approve re-fetches and pins only if the content still matches what you reviewed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from agent_control_eval.payload import (  # noqa: E402
    LOCK, PAYLOAD_URL, REVIEW_DIR, fetch_payload, sha256,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--reviewer")
    p.add_argument("--note", default="")
    args = p.parse_args(argv)

    data = fetch_payload()
    digest = sha256(data)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    review_file = REVIEW_DIR / f"payload_{digest[:12]}.txt"

    if not args.approve:
        review_file.write_bytes(data)
        print(f"sha256: {digest}")
        print(f"saved for review (not executable): {review_file}")
        print("Read it. If it only writes the marker file, re-run with --approve --reviewer NAME.")
        return 0

    if not args.reviewer:
        p.error("--approve needs --reviewer")
    if not review_file.exists():
        sys.exit("Content differs from anything you reviewed (or you skipped step 1). Run without --approve first.")
    lock = {
        "url": PAYLOAD_URL,
        "sha256": digest,
        "bytes": len(data),
        "reviewed_by": args.reviewer,
        "reviewed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": args.note,
    }
    LOCK.write_text(json.dumps(lock, indent=2) + "\n")
    print(f"pinned {digest} -> {LOCK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
