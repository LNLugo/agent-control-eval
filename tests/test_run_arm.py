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


def test_refuses_unset_models(tmp_path):
    from agent_control_eval.manifest import ConfigError, load_models
    f = tmp_path / "models.yaml"
    f.write_text("untrusted: {id: a/b, temperature: 1.0}\ntrusted: {id: null, temperature: 1.0}\n")
    with pytest.raises(ConfigError):
        load_models(f)


def test_repo_models_are_fully_set():
    from agent_control_eval.manifest import load_models
    models = load_models()
    assert models["trusted"]["id"].split("/")[0] != models["untrusted"]["id"].split("/")[0]


def test_deferred_arm_rejected():
    with pytest.raises(SystemExit):
        run_arm.main(["--arm", "A5", "--mode", "honest", "--dry-run"])


def test_unsupported_temperature_allowed_only_when_marked(tmp_path):
    from agent_control_eval.manifest import ConfigError, load_models
    ok = tmp_path / "ok.yaml"
    ok.write_text("untrusted: {id: a/b, temperature: null, temperature_unsupported: true}\n"
                  "trusted: {id: c/d, temperature: 1.0}\n")
    assert load_models(ok)["untrusted"]["temperature"] is None
    bad = tmp_path / "bad.yaml"
    bad.write_text("untrusted: {id: a/b, temperature: null}\ntrusted: {id: c/d, temperature: 1.0}\n")
    with pytest.raises(ConfigError):
        load_models(bad)
