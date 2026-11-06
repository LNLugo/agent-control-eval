from pathlib import Path

import pytest

from agent_control_eval.enforcement import load_policy
from agent_control_eval.enforcement.pdp import EpisodeState, PolicyDecisionPoint

POLICY = Path(__file__).resolve().parents[1] / "configs" / "policy" / "v1.0.yaml"


def test_policy_loads_with_unique_rule_ids_and_hash():
    policy = load_policy(POLICY)
    assert policy.policy_version == "1.0"
    assert len({r.id for r in policy.rules}) == len(policy.rules)
    assert len(policy.sha256) == 64


def test_every_rule_maps_to_a_threat_model_action():
    policy = load_policy(POLICY)
    for rule in policy.rules:
        assert rule.threat, f"{rule.id} has no PA-xx mapping"
        assert all(t.startswith("PA-0") for t in rule.threat)


def test_pdp_refuses_to_run_until_implemented():
    pdp = PolicyDecisionPoint(load_policy(POLICY))
    with pytest.raises(NotImplementedError):
        pdp.decide("ls", EpisodeState(workdir="/tmp"))
