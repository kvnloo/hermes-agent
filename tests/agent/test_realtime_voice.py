from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import pytest

from agent import realtime_voice_coordinator
from agent import realtime_voice_registry
from agent.realtime_voice import (
    HeardAudioBoundary,
    RealtimeEvent,
    RealtimeEventType,
    RealtimeSession,
    RealtimeVoiceProvider,
    SurfaceSessionConfig,
)
from agent.realtime_voice_coordinator import RealtimeVoiceCoordinator


class FakeSession(RealtimeSession):
    def __init__(self, events: list[RealtimeEvent]) -> None:
        self._events = events
        self.audio: list[bytes] = []
        self.tool_results: list[tuple[str, str]] = []
        self.cancelled = False
        self.cancellation_boundaries: list[HeardAudioBoundary | None] = []
        self.cancellation_operations: list[str] = []
        self.closed = False

    async def send_audio(self, pcm: bytes) -> None:
        self.audio.append(pcm)

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        for event in self._events:
            yield event

    async def submit_tool_result(self, call_id: str, output: str) -> None:
        self.tool_results.append((call_id, output))

    async def cancel_response(self) -> None:
        self.cancelled = True
        self.cancellation_operations.append("cancel")

    async def close(self) -> None:
        self.closed = True


class GatedSession(FakeSession):
    def __init__(self, events: list[RealtimeEvent]) -> None:
        super().__init__(events)
        self.release = asyncio.Event()

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        await self.release.wait()
        for event in self._events:
            yield event


class FakeProvider(RealtimeVoiceProvider):
    def __init__(self, name: str, session: FakeSession) -> None:
        self._name = name
        self.session = session
        self.opened_with: dict[str, Any] | None = None

    @property
    def name(self) -> str:
        return self._name

    async def open_session(self, *, instructions, tools, voice=None):
        self.opened_with = {"instructions": instructions, "tools": tools, "voice": voice}
        return self.session


class SurfaceFakeProvider(FakeProvider):
    def __init__(self, name: str, session: FakeSession, config: SurfaceSessionConfig) -> None:
        super().__init__(name, session)
        self.config = config

    async def mint_surface_session(self, *, instructions, tools, voice=None):
        self.opened_with = {"instructions": instructions, "tools": tools, "voice": voice}
        return self.config


class BoundarySession(FakeSession):
    async def truncate_response(self, boundary: HeardAudioBoundary) -> None:
        self.cancellation_boundaries.append(boundary)
        self.cancellation_operations.append("truncate")


class LegacyCancelSession(FakeSession):
    async def cancel_response(self) -> None:
        self.cancelled = True
        self.cancellation_boundaries.append(None)


@pytest.fixture(autouse=True)
def reset_registry():
    realtime_voice_registry._reset_for_tests()
    yield
    realtime_voice_registry._reset_for_tests()


def test_registry_is_profile_scoped_and_accepts_two_providers():
    alpha = FakeProvider("alpha", FakeSession([]))
    beta = FakeProvider("beta", FakeSession([]))
    realtime_voice_registry.register_provider(alpha, scope="home-a")
    realtime_voice_registry.register_provider(beta, scope="home-a")

    assert realtime_voice_registry.get_provider(" ALPHA ", scope="home-a") is alpha
    assert [provider.name for provider in realtime_voice_registry.list_providers(scope="home-a")] == [
        "alpha",
        "beta",
    ]
    assert realtime_voice_registry.get_provider("alpha", scope="home-b") is None


def test_registry_rejects_invalid_provider_and_empty_name():
    with pytest.raises(TypeError, match="RealtimeVoiceProvider"):
        realtime_voice_registry.register_provider(object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        realtime_voice_registry.register_provider(FakeProvider(" ", FakeSession([])))


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["grok-plugin", "second-provider"])
async def test_coordinator_keeps_tool_dispatch_in_hermes(provider_name: str):
    session = FakeSession(
        [
            RealtimeEvent.audio(b"reply-pcm"),
            RealtimeEvent.transcript("hello", final=True),
            RealtimeEvent.tool_call("call-1", "terminal", {"command": "pwd"}),
        ]
    )
    provider = FakeProvider(provider_name, session)
    dispatched: list[tuple[str, dict[str, Any]]] = []

    async def dispatch(name: str, arguments: dict[str, Any]) -> str:
        dispatched.append((name, arguments))
        return "/safe/workspace"

    coordinator = RealtimeVoiceCoordinator(provider, dispatch_tool=dispatch)
    await coordinator.open(instructions="Hermes owns tools", tools=[{"name": "terminal"}], voice="eve")
    await coordinator.send_audio(b"user-pcm")
    observed = [event async for event in coordinator.events()]
    await coordinator.close()

    assert provider.opened_with == {
        "instructions": "Hermes owns tools",
        "tools": [{"name": "terminal"}],
        "voice": "eve",
    }
    assert session.audio == [b"user-pcm"]
    assert dispatched == [("terminal", {"command": "pwd"})]
    assert session.tool_results == [("call-1", "/safe/workspace")]
    assert [event.type for event in observed] == [
        RealtimeEventType.AUDIO,
        RealtimeEventType.TRANSCRIPT,
        RealtimeEventType.TOOL_CALL,
    ]
    assert session.closed is True


@pytest.mark.asyncio
async def test_coordinator_cancels_at_the_latest_heard_output_boundary_once():
    session = BoundarySession([RealtimeEvent.audio(b"reply-pcm", item_id="item-1")])
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", session), dispatch_tool=lambda _name, _args: "ok"
    )
    await coordinator.open(instructions="", tools=[])
    [output] = [event async for event in coordinator.events()]

    assert output.item_id == "item-1"
    assert coordinator.report_audio_heard(output, audio_end_ms=240) is True
    await coordinator.cancel_response()

    assert session.cancellation_boundaries == [
        HeardAudioBoundary(item_id="item-1", audio_end_ms=240)
    ]
    assert session.cancellation_operations == ["truncate", "cancel"]


@pytest.mark.asyncio
async def test_coordinator_rejects_foreign_stale_and_regressing_heard_boundaries():
    first = RealtimeEvent.audio(b"first", item_id="item-1")
    second = RealtimeEvent.audio(b"second", item_id="item-2")
    session = FakeSession([first, second])
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", session), dispatch_tool=lambda _name, _args: "ok"
    )
    await coordinator.open(instructions="", tools=[])
    observed = [event async for event in coordinator.events()]

    assert coordinator.report_audio_heard(first, audio_end_ms=100) is False
    assert coordinator.report_audio_heard(
        RealtimeEvent.audio(b"foreign", item_id="item-2"), audio_end_ms=100
    ) is False
    assert coordinator.report_audio_heard(observed[1], audio_end_ms=100) is True
    assert coordinator.report_audio_heard(observed[1], audio_end_ms=90) is False


@pytest.mark.asyncio
async def test_coordinator_rejects_foreign_event_when_identity_token_is_reused(
    monkeypatch: pytest.MonkeyPatch,
):
    emitted = RealtimeEvent.audio(b"emitted", item_id="item-1")
    foreign = RealtimeEvent.audio(b"foreign", item_id="item-1")
    monkeypatch.setattr(realtime_voice_coordinator, "id", lambda _event: 7, raising=False)
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", FakeSession([emitted])),
        dispatch_tool=lambda _name, _args: "ok",
    )
    await coordinator.open(instructions="", tools=[])
    [observed] = [event async for event in coordinator.events()]

    assert coordinator.report_audio_heard(observed, audio_end_ms=100) is True
    assert coordinator.report_audio_heard(foreign, audio_end_ms=120) is False


@pytest.mark.asyncio
async def test_zero_heard_and_legacy_cancel_remain_compatible_across_reconnect():
    old_output = RealtimeEvent.audio(b"old", item_id="reused-item")
    session = LegacyCancelSession([old_output])
    provider = FakeProvider("legacy", session)
    coordinator = RealtimeVoiceCoordinator(
        provider, dispatch_tool=lambda _name, _args: "ok"
    )
    await coordinator.open(instructions="", tools=[])
    [observed_old] = [event async for event in coordinator.events()]
    await coordinator.close()

    replacement = LegacyCancelSession([])
    provider.session = replacement
    await coordinator.open(instructions="", tools=[])
    assert coordinator.report_audio_heard(observed_old, audio_end_ms=0) is False
    await coordinator.cancel_response()

    assert replacement.cancellation_boundaries == [None]


@pytest.mark.asyncio
async def test_zero_heard_boundary_truncates_to_start_before_cancel():
    session = BoundarySession([RealtimeEvent.audio(b"reply", item_id="item-zero")])
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", session), dispatch_tool=lambda _name, _args: "ok"
    )
    await coordinator.open(instructions="", tools=[])
    [output] = [event async for event in coordinator.events()]
    assert coordinator.report_audio_heard(output, audio_end_ms=0) is True

    await coordinator.cancel_response()

    assert session.cancellation_boundaries == [HeardAudioBoundary("item-zero", 0)]
    assert session.cancellation_operations == ["truncate", "cancel"]


@pytest.mark.asyncio
async def test_coordinator_returns_dispatch_failures_to_provider_without_losing_session():
    session = FakeSession([RealtimeEvent.tool_call("call-2", "browser", {})])

    async def dispatch(_name: str, _arguments: dict[str, Any]) -> str:
        raise RuntimeError("approval denied")

    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])
    events = [event async for event in coordinator.events()]

    assert len(events) == 1
    assert session.tool_results == [("call-2", "Error: approval denied")]


@pytest.mark.asyncio
async def test_coordinator_requires_open_session_and_closes_idempotently():
    session = FakeSession([])
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", session), dispatch_tool=lambda _name, _args: "ok"
    )

    with pytest.raises(RuntimeError, match="not open"):
        await coordinator.send_audio(b"pcm")
    await coordinator.close()
    await coordinator.open(instructions="", tools=[])
    await coordinator.close()
    await coordinator.close()
    assert session.closed is True


@pytest.mark.asyncio
async def test_surface_hosted_topology_returns_only_scoped_expiring_config():
    config = SurfaceSessionConfig(
        provider="surface-fake",
        session_id="session-1",
        endpoint="wss://voice.invalid/session",
        session_token="minted-short-lived-token",
        expires_at=time.time() + 60,
        scopes=frozenset({"audio.send", "events.receive"}),
    )
    provider = SurfaceFakeProvider("surface-fake", FakeSession([]), config)
    coordinator = RealtimeVoiceCoordinator(provider, dispatch_tool=lambda _n, _a: "ok")

    minted = await coordinator.mint_surface_session(
        instructions="Hermes owns approvals", tools=[{"name": "terminal"}]
    )

    assert minted is config
    assert set(vars(minted)) == {
        "provider", "session_id", "endpoint", "session_token", "expires_at", "scopes"
    }
    assert not ({"approve", "approval", "tools.execute", "provider.secret"} & minted.scopes)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("expires_at", "scopes", "message"),
    [
        (0, frozenset({"audio.send"}), "expired"),
        (time.time() + 60, frozenset({"approval"}), "forbidden scope"),
        (float("inf"), frozenset({"audio.send"}), "lifetime exceeds"),
    ],
)
async def test_surface_hosted_topology_rejects_expired_or_authoritative_config(
    expires_at: float, scopes: frozenset[str], message: str
):
    config = SurfaceSessionConfig(
        provider="fake",
        session_id="s",
        endpoint="wss://voice.invalid",
        session_token="ephemeral",
        expires_at=expires_at,
        scopes=scopes,
    )
    coordinator = RealtimeVoiceCoordinator(
        SurfaceFakeProvider("fake", FakeSession([]), config),
        dispatch_tool=lambda _n, _a: "ok",
    )
    with pytest.raises(ValueError, match=message):
        await coordinator.mint_surface_session(instructions="", tools=[])


@pytest.mark.asyncio
async def test_duplicate_tool_call_group_dispatches_exactly_once_per_connection():
    duplicate = RealtimeEvent.tool_call("group-1", "terminal", {"command": "pwd"})
    session = FakeSession([duplicate, duplicate])
    dispatched: list[str] = []
    coordinator = RealtimeVoiceCoordinator(
        FakeProvider("fake", session),
        dispatch_tool=lambda name, _args: dispatched.append(name) or "ok",
    )
    await coordinator.open(instructions="", tools=[])

    observed = [event async for event in coordinator.events()]

    assert observed == [duplicate]
    assert dispatched == ["terminal"]
    assert session.tool_results == [("group-1", "ok")]


@pytest.mark.asyncio
async def test_stale_event_iterator_cannot_dispatch_after_reconnect():
    stale_session = GatedSession([RealtimeEvent.tool_call("old", "terminal", {})])
    provider = FakeProvider("fake", stale_session)
    dispatched: list[str] = []
    coordinator = RealtimeVoiceCoordinator(
        provider, dispatch_tool=lambda name, _args: dispatched.append(name) or "ok"
    )
    await coordinator.open(instructions="", tools=[])
    stale_event = asyncio.ensure_future(anext(coordinator.events()))
    await asyncio.sleep(0)
    await coordinator.close()
    provider.session = FakeSession([])
    await coordinator.open(instructions="", tools=[])
    stale_session.release.set()

    with pytest.raises(StopAsyncIteration):
        await stale_event
    assert dispatched == []
