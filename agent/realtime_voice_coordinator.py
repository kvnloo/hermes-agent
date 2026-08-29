"""Hermes-owned coordination for provider-neutral realtime voice sessions."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from enum import Enum
from typing import Any
from uuid import UUID

from agent.realtime_voice import (
    HeardAudioBoundary,
    RealtimeEvent,
    RealtimeEventType,
    RealtimeSession,
    RealtimeVoiceProvider,
)

ToolDispatcher = Callable[[str, dict[str, Any]], str | Awaitable[str]]
logger = logging.getLogger(__name__)

MAX_INFLIGHT_TOOL_DISPATCHES = 8


class _CallState(str, Enum):
    PENDING = "pending"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class RealtimeVoiceCoordinator:
    """Relay audio while dispatching every tool call through the Hermes host."""

    def __init__(
        self, provider: RealtimeVoiceProvider, *, dispatch_tool: ToolDispatcher
    ) -> None:
        self._provider = provider
        self._dispatch_tool = dispatch_tool
        self._session: RealtimeSession | None = None
        self._current_item_id: str | None = None
        self._current_audio_events: dict[UUID, RealtimeEvent] = {}
        self._heard_boundary: HeardAudioBoundary | None = None
        self._epoch = 0
        self._ledger: dict[str, _CallState] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._sema = asyncio.Semaphore(MAX_INFLIGHT_TOOL_DISPATCHES)
        self._lock = asyncio.Lock()

    async def open(
        self,
        *,
        instructions: str,
        tools: list[dict[str, Any]],
        voice: str | None = None,
    ) -> None:
        if self._session is not None:
            raise RuntimeError("Realtime voice session is already open")
        self._session = await self._provider.open_session(
            instructions=instructions, tools=tools, voice=voice
        )
        self._reset_output_state()

    def _require_session(self) -> RealtimeSession:
        if self._session is None:
            raise RuntimeError("Realtime voice session is not open")
        return self._session

    async def send_audio(self, pcm: bytes) -> None:
        await self._require_session().send_audio(pcm)

    def report_audio_heard(self, event: RealtimeEvent, *, audio_end_ms: int) -> bool:
        """Record playback progress only for audio emitted by this open epoch."""
        if (
            self._session is None
            or event.type is not RealtimeEventType.AUDIO
            or not event.item_id
            or event.item_id != self._current_item_id
            or self._current_audio_events.get(event.emission_id) is not event
            or audio_end_ms < 0
        ):
            return False
        boundary = HeardAudioBoundary(event.item_id, audio_end_ms)
        if self._heard_boundary and audio_end_ms < self._heard_boundary.audio_end_ms:
            return False
        self._heard_boundary = boundary
        return True

    async def cancel_response(self) -> None:
        session = self._require_session()
        boundary, self._heard_boundary = self._heard_boundary, None
        async with self._lock:
            for call_id, state in list(self._ledger.items()):
                if state is _CallState.PENDING:
                    self._ledger[call_id] = _CallState.CANCELLED
        if boundary is not None:
            await session.truncate_response(boundary)
        await session.cancel_response()

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        session = self._require_session()
        epoch = self._epoch
        try:
            async for event in session.events():
                if event.type is RealtimeEventType.AUDIO and event.item_id:
                    if event.item_id != self._current_item_id:
                        self._current_item_id = event.item_id
                        self._current_audio_events.clear()
                        self._heard_boundary = None
                    self._current_audio_events[event.emission_id] = event
                if event.type is RealtimeEventType.TOOL_CALL:
                    self._spawn_dispatch(event, session, epoch)
                elif event.type is RealtimeEventType.TOOL_CALL_CANCELLED:
                    await self._cancel_call(event.call_id)
                yield event
        finally:
            await self._drain_tasks()

    def _spawn_dispatch(
        self, event: RealtimeEvent, session: RealtimeSession, epoch: int
    ) -> None:
        task = asyncio.create_task(self._run_dispatch(event, session, epoch))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run_dispatch(
        self, event: RealtimeEvent, session: RealtimeSession, epoch: int
    ) -> None:
        async with self._sema:
            await self._dispatch(event, session, epoch)

    async def _cancel_call(self, call_id: str | None) -> None:
        if not call_id:
            return
        async with self._lock:
            state = self._ledger.get(call_id)
            if state is _CallState.PENDING or state is None:
                self._ledger[call_id] = _CallState.CANCELLED

    async def _dispatch(
        self, event: RealtimeEvent, session: RealtimeSession, epoch: int
    ) -> None:
        if not event.call_id or not event.tool_name:
            raise ValueError("Realtime tool_call events require call_id and tool_name")
        async with self._lock:
            state = self._ledger.get(event.call_id)
            if state is not None:
                return
            self._ledger[event.call_id] = _CallState.PENDING
        try:
            result = self._dispatch_tool(event.tool_name, dict(event.arguments))
            if inspect.isawaitable(result):
                result = await result
            output = str(result)
        except Exception as exc:
            logger.warning(
                "Realtime voice tool dispatch failed",
                extra={
                    "tool_name": event.tool_name,
                    "call_id": event.call_id,
                    "provider": self._provider.name,
                },
                exc_info=True,
            )
            output = f"Error: {exc}"
        async with self._lock:
            if (
                epoch != self._epoch
                or self._session is not session
                or self._ledger.get(event.call_id) is not _CallState.PENDING
            ):
                if self._ledger.get(event.call_id) is _CallState.PENDING:
                    self._ledger[event.call_id] = _CallState.CANCELLED
                return
            self._ledger[event.call_id] = _CallState.SETTLED
        await session.submit_tool_result(event.call_id, output)

    async def close(self) -> None:
        session, self._session = self._session, None
        async with self._lock:
            for call_id, state in list(self._ledger.items()):
                if state is _CallState.PENDING:
                    self._ledger[call_id] = _CallState.CANCELLED
        await self._drain_tasks()
        self._reset_output_state()
        if session is not None:
            await session.close()

    async def _drain_tasks(self) -> None:
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)

    def _reset_output_state(self) -> None:
        self._epoch += 1
        self._current_item_id = None
        self._current_audio_events.clear()
        self._heard_boundary = None
        self._ledger.clear()
