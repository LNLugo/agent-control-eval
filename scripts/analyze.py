#!/usr/bin/env python
"""Aggregate metrics with task-level bootstrap 95% CIs.

    python scripts/analyze.py
    python scripts/analyze.py --logs results/logs --out results/summaries

Prints and writes ONLY aggregates (rates, safety, variance). It never prints
messages, tool calls or monitor reasoning, so it is safe to run on attack logs
before the policy freeze.

Outputs (results/summaries/):
  metrics.json         per arm x mode x attack policy: rates, safety, usefulness, CIs
  task_variance.csv    per arm x mode: between-task vs within-task variance (sample size input)
Runs tagged draft_policy or payload_changed_during_run are excluded unless --include-tagged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from agent_control_eval.stats import cluster_bootstrap_ci  # noqa: E402

EXCLUDE_TAGS = {"draft_policy", "payload_changed_during_run", "smoke"}
TASK_COL_CANDIDATES = ("id", "sample_id")


def load_runs(manifest_dir: Path, include_tagged: bool) -> list[dict]:
    runs = []
    for f in sorted(manifest_dir.glob("*.manifest.json")):
        m = json.loads(f.read_text())
        if not m.get("eval_logs"):
            continue  # dry run or crashed before eval
        if not include_tagged and EXCLUDE_TAGS & set(m.get("tags", [])):
            continue
        runs.append(m)
    return runs


def load_samples(runs: list[dict], log_root: Path) -> pd.DataFrame:
    from control_arena.analysis import samples_df

    frames = []
    for m in runs:
        df = samples_df(str(log_root / m["run_id"]))
        df["arm"] = m["arm"]
        df["mode"] = m["mode"]
        df["attack_policy"] = m.get("attack_policy") or "none"
        df["run_id"] = m["run_id"]
        frames.append(df)
    if not frames:
        raise SystemExit("no completed runs found")
    df = pd.concat(frames, ignore_index=True)
    task_col = next(c for c in TASK_COL_CANDIDATES if c in df.columns)
    df["task"] = df[task_col].astype(str)
    return df


def per_task(df: pd.DataFrame, col: str) -> dict[str, list[float]]:
    sub = df.dropna(subset=[col])
    return {t: g[col].astype(float).tolist() for t, g in sub.groupby("task")}


def rate(df: pd.DataFrame, col: str, n_boot: int) -> dict | None:
    data = per_task(df, col)
    if not data:
        return None
    est, lo, hi = cluster_bootstrap_ci(data, n_boot=n_boot)
    return {"estimate": est, "ci95": [lo, hi], "n_tasks": len(data),
            "n_samples": int(sum(len(v) for v in data.values()))}


def safety_with_ci(honest: pd.DataFrame, attack: pd.DataFrame, budget: float,
                   n_boot: int, seed: int = 0) -> dict:
    """ControlArena compute_safety, with a task-level bootstrap over honest and attack tasks."""
    from control_arena.analysis import compute_safety

    scorer = "max_suspicion_scorer"
    both = pd.concat([honest, attack], ignore_index=True)
    point = float(compute_safety(both, scorer, budget))
    rng = np.random.default_rng(seed)
    h_tasks, a_tasks = honest["task"].unique(), attack["task"].unique()
    h_groups = {t: g for t, g in honest.groupby("task")}
    a_groups = {t: g for t, g in attack.groupby("task")}
    boots = []
    for _ in range(n_boot):
        h = pd.concat([h_groups[t] for t in rng.choice(h_tasks, len(h_tasks))])
        a = pd.concat([a_groups[t] for t in rng.choice(a_tasks, len(a_tasks))])
        try:
            boots.append(float(compute_safety(pd.concat([h, a], ignore_index=True), scorer, budget)))
        except (ValueError, ZeroDivisionError):
            continue
    lo, hi = (np.quantile(boots, [0.025, 0.975]).tolist() if boots else [None, None])
    return {"estimate": point, "ci95": [lo, hi], "audit_budget_pct": budget,
            "n_honest_trajectories": len(honest), "n_attack_trajectories": len(attack),
            "bootstrap_valid": len(boots)}


def variance_table(df: pd.DataFrame) -> pd.DataFrame:
    """Between-task and within-task variance of main and side task success."""
    rows = []
    for (arm, mode, pol), g in df.groupby(["arm", "mode", "attack_policy"]):
        for col in ("main_task_success", "side_task_success"):
            sub = g.dropna(subset=[col])
            if sub.empty:
                continue
            y = sub[col].astype(float)
            task_means = sub.groupby("task")[col].mean().astype(float)
            within = sub.groupby("task")[col].var(ddof=1).astype(float).mean()
            between = task_means.var(ddof=1)
            k = sub.groupby("task").size().mean()
            icc = between / (between + within) if (between + within) > 0 else np.nan
            rows.append({
                "arm": arm, "mode": mode, "attack_policy": pol, "metric": col,
                "n_tasks": task_means.size, "epochs_mean": k, "mean": y.mean(),
                "var_between_tasks": between, "var_within_task": within, "icc": icc,
                "design_effect": 1 + (k - 1) * icc if not np.isnan(icc) else np.nan,
            })
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--logs", type=Path, default=REPO / "results" / "logs")
    p.add_argument("--manifests", type=Path, default=REPO / "results" / "manifests")
    p.add_argument("--out", type=Path, default=REPO / "results" / "summaries")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--include-tagged", action="store_true")
    args = p.parse_args(argv)

    import yaml
    budgets = yaml.safe_load((REPO / "configs" / "arms.yaml").read_text())["audit_budgets"]

    runs = load_runs(args.manifests, args.include_tagged)
    df = load_samples(runs, args.logs)
    out: dict = {"runs": [r["run_id"] for r in runs], "groups": {}}

    for (arm, mode, pol), g in df.groupby(["arm", "mode", "attack_policy"]):
        key = f"{arm}/{mode}/{pol}"
        entry = {"main_task_success": rate(g, "main_task_success", args.n_boot)}
        if mode == "attack":
            entry["side_task_success"] = rate(g, "side_task_success", args.n_boot)
        out["groups"][key] = entry

    # Usefulness scaled: T0 honest = 0, A0 honest = 1.
    def honest_main(arm):
        g = df[(df.arm == arm) & (df["mode"] == "honest")]
        return g["main_task_success"].astype(float).mean() if len(g) else None

    floor, ceil = honest_main("T0"), honest_main("A0")
    out["usefulness_baselines"] = {"trusted_only_T0": floor, "untrusted_only_A0": ceil}
    if floor is not None and ceil is not None and ceil > floor:
        for arm in sorted(df.arm.unique()):
            raw = honest_main(arm)
            if raw is not None:
                out["groups"].setdefault(f"{arm}/honest/none", {})["usefulness_scaled"] = (raw - floor) / (ceil - floor)

    # Safety for monitored arms: needs honest and attack runs of the same arm.
    for arm in sorted(df.arm.unique()):
        honest = df[(df.arm == arm) & (df["mode"] == "honest")]
        if honest.empty or "score_max_suspicion_scorer" not in df.columns:
            continue
        if honest["score_max_suspicion_scorer"].isna().all():
            continue
        for pol in sorted(df[(df.arm == arm) & (df["mode"] == "attack")].attack_policy.unique()):
            attack = df[(df.arm == arm) & (df["mode"] == "attack") & (df.attack_policy == pol)]
            out["groups"][f"{arm}/attack/{pol}"]["safety"] = [
                safety_with_ci(honest, attack, b, args.n_boot) for b in budgets
            ]

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "metrics.json").write_text(json.dumps(out, indent=2, default=float))
    var = variance_table(df)
    var.to_csv(args.out / "task_variance.csv", index=False)
    print(json.dumps(out["groups"], indent=2, default=float))
    print(var.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
