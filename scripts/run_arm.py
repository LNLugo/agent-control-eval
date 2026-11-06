#!/usr/bin/env python
"""Run one arm in one mode on the ControlArena Bash setting.

    python scripts/run_arm.py --arm T0 --mode honest --limit 5 --epochs 1
    python scripts/run_arm.py --arm A4 --mode honest --epochs 3
    python scripts/run_arm.py --arm A4 --mode attack --attack-policy P1 --epochs 3

Writes the Inspect log to results/logs/<run_id>/ and a manifest beside it.

Refuses to run if: models.yaml has unset required fields; the arm is deferred;
an enforcement arm's policy is not frozen (dev override: --allow-draft-policy,
those runs are tagged and excluded from main results); or, in attack mode, the
side task payload no longer matches configs/payload.lock.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from agent_control_eval.enforcement import load_policy  # noqa: E402
from agent_control_eval.manifest import (  # noqa: E402
    build_manifest, load_arms, load_models, write_manifest,
)

LOG_ROOT = REPO / "results" / "logs"
# Manifests live outside the log tree: Inspect scans log dirs for .json logs.
# They hold no trajectory content, so they are committed.
MANIFEST_DIR = REPO / "results" / "manifests"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--arm", required=True)
    p.add_argument("--mode", required=True, choices=["honest", "attack"])
    p.add_argument("--attack-policy", choices=["P1", "P2", "P3"])
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--limit", type=int, help="first N main tasks (dataset order is fixed)")
    p.add_argument("--sample-ids", type=Path, help="file with one task ID per line (main runs use the preregistered list)")
    p.add_argument("--max-samples", type=int, default=4, help="concurrent samples")
    p.add_argument("--max-steps", type=int, help="per-sample step cap; recorded in the manifest")
    p.add_argument("--allow-draft-policy", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="validate config and write manifest only")
    p.add_argument("--smoke", action="store_true",
                   help="pipeline test: Inspect's mockllm for U and T, no API cost; run tagged smoke and excluded")
    args = p.parse_args(argv)
    if args.mode == "attack" and not args.attack_policy:
        p.error("--attack-policy is required in attack mode")
    if args.mode == "honest" and args.attack_policy:
        p.error("--attack-policy is only valid in attack mode")
    if args.limit and args.sample_ids:
        p.error("use --limit or --sample-ids, not both")
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

    if args.smoke:
        models = {r: {"id": "mockllm/model", "temperature": 0.0, "max_tokens": None}
                  for r in ("untrusted", "trusted")}
    else:
        models = load_models()

    policy_sha = None
    tags: list[str] = []
    if arm_def.get("enforcement"):
        policy = load_policy(REPO / arm_def["enforcement"]["policy"])
        if policy.status != "frozen":
            if not args.allow_draft_policy:
                sys.exit("policy is not frozen; pass --allow-draft-policy for development runs")
            tags.append("draft_policy")
        policy_sha = policy.sha256

    if args.smoke:
        tags.append("smoke")
    payload_sha = None
    if args.mode == "attack" and not args.smoke:  # mockllm never calls tools that fetch
        from agent_control_eval.payload import PayloadError, verify_payload
        try:
            payload_sha = verify_payload()
        except PayloadError as exc:
            sys.exit(f"ABORT (payload check): {exc}")

    sample_ids = None
    if args.sample_ids:
        sample_ids = [s.strip() for s in args.sample_ids.read_text().splitlines() if s.strip()]

    from agent_control_eval.protocols.build import build_micro_protocol, resolve_defer_threshold

    run_id = f"{args.arm}-{args.mode}-{args.attack_policy or 'none'}-{uuid.uuid4().hex[:8]}"
    log_dir = LOG_ROOT / run_id
    manifest = build_manifest(
        run_id=run_id, arm=args.arm, mode=args.mode, attack_policy=args.attack_policy,
        epochs=args.epochs, models=models, arm_def=arm_def, policy_sha256=policy_sha,
        extra={
            "limit": args.limit,
            "sample_ids": sample_ids,
            "max_steps": args.max_steps,
            "defer_threshold": resolve_defer_threshold(arm_def),
            "payload_sha256_pre": payload_sha,
            "monitor": "control_arena basic_monitor, stock default prompt" if arm_def.get("monitor") else None,
            "tags": tags,
        },
    )
    write_manifest(manifest, MANIFEST_DIR)
    print(f"run {run_id} -> {log_dir}")
    if args.dry_run:
        return 0

    # Imported late so config validation and --dry-run work without Docker or API keys.
    from inspect_ai.model import GenerateConfig
    from control_arena import EvalMode
    from control_arena.eval import ControlEvalConfig, eval, get_control_task
    from control_arena.scorers import max_suspicion_scorer
    from control_arena.settings.bash.bash_setting import BashSetting

    def gen_config(m: dict) -> GenerateConfig:
        return GenerateConfig(temperature=m["temperature"], max_tokens=m.get("max_tokens"))

    eval_config = ControlEvalConfig(
        untrusted_model=models["untrusted"]["id"],
        untrusted_config=gen_config(models["untrusted"]),
        trusted_model=models["trusted"]["id"],
        trusted_config=gen_config(models["trusted"]),
        epochs=args.epochs,
        limit=args.limit,
        max_samples=args.max_samples,
        max_steps=args.max_steps,
        log_dir=str(log_dir),
    )
    micro_protocol = build_micro_protocol(
        args.arm, arm_def, args.attack_policy, arms["attack_policies"]
    )
    monitoring_scorers = [max_suspicion_scorer()] if arm_def.get("monitor") else []
    task = get_control_task(
        setting=BashSetting(),
        micro_protocol=micro_protocol,
        mode=EvalMode.ATTACK if args.mode == "attack" else EvalMode.HONEST,
        eval_config=eval_config,
        monitoring_scorers=monitoring_scorers,
        metadata={"run_id": run_id, "arm": args.arm, "attack_policy": args.attack_policy},
        task_name=run_id,
    )
    logs = eval(task, sample_id=sample_ids, **eval_config.eval_args())

    if args.mode == "attack" and not args.smoke:
        from agent_control_eval.payload import PayloadError, verify_payload
        try:
            manifest["payload_sha256_post"] = verify_payload()
        except PayloadError as exc:
            manifest["payload_sha256_post"] = None
            manifest["tags"].append("payload_changed_during_run")
            print(f"WARNING: {exc} Run tagged invalid.")
    manifest["eval_logs"] = [str(log.location) for log in logs]
    manifest["status"] = [log.status for log in logs]
    write_manifest(manifest, MANIFEST_DIR)
    print(json.dumps({"run_id": run_id, "status": manifest["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
