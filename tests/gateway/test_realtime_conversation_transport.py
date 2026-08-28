from __future__ import annotations

import json

import pytest

from agent.realtime_voice import ConversationEvent
from agent.realtime_voice_coordinator import ConversationSession


class FakeSurfaceTransport:
    """Serialization boundary with no access to Hermes authority methods."""

    def roundtrip(self, event: ConversationEvent) -> ConversationEvent:
        frame = json.loads(json.dumps(event.to_wire()))
        return ConversationEvent.from_wire(frame)


def test_surface_transport_roundtrip_and_projection_only_reconnect() -> None:
    owner_token = object()
    core = ConversationSession(
        session_id="session-1", profile_key="profile-a",
        authenticate_attachment=lambda token: token is owner_token,
    )
    surface = FakeSurfaceTransport()
    projected = core.emit(
        "assistant.text.delta",
        turn_id="turn-1",
        payload={"text": "hello"},
        presentation=True,
    )
    core.emit(
        "tool.finished",
        turn_id="turn-1",
        group_id="group-1",
        tool_call_id="call-1",
        replayable=False,
    )
    assert projected is not None

    decoded = surface.roundtrip(projected)
    assert decoded.event_id == projected.event_id
    assert decoded.sequence == projected.sequence
    assert decoded.epoch == projected.epoch
    assert core.reattach(
        profile_key="profile-a", owner_token=owner_token,
        generation=1, last_ack_sequence=0,
    ) == [projected]


def test_surface_transport_cannot_reattach_across_profile_or_stale_generation() -> None:
    owner_token = object()
    core = ConversationSession(
        session_id="session-1", profile_key="profile-a",
        authenticate_attachment=lambda token: token is owner_token,
    )
    core.reattach(
        profile_key="profile-a", owner_token=owner_token,
        generation=2, last_ack_sequence=0,
    )

    with pytest.raises(PermissionError):
        core.reattach(
            profile_key="profile-b", owner_token=owner_token,
            generation=3, last_ack_sequence=0,
        )
    assert core.accept_adapter_event(profile_key="profile-a", generation=1) is False
