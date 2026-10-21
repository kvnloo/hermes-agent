"""Queue aliases must manage accepted prompts, not become model input or quit."""
from collections import deque
import threading

import pytest

from tui_gateway import server


@pytest.fixture
def queued_session(monkeypatch):
    session = {
        "session_key": "queue-parity", "running": False, "history": [],
        "history_lock": threading.Lock(), "agent": None, "cwd": "",
        "queued_prompt": {"text": "first"},
        "queued_prompts": deque([{"text": "second"}]),
    }
    monkeypatch.setitem(server._sessions, "queue-parity", session)
    return session


def execute(command):
    response = server._methods["slash.exec"](1, {
        "session_id": "queue-parity", "command": command,
    })
    assert "error" not in response, response
    return response["result"]


@pytest.mark.parametrize("alias", ["queue", "q", "Q"])
def test_queue_alias_lists_real_accepted_prompts(queued_session, alias):
    result = execute(f"/{alias} list")
    assert result["type"] == "exec"
    assert result["output"] == "Queued prompts:\n  1. first\n  2. second"
    assert execute(f"/{alias} add next prompt") == {"type": "send", "message": "next prompt"}
    assert queued_session["queued_prompt"]["text"] == "first"


def test_queue_management_mutates_the_accepted_order(queued_session):
    execute("/q move 2 1")
    assert execute("/q list")["output"] == "Queued prompts:\n  1. second\n  2. first"
    execute("/q rm 1")
    assert execute("/q list")["output"] == "Queued prompts:\n  1. first"
    execute("/q clear")
    assert execute("/q list")["output"] == "No queued prompts."
