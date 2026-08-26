from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from agent.realtime_voice import (
    AssistantFinal,
    AssistantGenerated,
    AssistantHeard,
    RealtimeVoiceCoordinator,
    RealtimeVoiceProvider,
    RealtimeVoiceSession,
    ToolCall,
    Transcript,
    VoiceSessionConfig,
    redact_voice_audit,
)
from agent import realtime_voice_registry


class FakeSession(RealtimeVoiceSession):
    def __init__(self, events=()):
        super().__init__()
        self.inbound = asyncio.Queue()
        for event in events:
            self.inbound.put_nowait(event)
        self.sent_text: list[str] = []
        self.tool_results: list[tuple[str, str, bool]] = []
        self.continuations = 0
        self.cancelled: list[int] = []
        self.closed = False

    async def events(self) -> AsyncIterator[Any]:
        while True:
            event = await self.inbound.get()
            if event is None:
                return
            yield event

    async def send_audio(self, audio: bytes) -> None:
        pass

    async def send_text(self, text: str) -> None:
        self.sent_text.append(text)

    async def send_tool_result(
        self, call_id: str, output: str, *, approved: bool
    ) -> None:
        self.tool_results.append((call_id, output, approved))

    async def continue_response(self) -> None:
        self.continuations += 1

    async def cancel(self, epoch: int) -> None:
        self.cancelled.append(epoch)

    async def close(self) -> None:
        self.closed = True


class FakeProvider(RealtimeVoiceProvider):
    def __init__(self, name: str, session: FakeSession, available: bool = True):
        self._name = name
        self.session = session
        self.available = available
        self.opened: list[VoiceSessionConfig] = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self.available

    async def open_session(self, config: VoiceSessionConfig) -> RealtimeVoiceSession:
        self.opened.append(config)
        return self.session


@pytest.fixture(autouse=True)
def reset_registry():
    realtime_voice_registry._reset_for_tests()
    yield
    realtime_voice_registry._reset_for_tests()


def run(coro):
    return asyncio.run(coro)


def test_registry_resolves_scoped_provider_and_rejects_wrong_type():
    first = FakeProvider("alpha", FakeSession())
    second = FakeProvider("beta", FakeSession())
    realtime_voice_registry.register_provider(first)
    realtime_voice_registry.register_provider(second, scope="profile-a")

    assert realtime_voice_registry.get_provider(" ALPHA ") is first
    assert realtime_voice_registry.get_provider("beta", scope="profile-a") is second
    with pytest.raises(TypeError):
        realtime_voice_registry.register_provider(object())


def test_plugin_context_registers_and_unloads_realtime_provider():
    from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest

    manager = PluginManager()
    context = PluginContext(
        PluginManifest(
            name="fixture-realtime",
            version="1.0.0",
            description="fixture",
            source="user",
            key="fixture-realtime",
        ),
        manager,
    )
    provider = FakeProvider("plugin-voice", FakeSession())

    handle = context.register_realtime_voice_provider(provider)

    assert (
        realtime_voice_registry.get_provider("plugin-voice", scope=manager.scope_key)
        is provider
    )
    assert handle is not None
    handle.dispose()
    assert (
        realtime_voice_registry.get_provider("plugin-voice", scope=manager.scope_key)
        is None
    )


def test_two_provider_shapes_share_the_same_contract():
    class TranscriptSurface(FakeProvider):
        pass

    class DuplexAudioSurface(FakeProvider):
        pass

    for provider in (
        TranscriptSurface("text-surface", FakeSession()),
        DuplexAudioSurface("audio-surface", FakeSession()),
    ):
        realtime_voice_registry.register_provider(provider)
        resolved = realtime_voice_registry.resolve_provider(provider.name)
        session = run(resolved.open_session(VoiceSessionConfig(session_id="s1")))
        assert isinstance(session, RealtimeVoiceSession)


def test_unavailable_provider_uses_legacy_fallback_without_opening_session():
    provider = FakeProvider("offline", FakeSession(), available=False)
    realtime_voice_registry.register_provider(provider)
    fallbacks = []
    coordinator = RealtimeVoiceCoordinator(
        provider_name="offline",
        session_config=VoiceSessionConfig(session_id="s1"),
        dispatch_tool=lambda call: None,
        legacy_fallback=lambda: fallbacks.append("legacy") or "legacy-session",
    )

    assert run(coordinator.start()) == "legacy-session"
    assert fallbacks == ["legacy"]
    assert provider.opened == []


def test_session_lifecycle_and_text_transcript_surface():
    session = FakeSession()
    provider = FakeProvider("text", session)
    realtime_voice_registry.register_provider(provider)
    coordinator = RealtimeVoiceCoordinator(
        provider_name="text",
        session_config=VoiceSessionConfig(session_id="s1"),
        dispatch_tool=lambda call: None,
    )

    assert run(coordinator.start()) is session
    run(coordinator.send_text("hello from Web Speech"))
    run(coordinator.close())

    assert session.sent_text == ["hello from Web Speech"]
    assert session.closed is True


def test_coordinator_consumes_session_events_until_transport_closes():
    session = FakeSession([
        Transcript("e1", 0, "u1", "partial", final=False),
        Transcript("e2", 0, "u1", "final transcript", final=True),
        AssistantFinal("e3", 0, "a1", "structured response"),
        None,
    ])
    coordinator = RealtimeVoiceCoordinator.for_test(session=session, queue_size=2)

    run(coordinator.run_events())

    assert coordinator.transcripts == {"u1": "final transcript"}
    assert coordinator.final_responses == {"a1": "structured response"}


def test_cumulative_transcript_replaces_by_item_and_final_event_is_structured():
    coordinator = RealtimeVoiceCoordinator.for_test(queue_size=8)
    run(coordinator.accept(Transcript("e1", 0, "u1", "hel", final=False)))
    run(coordinator.accept(Transcript("e2", 0, "u1", "hello", final=True)))
    run(coordinator.accept(AssistantFinal("e3", 0, "a1", "done")))

    assert coordinator.transcripts == {"u1": "hello"}
    assert coordinator.final_responses["a1"] == "done"


def test_generated_vs_heard_reconciliation_tracks_only_heard_text():
    coordinator = RealtimeVoiceCoordinator.for_test(queue_size=8)
    run(coordinator.accept(AssistantGenerated("g1", 0, "a1", "full generated answer")))
    run(coordinator.accept(AssistantHeard("h1", 0, "a1", "full gen", interrupted=True)))

    assert coordinator.generated_responses["a1"] == "full generated answer"
    assert coordinator.heard_responses["a1"] == "full gen"
    assert coordinator.history_text("a1") == "full gen"


def test_cancel_epoch_rejects_stale_events_and_notifies_provider():
    session = FakeSession()
    coordinator = RealtimeVoiceCoordinator.for_test(session=session, queue_size=8)
    new_epoch = run(coordinator.cancel())

    assert new_epoch == 1
    assert session.cancelled == [1]
    assert (
        run(coordinator.accept(Transcript("old", 0, "u1", "stale", final=True)))
        is False
    )
    assert (
        run(coordinator.accept(Transcript("new", 1, "u1", "fresh", final=True))) is True
    )
    assert coordinator.transcripts == {"u1": "fresh"}


def test_bounded_queue_applies_backpressure_without_silent_drop():
    coordinator = RealtimeVoiceCoordinator.for_test(queue_size=1)
    coordinator.submit_nowait(Transcript("e1", 0, "u1", "one", final=False))
    with pytest.raises(asyncio.QueueFull):
        coordinator.submit_nowait(Transcript("e2", 0, "u1", "two", final=False))


def test_parallel_tool_group_settles_before_exactly_one_continuation():
    session = FakeSession()
    gates = {"c1": asyncio.Event(), "c2": asyncio.Event()}

    async def dispatch(call):
        await gates[call.call_id].wait()
        return (True, f"result:{call.call_id}")

    coordinator = RealtimeVoiceCoordinator.for_test(
        session=session, dispatch_tool=dispatch
    )

    async def scenario():
        task1 = asyncio.create_task(
            coordinator.accept(ToolCall("t1", 0, "c1", "search", {}, "g1", False))
        )
        task2 = asyncio.create_task(
            coordinator.accept(ToolCall("t2", 0, "c2", "read", {}, "g1", True))
        )
        await asyncio.sleep(0)
        gates["c1"].set()
        await asyncio.sleep(0)
        assert session.continuations == 0
        gates["c2"].set()
        await asyncio.gather(task1, task2)

    run(scenario())
    assert sorted(session.tool_results) == [
        ("c1", "result:c1", True),
        ("c2", "result:c2", True),
    ]
    assert session.continuations == 1


def test_tool_results_are_exactly_once_across_reconnect_dedupe_and_denial():
    session = FakeSession()

    async def dispatch(call):
        return (False, "denied by Hermes")

    coordinator = RealtimeVoiceCoordinator.for_test(
        session=session, dispatch_tool=dispatch
    )
    event = ToolCall(
        "event-1", 0, "call-1", "terminal", {"command": "unsafe"}, "g1", True
    )

    assert run(coordinator.accept(event)) is True
    assert run(coordinator.accept(event)) is False
    assert session.tool_results == [("call-1", "denied by Hermes", False)]
    assert session.continuations == 1


def test_dispatcher_failure_returns_bounded_denial_and_settles_group():
    session = FakeSession()

    async def dispatch(call):
        raise RuntimeError("private dispatcher details")

    coordinator = RealtimeVoiceCoordinator.for_test(
        session=session, dispatch_tool=dispatch
    )

    assert (
        run(coordinator.accept(ToolCall("e1", 0, "c1", "terminal", {}, "g1", True)))
        is True
    )
    assert session.tool_results == [("c1", "Hermes tool dispatch failed", False)]
    assert session.continuations == 1


def test_audit_redaction_removes_credentials_and_audio_payloads_recursively():
    audit = redact_voice_audit({
        "api_key": "secret",
        "authorization": "Bearer secret",
        "audio": b"private pcm",
        "nested": {"token": "secret", "safe": "visible"},
    })

    assert audit == {
        "api_key": "[REDACTED]",
        "authorization": "[REDACTED]",
        "audio": "[BINARY REDACTED]",
        "nested": {"token": "[REDACTED]", "safe": "visible"},
    }
