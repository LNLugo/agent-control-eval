import json

import pytest

from agent_control_eval.payload import PayloadError, sha256, verify_payload


def _lock(tmp_path, data=b"inert"):
    p = tmp_path / "payload.lock"
    p.write_text(json.dumps({"url": "https://example.invalid/x", "sha256": sha256(data)}))
    return p


def test_matching_payload_passes(tmp_path):
    assert verify_payload(_lock(tmp_path), fetch=lambda url: b"inert") == sha256(b"inert")


def test_changed_payload_aborts(tmp_path):
    with pytest.raises(PayloadError, match="changed"):
        verify_payload(_lock(tmp_path), fetch=lambda url: b"something else")


def test_missing_lock_aborts(tmp_path):
    with pytest.raises(PayloadError, match="not found"):
        verify_payload(tmp_path / "nope.lock", fetch=lambda url: b"")


def test_fetch_failure_aborts(tmp_path):
    def boom(url):
        raise OSError("offline")
    with pytest.raises(PayloadError, match="could not fetch"):
        verify_payload(_lock(tmp_path), fetch=boom)
