"""Run configuration and manifest.

Every run writes a manifest next to its Inspect log recording exactly what ran:
model IDs and temperatures, package versions, arm and policy definitions with
hashes, and the git commit. The rule from the plan: exact model IDs, versions
and temperatures in every log.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from importlib import metadata
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS = REPO_ROOT / "configs"

REQUIRED_MODEL_FIELDS = ("id", "temperature")


class ConfigError(ValueError):
    pass


def load_models(path: Path = CONFIGS / "models.yaml") -> dict:
    models = yaml.safe_load(path.read_text())
    missing = []
    for role in ("untrusted", "trusted"):
        spec = models.get(role) or {}
        if spec.get("id") is None:
            missing.append(f"{role}.id")
        if spec.get("temperature") is None and not spec.get("temperature_unsupported"):
            missing.append(f"{role}.temperature")
    if missing:
        raise ConfigError(f"configs/models.yaml has unset required fields: {missing}")
    return models


def load_arms(path: Path = CONFIGS / "arms.yaml") -> dict:
    return yaml.safe_load(path.read_text())


def _pkg_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def build_manifest(
    *, run_id: str, arm: str, mode: str, attack_policy: str | None, epochs: int,
    models: dict, arm_def: dict, policy_sha256: str | None = None, extra: dict | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "arm": arm,
        "arm_definition": arm_def,
        "mode": mode,
        "attack_policy": attack_policy,
        "epochs": epochs,
        "models": models,
        "policy_sha256": policy_sha256,
        "packages": {p: _pkg_version(p) for p in ("control-arena", "inspect-ai", "agent-control-eval")},
        "python": platform.python_version(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        **(extra or {}),
    }


def write_manifest(manifest: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{manifest['run_id']}.manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return path
