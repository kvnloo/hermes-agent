from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import pytest

from agent.realtime_voice import RealtimeEvent, RealtimeEventType
from agent.realtime_voice_coordinator import RealtimeVoiceCoordinator
from tests.agent.test_realtime_voice import FakeProvider, FakeSession


class SlowQueueSession(FakeSession):
    def __init__(self) -> None:
        super().__init__([])
        self._queue: asyncio.Queue[RealtimeEvent | None] = asyncio.Queue()

    async def push(self, event: RealtimeEvent) -> None:
        await self._queue.put(event)

    async def end(self) -> None:
        await self._queue.put(None)

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event


async def _consume(coordinator: RealtimeVoiceCoordinator, observed: list[RealtimeEvent]) -> None:
    async for event in coordinator.events():
        observed.append(event)


@pytest.mark.asyncio
async def test_tool_call_event_is_yielded_before_slow_dispatch_completes():
    session = SlowQueueSession()
    started = asyncio.Event()
    release = asyncio.Event()
    two = asyncio.Event()
    observed: list[RealtimeEvent] = []
    dispatched: list[str] = []

    async def dispatch(name: str, _arguments: dict[str, Any]) -> str:
        dispatched.append(name)
        started.set()
        await release.wait()
        return "ok"

    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])

    async def consume() -> None:
        async for event in coordinator.events():
            observed.append(event)
            if len(observed) >= 2:
                two.set()

    consumer = asyncio.create_task(consume())
    await session.push(RealtimeEvent.tool_call("call-slow", "terminal", {"command": "pwd"}))
    await session.push(RealtimeEvent.audio(b"after-tool"))
    await asyncio.wait_for(two.wait(), timeout=1)
    await asyncio.wait_for(started.wait(), timeout=1)
    assert [event.type for event in observed] == [
        RealtimeEventType.TOOL_CALL,
        RealtimeEventType.AUDIO,
    ]
    assert session.tool_results == []
    release.set()
    await session.end()
    await asyncio.wait_for(consumer, timeout=1)
    await coordinator.close()
    assert session.tool_results == [("call-slow", "ok")]
    assert dispatched == ["terminal"]


@pytest.mark.asyncio
async def test_duplicate_call_id_is_dispatched_exactly_once():
    session = FakeSession(
        [
            RealtimeEvent.tool_call("call-dup", "terminal", {"command": "once"}),
            RealtimeEvent.tool_call("call-dup", "terminal", {"command": "twice"}),
        ]
    )
    dispatched: list[dict[str, Any]] = []

    async def dispatch(_name: str, arguments: dict[str, Any]) -> str:
        dispatched.append(arguments)
        return "ok"

    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])
    events = [event async for event in coordinator.events()]
    await coordinator.close()

    assert len(events) == 2
    assert dispatched == [{"command": "once"}]
    assert session.tool_results == [("call-dup", "ok")]


@pytest.mark.asyncio
async def test_provider_tool_cancellation_suppresses_submit():
    session = SlowQueueSession()
    release = asyncio.Event()
    entered = asyncio.Event()
    two = asyncio.Event()
    observed: list[RealtimeEvent] = []

    async def dispatch(_name: str, _arguments: dict[str, Any]) -> str:
        entered.set()
        await release.wait()
        return "should-not-submit"

    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])

    async def consume() -> None:
        async for event in coordinator.events():
            observed.append(event)
            if len(observed) >= 2:
                two.set()

    consumer = asyncio.create_task(consume())
    await session.push(RealtimeEvent.tool_call("call-x", "browser", {}))
    await asyncio.wait_for(entered.wait(), timeout=1)
    await session.push(RealtimeEvent.tool_call_cancelled("call-x"))
    await asyncio.wait_for(two.wait(), timeout=1)
    release.set()
    await session.end()
    await asyncio.wait_for(consumer, timeout=1)
    await coordinator.close()
    assert session.tool_results == []
    assert [event.type for event in observed] == [
        RealtimeEventType.TOOL_CALL,
        RealtimeEventType.TOOL_CALL_CANCELLED,
    ]


@pytest.mark.asyncio
async def test_cancel_response_cancels_inflight_tool_ledger():
    session = SlowQueueSession()
    entered = asyncio.Event()
    release = asyncio.Event()
    one = asyncio.Event()
    observed: list[RealtimeEvent] = []

    async def dispatch(_name: str, _arguments: dict[str, Any]) -> str:
        entered.set()
        await release.wait()
        return "late"

    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])

    async def consume() -> None:
        async for event in coordinator.events():
            observed.append(event)
            if len(observed) >= 1:
                one.set()

    consumer = asyncio.create_task(consume())
    await session.push(RealtimeEvent.tool_call("call-int", "terminal", {}))
    await asyncio.wait_for(one.wait(), timeout=1)
    await asyncio.wait_for(entered.wait(), timeout=1)
    await coordinator.cancel_response()
    release.set()
    await session.end()
    await asyncio.wait_for(consumer, timeout=1)
    await coordinator.close()
    assert session.tool_results == []
    assert session.cancelled is True


@pytest.mark.asyncio
async def test_dispatch_failure_logs_structured_fields(caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.WARNING)
    session = FakeSession([RealtimeEvent.tool_call("call-log", "browser", {"url": "x"})])

    async def dispatch(_name: str, _arguments: dict[str, Any]) -> str:
        raise RuntimeError("approval denied")

    coordinator = RealtimeVoiceCoordinator(FakeProvider("fake", session), dispatch_tool=dispatch)
    await coordinator.open(instructions="", tools=[])
    [event async for event in coordinator.events()]
    await coordinator.close()

    records = [
        record
        for record in caplog.records
        if record.getMessage() == "Realtime voice tool dispatch failed"
    ]
    assert len(records) == 1
    assert records[0].__dict__["tool_name"] == "browser"
    assert records[0].__dict__["call_id"] == "call-log"
    assert records[0].__dict__["provider"] == "fake"
    assert session.tool_results == [("call-log", "Error: approval denied")]


@pytest.mark.asyncio
async def test_reconnect_rejects_prior_epoch_audio_identity():
    first_output = RealtimeEvent.audio(b"old", item_id="reused-item")
    session = FakeSession([first_output])
    provider = FakeProvider("fake", session)
    coordinator = RealtimeVoiceCoordinator(provider, dispatch_tool=lambda _n, _a: "ok")
    await coordinator.open(instructions="", tools=[])
    [old] = [event async for event in coordinator.events()]
    await coordinator.close()

    reused = RealtimeEvent(
        type=RealtimeEventType.AUDIO,
        audio_bytes=b"new",
        item_id="reused-item",
        emission_id=old.emission_id,
    )
    replacement = FakeSession([reused])
    provider.session = replacement
    await coordinator.open(instructions="", tools=[])
    [new] = [event async for event in coordinator.events()]
    assert coordinator.report_audio_heard(old, audio_end_ms=40) is False
    assert coordinator.report_audio_heard(new, audio_end_ms=40) is True
    await coordinator.close()
