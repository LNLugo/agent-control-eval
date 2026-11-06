"""Once configs/policy/FROZEN.lock exists, the frozen policy bytes may never change."""

from pathlib import Path

import pytest

from agent_control_eval.enforcement import load_policy

POLICY_DIR = Path(__file__).resolve().parents[1] / "configs" / "policy"
LOCK = POLICY_DIR / "FROZEN.lock"


@pytest.mark.skipif(not LOCK.exists(), reason="policy not frozen yet")
def test_frozen_policies_unchanged():
    for line in LOCK.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        sha, name = line.split()
        policy = load_policy(POLICY_DIR / name)
        assert policy.status == "frozen", name
        assert policy.sha256 == sha, f"{name} changed after freeze; create a new version instead"
