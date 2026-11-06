import pytest

from agent_control_eval.stats import (
    cluster_bootstrap_ci, normalized_usefulness, paired_diff_bootstrap_ci,
)


def test_ci_brackets_point_estimate():
    data = {f"t{i}": [i % 2, (i + 1) % 2, i % 2] for i in range(40)}
    est, lo, hi = cluster_bootstrap_ci(data, n_boot=2000)
    assert lo <= est <= hi


def test_paired_diff_zero_for_identical_arms():
    data = {f"t{i}": [i % 3 == 0] * 3 for i in range(30)}
    est, lo, hi = paired_diff_bootstrap_ci(data, data, n_boot=1000)
    assert est == lo == hi == 0


def test_paired_requires_same_tasks():
    with pytest.raises(ValueError):
        paired_diff_bootstrap_ci({"a": [1]}, {"b": [1]})


def test_usefulness_normalization():
    assert normalized_usefulness(0.5, 0.2, 0.8) == pytest.approx(0.5)
