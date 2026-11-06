"""Policy loading and versioning for the policy decision point.

The policy file is the single source of truth for what the PDP enforces. Its
sha256 is recorded in every decision record and every run manifest, so any
result can be traced to the exact bytes of the policy that produced it.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class Rule(BaseModel):
    id: str
    threat: list[str] = Field(default_factory=list)
    description: str
    match: str


class PolicyContext(BaseModel):
    task_workdir: str | None = None
    egress_allowlist: list[str] = Field(default_factory=list)


class Policy(BaseModel):
    policy_version: str
    status: Literal["draft", "frozen"]
    frozen_at: str | None = None
    default: Literal["allow", "deny"] = "allow"
    context: PolicyContext = Field(default_factory=PolicyContext)
    rules: list[Rule]

    # Set by load_policy, not read from the file.
    sha256: str = ""
    path: str = ""


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_policy(path: str | Path) -> Policy:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    policy = Policy.model_validate(raw)
    ids = [r.id for r in policy.rules]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate rule IDs in {path}: {ids}")
    policy.sha256 = file_sha256(path)
    policy.path = str(path)
    return policy
