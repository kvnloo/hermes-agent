"""Discord duplex consumer: barge-in, fallback, transcript durability, pause gate."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.realtime_voice import RealtimeEvent
from agent.realtime_voice_coordinator import RealtimeVoiceCoordinator
from plugins.platforms.discord.realtime_consumer import (
    DiscordDuplexConsumer,
    classify_overlap,
    is_discord_duplex_enabled,
    load_discord_duplex_config,
)
from tests.agent.test_realtime_voice import FakeProvider, FakeSession


def test_discord_duplex_defaults_off_and_does_not_touch_voice_chat_mode():
    cfg = load_discord_duplex_config({"voice": {"voice_chat_mode": "chained"}})
    assert cfg["enabled"] is False
    assert cfg["provider"] == "openai"
    assert cfg["model"] == "gpt-realtime-2.1"
    assert is_discord_duplex_enabled({"voice": {}}) is False
    assert is_discord_duplex_enabled({"voice": {"discord_duplex": {"enabled": True}}}) is True


def test_admission_echo_backchannel_takeover():
    loud = b"\x00\x30" * 2000
    quiet = b"\x02\x00" * 200
    assert classify_overlap(quiet, playing=True, echo_window=True, duration_ms=80) == "echo"
    assert classify_overlap(loud, playing=True, echo_window=False, duration_ms=80) == "backchannel"
    assert classify_overlap(loud, playing=True, echo_window=False, duration_ms=400, rms=5000) == "takeover"
    assert classify_overlap(loud, playing=False, echo_window=False, duration_ms=400, rms=5000) == "speech"


@pytest.mark.asyncio
async def test_local_barge_in_stops_mixer_before_provider_cancel():
    order: list[str] = []
    mixer = MagicMock()
    mixer.played_through_ms = 80
    mixer.stop_speech.side_effect = lambda: order.append("stop")
    mixer.reset_playback_cursor.side_effect = lambda: order.append("reset")

    class OrderSession(FakeSession):
        async def truncate_response(self, boundary) -> None:
            order.append(f"truncate:{boundary.audio_end_ms}")

        async def cancel_response(self) -> None:
            order.append("cancel")

    session = OrderSession([RealtimeEvent.audio(b"pcm", item_id="item-1")])
    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=lambda *_: "ok")
    await coordinator.open(instructions="", tools=[])
    observed = [event async for event in coordinator.events()]

    async def fallback(**kwargs):
        return None

    consumer = DiscordDuplexConsumer(coordinator=coordinator, mixer=mixer, fallback=fallback)
    consumer._clock.event = observed[0]
    await consumer.local_barge_in()
    assert order[0] == "stop"
    assert "cancel" in order
    assert order.index("stop") < order.index("cancel")


@pytest.mark.asyncio
async def test_unauthorized_capture_is_not_a_turn_and_deny_has_zero_side_effects():
    executed = []

    def dispatch(_n, _a):
        executed.append("ran")
        raise RuntimeError("approval denied")

    session = FakeSession([RealtimeEvent.tool_call("c1", "terminal", {"command": "pwd"})])
    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])
    fallbacks = []

    async def fallback(**kwargs):
        fallbacks.append(kwargs)

    consumer = DiscordDuplexConsumer(coordinator=coordinator, mixer=None, fallback=fallback)
    kind = await consumer.ingest_capture(
        b"\x00\x30" * 400, playing=False, echo_window=False, duration_ms=400,
        user_id=1, guild_id=1, authorized=False,
    )
    assert kind == "unauthorized"
    assert fallbacks == []
    [event async for event in coordinator.events()]
    assert executed == ["ran"]
    assert session.tool_results[0][1].startswith("Error: approval denied")


@pytest.mark.asyncio
async def test_fallback_on_overflow_does_not_duplicate_finalized_turn():
    session = FakeSession([])
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", session), dispatch_tool=lambda *_: "ok", max_audio_bytes=16
    )
    await coordinator.open(instructions="", tools=[])
    fallbacks = []

    async def fallback(**kwargs):
        fallbacks.append(kwargs.get("reason"))

    consumer = DiscordDuplexConsumer(
        coordinator=coordinator, mixer=None, fallback=fallback, max_ingress_seconds=0.0,
    )
    consumer.finalized_turns["t1"] = "hello"
    pcm = b"\x00\x10" * 400
    kind = await consumer.ingest_capture(
        pcm, playing=False, echo_window=False, duration_ms=400,
        user_id=9, guild_id=1, authorized=True,
    )
    assert kind == "overflow"
    assert consumer.degraded is True
    assert fallbacks == ["ingress_overflow"]
    # already-finalized user turn is not re-submitted by fallback path in consumer
    assert consumer.finalized_turns == {"t1": "hello"}


def test_pause_gate_false_until_degraded():
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", FakeSession([])), dispatch_tool=lambda *_: "ok"
    )
    consumer = DiscordDuplexConsumer(coordinator=coordinator, mixer=None, fallback=lambda **k: None)
    assert consumer.should_pause_receiver() is False
    consumer.mark_degraded("test")
    assert consumer.should_pause_receiver() is True
    assert consumer.degrade_reason == "test"


def test_adapter_pause_gate_respects_opt_in(monkeypatch):
    from plugins.platforms.discord.adapter import DiscordAdapter

    adapter = object.__new__(DiscordAdapter)
    adapter._duplex_consumers = {}
    monkeypatch.setattr(
        "plugins.platforms.discord.realtime_consumer.is_discord_duplex_enabled",
        lambda config=None: True,
    )
    assert adapter._should_pause_voice_receiver(1) is False
    monkeypatch.setattr(
        "plugins.platforms.discord.realtime_consumer.is_discord_duplex_enabled",
        lambda config=None: False,
    )
    assert adapter._should_pause_voice_receiver(1) is True
