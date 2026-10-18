"""Revision-bound live plan intents, ownership and execution policy (#575)."""
import threading
from types import SimpleNamespace

import pytest


@pytest.fixture
def plans(tmp_path, monkeypatch):
    from tui_gateway import server
    from tui_gateway.plan_review import begin_plan_generation, finish_plan_generation

    transport = SimpleNamespace(write=lambda frame: True)
    agent = SimpleNamespace()
    session = {"session_key": "plan-owner", "transport": transport, "profile_home": tmp_path,
               "agent": agent, "history_lock": threading.Lock(), "history_version": 0}
    monkeypatch.setattr(server, "_sessions", {"owned": session})
    monkeypatch.setattr(server, "_session_uses_compute_host", lambda session: False)

    def call(method, via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": method,
                                          "params": {"session_id": "owned", **params}})
        finally:
            server.reset_transport(token)

    def generate(text="# Build\nCode\n## Test\nTests", status="complete"):
        begin_plan_generation(session, agent)
        session["history_version"] += 1
        finish_plan_generation(session, text, status)
        return call("plan.status")["result"]["plan"]

    return call, session, agent, generate, server


def target(plan):
    return {"plan_id": plan["id"], "revision": plan["revision"]}


def test_markdown_is_not_authority_and_mode_is_explicit(plans):
    call, session, agent, generate, _ = plans
    session["history"] = [{"role": "assistant", "content": "# Ordinary answer"}]
    assert call("plan.status")["result"] == {"enabled": False, "generating": False, "plan": None}
    assert generate() is None
    assert call("plan.mode", enabled=True)["result"]["enabled"]
    assert agent._plan_mode
    assert generate("A plan without headings")["text"] == "A plan without headings"


def test_annotations_and_edits_create_new_immutable_revisions(plans):
    call, _, _, generate, _ = plans
    call("plan.mode", enabled=True)
    first = generate()
    second = call("plan.annotate", **target(first), section=1, text="Add rollback")['result']['plan']
    assert second["id"] == first["id"] and second["revision"] == first["revision"] + 1
    assert first["annotations"] == []
    assert second["annotations"] == [{"section": 1, "text": "Add rollback"}]
    assert "error" in call("plan.decide", **target(first), intent="approve")
    edited = call("plan.edit", **target(second), text="# New\nRevised")['result']['plan']
    assert edited["revision"] == second["revision"] + 1
    assert edited["annotations"] == []
    assert "error" in call("plan.annotate", **target(edited), section=9, text="wrong")


def test_exact_revision_approval_is_once_and_does_not_execute(plans, monkeypatch):
    call, _, agent, generate, server = plans
    submitted = []
    monkeypatch.setitem(server._methods, "prompt.submit", lambda *args: submitted.append(args))
    call("plan.mode", enabled=True)
    plan = generate()
    result = call("plan.decide", **target(plan), intent="approve")['result']
    assert result["plan"]["decision"] == "approved"
    assert not result["enabled"] and not agent._plan_mode
    assert not submitted
    assert "error" in call("plan.decide", **target(plan), intent="approve")


def test_refine_round_trip_carries_exact_plan_and_notes(plans, monkeypatch):
    call, session, _, generate, server = plans
    submitted = []
    monkeypatch.setitem(server._methods, "prompt.submit", lambda rid, params: submitted.append(params) or {"result": {"status": "streaming"}})
    call("plan.mode", enabled=True)
    plan = generate()
    plan = call("plan.annotate", **target(plan), section=1, text="Failure test")['result']['plan']
    assert call("plan.decide", **target(plan), intent="refine", feedback="Smaller change")['result']['enabled']
    assert plan["text"] in submitted[0]["text"]
    assert f"revision {plan['revision']}" in submitted[0]["text"]
    assert "Section 2: Failure test" in submitted[0]["text"]
    assert "error" in call("plan.decide", **target(plan), intent="refine", feedback="duplicate")
    revised = generate("# Revised\nDone")
    assert revised["id"] == plan["id"] and revised["revision"] > plan["revision"]


@pytest.mark.parametrize("status,text", [("interrupted", "# Partial"), ("error", "# Failed"), ("complete", "  ")])
def test_interrupted_failed_or_empty_generation_revokes_previous_plan(plans, status, text):
    call, _, _, generate, _ = plans
    call("plan.mode", enabled=True)
    old = generate()
    assert generate(text, status) is None
    assert "error" in call("plan.decide", **target(old), intent="approve")


def test_history_busy_mode_and_foreign_transport_revoke_authority(plans):
    call, session, _, generate, _ = plans
    call("plan.mode", enabled=True)
    plan = generate()
    assert "error" in call("plan.decide", **target(plan), intent="approve", via=SimpleNamespace())
    session["running"] = True
    assert "error" in call("plan.decide", **target(plan), intent="approve")
    assert "error" in call("plan.mode", enabled=False)
    session["running"] = False
    session["history_version"] += 1
    assert call("plan.status")["result"]["plan"] is None
    assert "error" in call("plan.edit", **target(plan), text="stale")


@pytest.mark.parametrize("method,params", [("plan.mode", {"enabled": "false"}), ("plan.edit", {"plan_id": "p", "revision": True, "text": "x"}), ("plan.decide", {"plan_id": "p", "revision": 1, "intent": "execute"})])
def test_invalid_intents_are_rejected_at_dispatch_boundary(plans, method, params):
    call, _, _, _, _ = plans
    assert "error" in call(method, **params)


def test_next_turn_receives_exact_approved_bytes_without_system_prompt_mutation(plans):
    from tui_gateway.plan_review import begin_plan_generation, plan_turn_note
    call, session, agent, generate, _ = plans
    call("plan.mode", enabled=True)
    plan = generate()
    edited = call("plan.edit", **target(plan), text="# Approved edit\nExact bytes")['result']['plan']
    call("plan.decide", **target(edited), intent="approve")
    agent._cached_system_prompt = "unchanged"
    begin_plan_generation(session, agent)
    note = plan_turn_note(session)
    assert edited["text"] in note and f"revision {edited['revision']}" in note
    assert agent._cached_system_prompt == "unchanged"
    assert not agent._plan_mode
    assert plan_turn_note(session) == ""


def test_plan_policy_blocks_real_executor_dispatch_without_changing_tool_schemas(monkeypatch):
    from agent.tool_executor import _ManagedToolResult, _ToolCallRef, _dispatch_authorized_once
    from agent.agent_runtime_helpers import invoke_tool

    agent = SimpleNamespace(_plan_mode=True, session_id="plan-test")
    executed = []
    monkeypatch.setattr(_ToolCallRef, "emit_post", lambda *args, **kwargs: None)
    state = _ManagedToolResult(None, {}, [], False, False)
    ref = _ToolCallRef("terminal", {"command": "touch forbidden"}, "task", "call", [])
    result = _dispatch_authorized_once(agent, state, ref, execute=lambda args: executed.append(args),
                                      scope_block=None, display_index=None, begin_execution=None, authorization_gate=None)
    assert "Plan mode is active" in result and state.blocked and not executed
    assert "Plan mode is active" in invoke_tool(agent, "delegate_task", {}, "task", pre_tool_block_checked=True)
    from agent.plan_mode import plan_tool_block
    assert plan_tool_block(agent, "read_file") is None
    assert plan_tool_block(agent, "tool_call")
    agent._plan_mode = False
    assert plan_tool_block(agent, "terminal") is None
