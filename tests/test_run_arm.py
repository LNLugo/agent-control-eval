import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_arm.py"
spec = importlib.util.spec_from_file_location("run_arm", SCRIPT)
run_arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_arm)


def test_attack_mode_requires_policy():
    with pytest.raises(SystemExit):
        run_arm.parse_args(["--arm", "A1", "--mode", "attack"])


def test_refuses_unset_models():
    # models.yaml ships with null IDs; the runner must not start.
    from agent_control_eval.manifest import ConfigError
    with pytest.raises(ConfigError):
        run_arm.main(["--arm", "A0", "--mode", "honest", "--dry-run"])


def test_deferred_arm_rejected():
    with pytest.raises(SystemExit):
        run_arm.main(["--arm", "A5", "--mode", "honest", "--dry-run"])
