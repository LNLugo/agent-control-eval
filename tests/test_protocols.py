import pytest

pytest.importorskip("control_arena")

from agent_control_eval.manifest import load_arms  # noqa: E402
from agent_control_eval.protocols.build import (  # noqa: E402
    STOCK_DEFER_THRESHOLD, build_micro_protocol, resolve_defer_threshold,
)

ARMS = load_arms()


def test_stock_threshold_is_library_default():
    from control_arena.micro_protocol._defer_to_trusted import DEFAULT_DEFER_THRESHOLD
    assert STOCK_DEFER_THRESHOLD == DEFAULT_DEFER_THRESHOLD == 0.5
    assert resolve_defer_threshold(ARMS["arms"]["A4"]) == 0.5


@pytest.mark.parametrize("arm,pol", [("T0", None), ("A0", "P1"), ("A1", "P1"), ("A1", "P2"), ("A4", "P1")])
def test_phase1_arms_build(arm, pol):
    assert build_micro_protocol(arm, ARMS["arms"][arm], pol, ARMS["attack_policies"]) is not None


def test_enforcement_arms_wait_for_pep():
    with pytest.raises(NotImplementedError):
        build_micro_protocol("A2", ARMS["arms"]["A2"], "P1", ARMS["attack_policies"])


def test_p2_prompt_keeps_template_fields():
    from pathlib import Path
    from agent_control_eval.protocols.build import REPO
    text = (REPO / ARMS["attack_policies"]["P2"]["prompt"]).read_text()
    assert "{side_task_description}" in text and "{setting_description}" in text
    text.format(main_task_description="m", side_task_description="s", setting_description="d")
