"""Hermes-owned coordination for provider-neutral realtime voice sessions."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from agent.realtime_voice import HeardAudioBoundary, RealtimeEvent, RealtimeEventType, RealtimeSession, RealtimeVoiceProvider

ToolDispatcher = Callable[[str, dict[str, Any]], str | Awaitable[str]]


class RealtimeVoiceMetrics:
    """Redacted stage timestamps (monotonic ns) and counters."""

    def __init__(self, *, surface: str = "", provider: str = "", model: str = "") -> None:
        self.labels = {"surface": surface, "provider": provider, "model": model}
        self.stages: dict[str, int] = {}
        self.counters: dict[str, int] = {}

    def mark(self, stage: str) -> None:
        if stage not in self.stages:
            self.stages[stage] = time.monotonic_ns()

    def inc(self, name: str, n: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + n

    def snapshot(self) -> dict[str, Any]:
        return {"labels": dict(self.labels), "stages": dict(self.stages), "counters": dict(self.counters)}


class RealtimeVoiceCoordinator:
    """Normalize replay/cancellation and route proposals through Hermes."""

    def __init__(self, provider: RealtimeVoiceProvider, *, dispatch_tool: ToolDispatcher,
                 max_audio_bytes: int = 384_000, max_pending_tools: int = 8,
                 surface: str = "", model: str = "") -> None:
        self._provider = provider
        self._dispatch_tool = dispatch_tool
        self._session: RealtimeSession | None = None
        self._epoch = 0
        self._max_audio_bytes = max_audio_bytes
        self._max_pending_tools = max_pending_tools
        self._accepted_audio_bytes = 0
        self._audio_tokens: dict[str, RealtimeEvent] = {}
        self._current_item_id: str | None = None
        self._heard_boundary: HeardAudioBoundary | None = None
        self._seen_events: set[str] = set()
        self._transcripts: dict[tuple[str, str], tuple[int, str, bool]] = {}
        self._final_turns: dict[str, str] = {}
        self._tool_outcomes: dict[str, tuple[str, str]] = {}
        self._tool_tasks: set[asyncio.Task[None]] = set()
        self._tool_groups: dict[tuple[str | None, str | None, int], list[tuple[str, str]]] = {}
        self.metrics = RealtimeVoiceMetrics(surface=surface, provider=provider.name, model=model)

    @property
    def cancellation_epoch(self) -> int:
        return self._epoch

    async def open(self, *, instructions: str, tools: list[dict[str, Any]], voice: str | None = None) -> None:
        if self._session is not None:
            raise RuntimeError("Realtime voice session is already open")
        self._session = await self._provider.open_session(instructions=instructions, tools=tools, voice=voice)
        self._reset_output_state()
        self.metrics.mark("capture_open")

    def _require_session(self) -> RealtimeSession:
        if self._session is None:
            raise RuntimeError("Realtime voice session is not open")
        return self._session

    async def send_audio(self, pcm: bytes) -> None:
        if len(pcm) > self._max_audio_bytes:
            raise BufferError("realtime voice ingress audio exceeds configured bound")
        self.metrics.mark("speech_first_frame")
        await self._require_session().send_audio(pcm)

    def report_audio_heard(self, event: RealtimeEvent, *, audio_end_ms: int) -> bool:
        if (self._session is None or event.type is not RealtimeEventType.AUDIO or
                not event.item_id or self._audio_tokens.get(event.event_id) is not event or
                event.cancellation_epoch != self._epoch or audio_end_ms < 0):
            return False
        if event.audio_end_ms is not None and audio_end_ms > event.audio_end_ms:
            return False
        previous = self._heard_boundary
        if previous and (previous.item_id != event.item_id or audio_end_ms < previous.audio_end_ms):
            return False
        self._heard_boundary = HeardAudioBoundary(event.item_id, audio_end_ms, event.response_id, self._epoch)
        self.metrics.mark("playback_first_sample")
        return True

    async def cancel_response(self) -> None:
        session = self._require_session()
        boundary, self._heard_boundary = self._heard_boundary, None
        self._epoch += 1  # local stale rejection precedes provider I/O
        self._audio_tokens.clear()
        self._accepted_audio_bytes = 0
        self.metrics.mark("interruption_detected")
        self.metrics.inc("interrupts")
        if boundary is not None:
            await session.truncate_response(boundary)
        await session.cancel_response()
        self.metrics.mark("provider_cancel_ack")
        self.metrics.mark("local_playback_silent")

    def transcript(self, turn_id: str, *, source: str = "input") -> str | None:
        value = self._transcripts.get((turn_id, source))
        return value[1] if value else None

    def finalized_user_turns(self) -> dict[str, str]:
        return dict(self._final_turns)

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        session = self._require_session()
        async for event in session.events():
            if not event.event_id or event.event_id in self._seen_events:
                self.metrics.inc("deduped_events")
                continue
            self._seen_events.add(event.event_id)
            if event.cancellation_epoch != self._epoch:
                self.metrics.inc("stale_epoch_drops")
                continue
            if event.type is RealtimeEventType.AUDIO:
                size = len(event.audio_bytes or b"")
                if self._accepted_audio_bytes + size > self._max_audio_bytes:
                    raise BufferError("realtime voice playback exceeds configured bound")
                self._accepted_audio_bytes += size
                if event.item_id != self._current_item_id:
                    self._current_item_id = event.item_id
                    self._audio_tokens.clear()
                    self._heard_boundary = None
                self._audio_tokens[event.event_id] = event
                self.metrics.mark("first_audio_received")
            elif event.type in {RealtimeEventType.TRANSCRIPT, RealtimeEventType.INPUT_TRANSCRIPT,
                                RealtimeEventType.OUTPUT_TRANSCRIPT}:
                if not self._reconcile_transcript(event):
                    continue
            elif event.type is RealtimeEventType.TOOL_CALL:
                if len(self._tool_tasks) >= self._max_pending_tools:
                    raise BufferError("realtime voice pending tool bound exceeded")
                self.metrics.mark("tool_group_start")
                self.metrics.inc("tool_dispatch")
                task = asyncio.create_task(self._dispatch(event, session))
                self._tool_tasks.add(task)
                task.add_done_callback(self._tool_tasks.discard)
            yield event
        # Do not block event consumption on approvals/tools, but settle all
        # proposals before a finite provider stream is reported as drained.
        await self.wait_for_tools()

    def _reconcile_transcript(self, event: RealtimeEvent) -> bool:
        turn_id = event.turn_id or "legacy"
        source = "output" if event.type is RealtimeEventType.OUTPUT_TRANSCRIPT else "input"
        key = (turn_id, source)
        previous = self._transcripts.get(key)
        if previous and event.revision < previous[0]:
            self.metrics.inc("coalesced_revisions")
            return False
        if previous and previous[2]:
            return previous[1] == (event.text or "")
        text = event.text or ""
        if event.final and turn_id in self._final_turns:
            return self._final_turns[turn_id] == text
        self._transcripts[key] = (event.revision, text, event.final)
        if not event.final:
            self.metrics.mark("transcript_partial_first")
        if event.final and source == "input":
            self._final_turns[turn_id] = text
            self.metrics.mark("transcript_final")
        return True

    async def _dispatch(self, event: RealtimeEvent, session: RealtimeSession) -> None:
        if not event.call_id or not event.tool_name:
            return
        payload_hash = hashlib.sha256(json.dumps(event.arguments, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        cached = self._tool_outcomes.get(event.call_id)
        if cached:
            if cached[0] != payload_hash:
                output = "Error: call_id payload collision"
                self.metrics.inc("tool_collisions")
            else:
                output = cached[1]
                self.metrics.inc("tool_replays")
        else:
            try:
                result = self._dispatch_tool(event.tool_name, dict(event.arguments))
                if inspect.isawaitable(result):
                    result = await result
                output = str(result)
            except Exception as exc:
                output = f"Error: {exc}"
            self._tool_outcomes[event.call_id] = (payload_hash, output)
        group_key = (event.response_id, event.tool_group_id, event.cancellation_epoch)
        self._tool_groups.setdefault(group_key, []).append((event.call_id, output))

    async def wait_for_tools(self) -> None:
        if self._tool_tasks:
            await asyncio.gather(*tuple(self._tool_tasks))
        session = self._session
        if session is None:
            return
        groups = self._tool_groups
        self._tool_groups = {}
        for (_response_id, _group_id, epoch), results in groups.items():
            if epoch != self._epoch or not results:
                continue
            await session.submit_tool_group(results)
            self.metrics.mark("tool_group_terminal")

    async def close(self) -> None:
        session, self._session = self._session, None
        self._epoch += 1
        await self.wait_for_tools()
        self._reset_output_state()
        if session is not None:
            await session.close()
        self.metrics.mark("turn_complete")

    def _reset_output_state(self) -> None:
        self._audio_tokens.clear()
        self._current_item_id = None
        self._heard_boundary = None
        self._accepted_audio_bytes = 0
