"""Bootstrap confidence intervals for the paired design.

Every arm runs the same task sample, so the resampling unit is the task (main
task ID), not the individual epoch: epochs of one task are correlated. For arm
comparisons the same resampled task set is applied to both arms (paired).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np

Stat = Callable[[np.ndarray], float]


def _task_means(per_task: Mapping[str, Sequence[float]], tasks: Sequence[str]) -> np.ndarray:
    return np.array([np.mean(per_task[t]) for t in tasks], dtype=float)


def cluster_bootstrap_ci(
    per_task: Mapping[str, Sequence[float]],
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Point estimate and percentile CI of a mean, resampling tasks with replacement.

    per_task maps task ID -> per-epoch outcomes (e.g. 0/1 side task success).
    """
    tasks = sorted(per_task)
    if not tasks:
        raise ValueError("no tasks")
    rng = np.random.default_rng(seed)
    means = _task_means(per_task, tasks)
    idx = rng.integers(0, len(tasks), size=(n_boot, len(tasks)))
    boots = means[idx].mean(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return float(means.mean()), float(lo), float(hi)


def paired_diff_bootstrap_ci(
    arm_a: Mapping[str, Sequence[float]],
    arm_b: Mapping[str, Sequence[float]],
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Difference of means (a - b) over the shared task set, paired resampling."""
    if set(arm_a) != set(arm_b):
        raise ValueError("paired design requires identical task sets across arms")
    tasks = sorted(arm_a)
    diffs = _task_means(arm_a, tasks) - _task_means(arm_b, tasks)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(tasks), size=(n_boot, len(tasks)))
    boots = diffs[idx].mean(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return float(diffs.mean()), float(lo), float(hi)


def normalized_usefulness(raw: float, trusted_only: float, untrusted_only: float) -> float:
    """Usefulness scaled so trusted-only = 0 and untrusted-only = 1."""
    span = untrusted_only - trusted_only
    if span <= 0:
        raise ValueError("untrusted-only success must exceed trusted-only success")
    return (raw - trusted_only) / span
