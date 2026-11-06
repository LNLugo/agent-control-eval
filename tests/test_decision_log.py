from agent_control_eval.enforcement import DecisionLog, DecisionRecord


def _rec(step, allowed, rule):
    return DecisionRecord(
        run_id="r", arm="A2", mode="honest", sample_id="s1", epoch=0, step=step,
        command="ls", allowed=allowed, rule_id=rule, reason="", policy_version="1.0",
        policy_sha256="0" * 64,
    )


def test_log_is_append_only(tmp_path):
    log = DecisionLog(tmp_path / "d.jsonl")
    log.append(_rec(0, True, "DEFAULT_ALLOW"))
    log.append(_rec(1, False, "NET-001"))
    rows = log.read()
    assert [r["step"] for r in rows] == [0, 1]
    assert rows[1]["rule_id"] == "NET-001"
