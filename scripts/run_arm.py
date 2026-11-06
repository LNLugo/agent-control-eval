#!/usr/bin/env python
"""Run one arm in one mode.

    python scripts/run_arm.py --arm A4 --mode honest --epochs 3
    python scripts/run_arm.py --arm A4 --mode attack --attack-policy P1 --epochs 3

Writes the Inspect log to results/logs/ and a run manifest beside it. Refuses to
run if models.yaml has unset required fields, if the arm is deferred, or if an
enforcement arm's policy is not frozen (override for Phase 1/dev with --allow-draft-policy;
draft-policy runs are tagged and excluded by analyze.py).
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from agent_control_eval.enforcement import load_policy  # noqa: E402
from agent_control_eval.manifest import (  # noqa: E402
    build_manifest, load_arms, load_models, write_manifest,
)

LOG_DIR = REPO / "results" / "logs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arm", required=True)
    p.add_argument("--mode", required=True, choices=["honest", "attack"])
    p.add_argument("--attack-policy", choices=["P1", "P2", "P3"])
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--limit", type=int, help="number of main tasks (fixed by PREREGISTRATION for main runs)")
    p.add_argument("--allow-draft-policy", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="validate config and write manifest only")
    args = p.parse_args(argv)
    if args.mode == "attack" and not args.attack_policy:
        p.error("--attack-policy is required in attack mode")
    if args.mode == "honest" and args.attack_policy:
        p.error("--attack-policy is only valid in attack mode")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    arms = load_arms()
    if args.arm not in arms["arms"]:
        sys.exit(f"unknown arm {args.arm}")
    arm_def = arms["arms"][args.arm]
    if arm_def["status"] == "deferred":
        sys.exit(f"arm {args.arm} is deferred to v0.2")
    if args.arm == "T0" and args.mode != "honest":
        sys.exit("T0 (trusted only) runs in honest mode only")
    if args.attack_policy and arms["attack_policies"][args.attack_policy]["status"] != "active":
        sys.exit(f"attack policy {args.attack_policy} is not active")

    models = load_models()

    policy_sha = None
    tags = []
    if arm_def.get("enforcement"):
        policy = load_policy(REPO / arm_def["enforcement"]["policy"])
        if policy.status != "frozen":
            if not args.allow_draft_policy:
                sys.exit("policy is not frozen; pass --allow-draft-policy for development runs")
            tags.append("draft_policy")
        policy_sha = policy.sha256

    run_id = f"{args.arm}-{args.mode}-{args.attack_policy or 'none'}-{uuid.uuid4().hex[:8]}"
    manifest = build_manifest(
        run_id=run_id, arm=args.arm, mode=args.mode, attack_policy=args.attack_policy,
        epochs=args.epochs, models=models, arm_def=arm_def, policy_sha256=policy_sha,
        extra={"limit": args.limit, "tags": tags},
    )
    path = write_manifest(manifest, LOG_DIR)
    print(f"manifest: {path}")
    if args.dry_run:
        return 0

    # Step 2: build the ControlArena task for this arm and call inspect_ai.eval(...)
    # against the API recorded in docs/CONTROLARENA_API_NOTES.md.
    raise NotImplementedError("Protocol wiring is built in step 2 after the ControlArena API check.")


if __name__ == "__main__":
    raise SystemExit(main())
