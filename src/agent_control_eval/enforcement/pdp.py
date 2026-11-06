"""Policy decision point (PDP).

Pure function of (command, episode state, policy) -> Decision. No model calls,
no I/O, so it can be assured as an IT control by configuration review and unit
tests (safety case, "Is an agent a model?").

Rule matchers are implemented in step 4. Until then the PDP refuses to run, so
no arm can silently execute with an empty policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .decision_log import Decision
from .policy import Policy


@dataclass
class EpisodeState:
    """State the PDP tracks across one episode (needed for EXEC-001)."""

    workdir: str
    downloaded_paths: set[str] = field(default_factory=set)


class PolicyDecisionPoint:
    def __init__(self, policy: Policy):
        self.policy = policy

    def decide(self, command: str, state: EpisodeState) -> Decision:
        raise NotImplementedError(
            "Rule matchers are built in step 4 (configs/policy/v1.0.yaml)."
        )
