from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect

import pytest

from agent.realtime_voice import ConversationEvent
from agent.realtime_voice_coordinator import (
    AttachmentSaturated,
    ConversationSession,
    run_authoritative_turn,
)
from run_agent import AIAgent


def test_conversation_session_emits_ordered_immutable_copied_events() -> None:
    payload = {"text": "hello", "nested": {"safe": True}}
    session = ConversationSession(session_id="session-1", profile_key="profile-a")

    event = session.emit(
        "assistant.text.delta",
        turn_id="turn-1",
        task_id="task-1",
        payload=payload,
    )
    payload["text"] = "mutated"
    payload["nested"]["safe"] = False
    next_event = session.emit("assistant.text.final", turn_id="turn-1")

    assert isinstance(event, ConversationEvent)
    assert event.sequence == 1
    assert next_event.sequence == 2
    assert event.session_id == "session-1"
    assert event.turn_id == "turn-1"
    assert event.task_id == "task-1"
    assert event.event_id == "session-1:1"
    assert dict(event.payload) == {"text": "hello", "nested": {"safe": True}}
    with pytest.raises((FrozenInstanceError, AttributeError)):
        event.sequence = 9  # type: ignore[misc]
    with pytest.raises(TypeError):
        event.payload["text"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        event.payload["nested"]["safe"] = False  # type: ignore[index]


def test_interruption_accepts_heard_boundary_once_and_rejects_stale_epoch() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")
    epoch = session.begin_response("turn-1")
    audio = session.emit(
        "assistant.audio.delta",
        turn_id="turn-1",
        item_id="audio-1",
        payload={"audio_sequence": 4, "audio_byte_count": 128},
    )

    assert session.report_audio_heard(audio, audio_sequence=4) is True
    interruption = session.interrupt("turn-1", epoch=epoch)
    assert interruption.payload["heard_audio_sequence"] == 4
    assert session.interrupt("turn-1", epoch=epoch) is interruption
    assert session.report_audio_heard(audio, audio_sequence=5) is False

    next_epoch = session.begin_response("turn-1")
    assert next_epoch == epoch + 1
    with pytest.raises(ValueError, match="stale epoch"):
        session.emit("assistant.audio.delta", turn_id="turn-1", epoch=epoch)


def test_tool_effect_group_dispatches_exactly_once_across_retries() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")
    epoch = session.begin_response("turn-1")
    effects: list[str] = []

    first = session.dispatch_tool_once(
        turn_id="turn-1", epoch=epoch, group_id="group-1", tool_call_id="call-1",
        approved=True, effect=lambda: effects.append("ran") or "ok",
    )
    duplicate = session.dispatch_tool_once(
        turn_id="turn-1", epoch=epoch, group_id="group-1", tool_call_id="call-1",
        approved=True, effect=lambda: effects.append("ran-again") or "bad",
    )

    assert first == duplicate == "ok"
    assert effects == ["ran"]
    with pytest.raises(PermissionError, match="approval"):
        session.dispatch_tool_once(
            turn_id="turn-1", epoch=epoch, group_id="group-2", tool_call_id="call-2",
            approved=False, effect=lambda: "must not run",
        )


def test_projection_queue_is_bounded_nonblocking_and_never_silently_drops_authority() -> None:
    session = ConversationSession(
        session_id="session-1", profile_key="profile-a", projection_capacity=2
    )
    session.emit("assistant.text.delta", turn_id="turn-1", presentation=True)
    session.emit("assistant.text.delta", turn_id="turn-1", presentation=True)

    dropped = session.emit(
        "assistant.text.delta", turn_id="turn-1", presentation=True
    )
    assert dropped is None
    assert session.metrics()["presentation_events_dropped"] == 1
    assert session.metrics()["queue_high_water"] == 2

    with pytest.raises(AttachmentSaturated):
        session.emit("approval.requested", turn_id="turn-1")
    assert [event.sequence for event in session.drain_projection()] == [1, 2]


def test_reattach_replays_projection_only_and_suppresses_stale_generation() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")
    first = session.emit("assistant.text.delta", turn_id="turn-1", presentation=True)
    session.emit("tool.started", turn_id="turn-1", replayable=False)
    third = session.emit("assistant.text.final", turn_id="turn-1", presentation=True)

    replay = session.reattach(profile_key="profile-a", generation=2, last_ack_sequence=1)
    assert replay == [third]
    assert first is not None and third is not None
    assert session.accept_adapter_event(profile_key="profile-a", generation=1) is False
    assert session.accept_adapter_event(profile_key="profile-a", generation=2) is True
    with pytest.raises(PermissionError, match="profile"):
        session.reattach(profile_key="profile-b", generation=3, last_ack_sequence=0)
    with pytest.raises(ValueError, match="future acknowledgement"):
        session.reattach(profile_key="profile-a", generation=3, last_ack_sequence=99)


def test_run_conversation_exposes_an_opt_in_conversation_session_facade() -> None:
    parameter = inspect.signature(AIAgent.run_conversation).parameters[
        "conversation_session"
    ]
    assert parameter.default is None


def test_facade_observes_real_turn_without_replacing_result_or_stream_callback() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")
    streamed: list[str] = []
    authoritative_result = {"final_response": "done", "completed": True}

    def run_turn(callback):
        callback("hel")
        callback("hello")
        return authoritative_result

    result = run_authoritative_turn(
        session,
        turn_id="turn-1",
        task_id="task-1",
        run_turn=run_turn,
        stream_callback=streamed.append,
    )

    assert result is authoritative_result
    assert streamed == ["hel", "hello"]
    assert [event.event_type for event in session.drain_projection()] == [
        "turn.accepted",
        "assistant.text.delta",
        "assistant.text.delta",
        "persistence.terminal",
    ]


def test_facade_projects_failed_terminal_and_preserves_authoritative_exception() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")

    def fail_turn(_callback):
        raise RuntimeError("authoritative failure")

    with pytest.raises(RuntimeError, match="authoritative failure"):
        run_authoritative_turn(
            session,
            turn_id="turn-1",
            task_id="task-1",
            run_turn=fail_turn,
        )

    events = session.drain_projection()
    assert [event.event_type for event in events] == ["turn.accepted", "persistence.terminal"]
    assert events[-1].payload["failed"] is True


def test_surface_wire_roundtrip_retains_identity_and_rejects_sensitive_payloads() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")
    event = session.emit(
        "assistant.text.final", turn_id="turn-1", task_id="task-1",
        payload={"text": "safe"},
    )
    assert event is not None

    decoded = ConversationEvent.from_wire(event.to_wire())
    assert decoded == event
    assert decoded is not event
    for forbidden in ("audio_bytes", "provider_secret", "reasoning"):
        with pytest.raises(ValueError, match="sensitive"):
            session.emit(
                "diagnostic.adapter", turn_id="turn-1", payload={forbidden: "nope"}
            )


def test_session_scope_is_bounded_to_five_minutes_and_close_is_idempotent() -> None:
    with pytest.raises(ValueError, match="300 seconds"):
        ConversationSession(
            session_id="session-1", profile_key="profile-a", max_duration_seconds=301
        )
    session = ConversationSession(
        session_id="session-1", profile_key="profile-a", max_duration_seconds=300
    )
    session.close()
    session.close()
    with pytest.raises(RuntimeError, match="closed"):
        session.emit("turn.accepted", turn_id="turn-1")


def test_latency_hooks_report_monotonic_percentiles_and_sample_count() -> None:
    session = ConversationSession(session_id="session-1", profile_key="profile-a")
    session.record_latency("input_to_first_text", started_ns=10, finished_ns=20)
    session.record_latency("input_to_first_text", started_ns=20, finished_ns=50)

    report = session.latency_snapshot()["input_to_first_text"]
    assert report["count"] == 2
    assert report["p50_ms"] <= report["p95_ms"] <= report["p99_ms"]
    with pytest.raises(ValueError, match="monotonic"):
        session.record_latency("bad", started_ns=50, finished_ns=20)

