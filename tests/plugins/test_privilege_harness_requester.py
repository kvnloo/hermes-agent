import importlib.util
import json
from pathlib import Path

import pytest


PLUGIN = Path(__file__).parents[2] / "plugins" / "hermes-privilege-harness"
spec = importlib.util.spec_from_file_location("privilege_requester", PLUGIN / "guard.py")
assert spec is not None
requester = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(requester)


def test_request_payload_contains_only_typed_request_and_correlation():
    payload = requester.build_request(
        operation_id="service.restart",
        slots={"unit": "alpha"},
        reason="recover service",
        profile="default",
        session="session-1",
    )

    assert payload == {
        "type": "request",
        "operation_id": "service.restart",
        "slots": {"unit": "alpha"},
        "reason": "recover service",
        "profile": "default",
        "session": "session-1",
    }
    encoded = json.dumps(payload)
    for forbidden in ("command", "shell", "argv", "cwd", "env", "approval", "operator"):
        assert forbidden not in encoded


def test_requester_rejects_untyped_slots_and_process_control_fields():
    with pytest.raises(ValueError):
        requester.build_request("service.restart", {"unit": ["alpha"]}, "why", "p", "s")
    with pytest.raises(TypeError):
        requester.build_request("service.restart", {"unit": "alpha"}, "why", "p", "s", argv=["id"])
