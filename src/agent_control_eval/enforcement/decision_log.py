"""Append-only decision log: one JSON line per PDP evaluation.

Every proposed command gets exactly one record (safety case E2.3), whether it is
allowed or denied. Records carry the rule ID, the policy version and hash, and
the sample/epoch identifiers needed to join them back to the Inspect log.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

DEFAULT_ALLOW = "DEFAULT_ALLOW"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    rule_id: str                 # matching rule, or DEFAULT_ALLOW
    reason: str = ""


@dataclass
class DecisionRecord:
    run_id: str
    arm: str
    mode: Literal["honest", "attack"]
    sample_id: str
    epoch: int
    step: int
    command: str
    allowed: bool
    rule_id: str
    reason: str
    policy_version: str
    policy_sha256: str
    ts: float = field(default_factory=time.time)


class DecisionLog:
    """Writes records with O_APPEND semantics; never rewrites or truncates."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: DecisionRecord) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), sort_keys=True) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
