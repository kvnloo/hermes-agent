"""Same-turn duplicate-call elimination must keep order-significant input.

A real ``AIAgent`` turn against the scripted loopback provider; only the model and the
cua-driver device are fake. The model emits the same ``computer_use`` key press twice in
one assistant message (Tab, Tab moves focus twice). Both presses must reach the backend,
and each must report its own unverified verdict back to the model; a repeated click on
the same element in the same message is still collapsed. ``computer_use`` is deferred by
default, so on the default config the model reaches it through the ``tool_call`` bridge.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.fakes.fake_llm_provider import MODEL_ID, FakeLLMServer, Text, ToolCall, write_hermes_home

TAB = {"action": "key", "keys": "tab"}
TAB_REORDERED = {"keys": "tab", "action": "key"}
CLICK = {"action": "click", "element": 3}


@pytest.fixture
def cu_backend(monkeypatch):
    """The in-tree recording stub stands in for cua-driver; every approval prompt answers "once"."""
    from tools.computer_use import tool as cu_tool

    cu_tool.reset_backend_for_tests()
    backend = cu_tool._NoopBackend()
    monkeypatch.setattr("tools.computer_use.cua_backend_driver.cua_driver_binary_available", lambda: True)
    monkeypatch.setattr(cu_tool, "_new_backend", lambda permission_mode: backend)
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    cu_tool.set_approval_callback(lambda command, description, **kw: "once")
    yield backend
    cu_tool.set_approval_callback(None)
    cu_tool.reset_backend_for_tests()


def _calls(bridge: bool, *args_list: dict) -> ToolCall:
    name = "tool_call" if bridge else "computer_use"
    wire = [{"calls": [{"name": "computer_use", "arguments": a}]} if bridge else a for a in args_list]
    return ToolCall(name, wire[0], parallel=[(name, a) for a in wire[1:]])


@pytest.mark.parametrize("bridge", [True, False], ids=["tool_call-bridge", "direct"])
def test_repeated_key_press_in_one_turn_is_delivered_twice(bridge, cu_backend):
    from run_agent import AIAgent

    script = [_calls(bridge, TAB, TAB_REORDERED, CLICK, CLICK), Text("done")]
    with FakeLLMServer(script) as srv:
        extra = "" if bridge else "tools:\n  tool_search:\n    enabled: \"off\"\n"
        write_hermes_home(Path(os.environ["HERMES_HOME"]), srv.base_url, extra_config=extra)
        agent = AIAgent(provider="custom", base_url=srv.base_url, api_key="sk-fake-e2e", model=MODEL_ID,
                        quiet_mode=True, skip_context_files=True, skip_memory=True,
                        enabled_toolsets=["computer_use"])
        try:
            agent.run_conversation("press tab twice, then click element 3")
        finally:
            agent.close()
        advertised = {t["function"]["name"] for t in srv.main_requests()[0]["tools"]}
        followup = srv.main_requests()[1]["messages"]

    assert ("tool_call" in advertised) is bridge and ("computer_use" in advertised) is not bridge
    assert [name for name, _ in cu_backend.calls] == ["key", "key", "click"]
    results = [json.loads(m["content"]) for m in followup if m.get("role") == "tool"]
    assert [r["action"] for r in results] == ["key", "key", "click"]
    # Each press reports its own unproven effect; the kept repeat never reads as confirmed.
    assert [r["verdict"]["decision"] for r in results[:2]] == ["verify_fresh_state"] * 2
