"""Regression for #133514: stale parent cleanup cannot withdraw a later turn's consent."""
from contextlib import nullcontext
from types import SimpleNamespace

import gateway.run
from gateway.run_turn_runner import TurnRunner
from gateway.run_turn_runner_approval_transport import approval_transport
from gateway.turn_context import TurnContext
from tools import approval
from tools.approval_gateway_wait import _ApprovalEntry


def test_delayed_parent_cleanup_keeps_successor_approval(monkeypatch):
    key = "agent:test:handoff"
    predecessor = TurnRunner(None, TurnContext(session_key=key, message="first"))
    successor = TurnRunner(None, TurnContext(session_key=key, message="second"))
    monkeypatch.setattr(predecessor, "_native_image_run_message", lambda: "first")
    monkeypatch.setattr(gateway.run, "_wrap_current_message_with_observed_context",
                        lambda message, group: message)
    monkeypatch.setattr("gateway.session_onboarding.arm_onboarding_turn", lambda *args: None)
    monkeypatch.setattr("agent.notification_presentation.notification_turn",
                        lambda *args, **kwargs: nullcontext())

    entry = _ApprovalEntry({"command": "safe fixture", "description": "review",
                            "pattern_key": "fixture"})
    successor_notifier = approval_transport(successor)

    def predecessor_body(*args, **kwargs):
        # A released admission before its finally; B now owns the chat and
        # has a pending approval when A's stale finally resumes.
        approval.register_gateway_notify(key, successor_notifier)
        with approval._lock:
            approval._gateway_queues.setdefault(key, []).append(entry)
        return {"final_response": "predecessor completed"}

    try:
        predecessor._run_conversation_with_approval(
            SimpleNamespace(run_conversation=predecessor_body), [], None, None, None)
        assert approval._gateway_notify_cb(key) is successor_notifier
        assert approval.has_blocking_approval(key)
        assert not entry.event.is_set()
        assert approval.resolve_gateway_approval(
            key, "once", request_id=entry.data["request_id"]) == 1
        assert entry.result == "once"
        assert entry.event.is_set()
    finally:
        approval.unregister_gateway_notify(key)
        approval.clear_session(key)
