"""Tests for the GUI-surface ``focus_pane`` tool."""

import json

import pytest

from tools import desktop_ui, focus_pane_tool as fp


@pytest.fixture(autouse=True)
def _reset_emitter():
    desktop_ui.set_emitter(None)
    yield
    desktop_ui.set_emitter(None)




@pytest.mark.parametrize("pane", [p for p in fp.PANES if p != "terminal"])
def test_emits_pane_reveal(pane):
    calls = []
    desktop_ui.set_emitter(lambda sid, event, payload: calls.append((event, payload)))

    out = json.loads(fp.focus_pane_tool(f"  {pane.upper()}  "))

    assert out == {"success": True, "pane": pane}
    assert calls == [("pane.reveal", {"pane": pane})]

def test_terminal_pane_does_not_claim_to_be_the_agent_shell():
    """#156710: revealing an existing Desktop terminal does not pick the agent host."""
    calls = []
    desktop_ui.set_emitter(lambda sid, event, payload: calls.append((event, payload)))

    result = json.loads(fp.focus_pane_tool("terminal"))

    assert result["success"] is True
    assert result["pane"] == "terminal"
    assert "URL/cloud gateways" in result["host_context"]
    assert "Desktop client" in result["host_context"]
    assert "Verify the terminal host" in result["host_context"]
    assert calls == [("pane.reveal", {"pane": "terminal"})]
