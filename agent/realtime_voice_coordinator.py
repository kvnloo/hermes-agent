"""Hermes-owned coordination for provider-neutral realtime voice sessions."""

from __future__ import annotations

import inspect
import math
import threading
import time
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from agent.realtime_voice import (
    ConversationEvent,
    HeardAudioBoundary,
    RealtimeEvent,
    RealtimeEventType,
    RealtimeSession,
    RealtimeVoiceProvider,
)

ToolDispatcher = Callable[[str, dict[str, Any]], str | Awaitable[str]]
TurnRunner = Callable[[Callable[..., None] | None], Any]


class AttachmentSaturated(RuntimeError):
    """An authoritative event could not enter the bounded projection lane."""


class ConversationSession:
    """Hermes-owned canonical identity and event sequencing facade."""

    def __init__(
        self,
        *,
        session_id: str,
        profile_key: str,
        projection_capacity: int = 256,
        max_duration_seconds: float = 300.0,
    ) -> None:
        if not session_id or not profile_key:
            raise ValueError("ConversationSession requires session and profile identity")
        if projection_capacity < 1:
            raise ValueError("projection_capacity must be positive")
        if not 0 < max_duration_seconds <= 300:
            raise ValueError("ConversationSession scope must be at most 300 seconds")
        self.session_id = session_id
        self.profile_key = profile_key
        self._sequence = 0
        self._epoch = 0
        self._turn_id: str | None = None
        self._audio_events: dict[str, ConversationEvent] = {}
        self._heard_audio: dict[str, int] = {}
        self._interruptions: dict[int, ConversationEvent] = {}
        self._tool_results: dict[tuple[str, str], Any] = {}
        self._tool_lock = threading.Lock()
        self._projection_capacity = projection_capacity
        self._projection: deque[ConversationEvent] = deque()
        self._event_log: deque[ConversationEvent] = deque(maxlen=projection_capacity)
        self._presentation_events_dropped = 0
        self._queue_high_water = 0
        self._attachment_generation = 0
        self._deadline = time.monotonic() + max_duration_seconds
        self._closed = False
        self._latencies_ns: dict[str, list[int]] = {}

    def _ensure_active(self) -> None:
        if self._closed or time.monotonic() >= self._deadline:
            self.close()
            raise RuntimeError("ConversationSession is closed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._audio_events.clear()
        self._heard_audio.clear()
        self._projection.clear()
        self._event_log.clear()

    def begin_response(self, turn_id: str) -> int:
        self._ensure_active()
        if not turn_id:
            raise ValueError("A response requires turn identity")
        self._epoch += 1
        self._turn_id = turn_id
        self._audio_events.clear()
        self._heard_audio.clear()
        return self._epoch

    def emit(
        self,
        event_type: str,
        *,
        turn_id: str,
        task_id: str | None = None,
        payload: dict[str, Any] | None = None,
        item_id: str | None = None,
        tool_call_id: str | None = None,
        group_id: str | None = None,
        replayable: bool = True,
        epoch: int | None = None,
        presentation: bool = False,
    ) -> ConversationEvent | None:
        self._ensure_active()
        if not event_type or not turn_id:
            raise ValueError("Conversation events require event_type and turn_id")
        event_epoch = self._epoch if epoch is None else epoch
        if event_epoch != self._epoch:
            raise ValueError("stale epoch")
        self._sequence += 1
        projection_replayable = replayable and presentation
        event = ConversationEvent(
            session_id=self.session_id,
            turn_id=turn_id,
            task_id=task_id,
            sequence=self._sequence,
            epoch=event_epoch,
            event_id=f"{self.session_id}:{self._sequence}",
            event_type=event_type,
            item_id=item_id,
            tool_call_id=tool_call_id,
            group_id=group_id,
            payload=payload or {},
            replayable=projection_replayable,
        )
        if event_type == "assistant.audio.delta" and item_id:
            self._audio_events[event.event_id] = event
        if projection_replayable:
            # This log is projection-only. Its bounded eviction can never discard
            # an approval, tool effect, history mutation, or persistence action.
            self._event_log.append(event)
        if len(self._projection) >= self._projection_capacity:
            if presentation:
                self._presentation_events_dropped += 1
                return None
            raise AttachmentSaturated(
                f"authoritative projection lane is full at {self._projection_capacity} events"
            )
        self._projection.append(event)
        self._queue_high_water = max(self._queue_high_water, len(self._projection))
        return event

    def drain_projection(self) -> list[ConversationEvent]:
        events = list(self._projection)
        self._projection.clear()
        return events

    def metrics(self) -> dict[str, int]:
        return {
            "presentation_events_dropped": self._presentation_events_dropped,
            "queue_high_water": self._queue_high_water,
        }

    def record_latency(
        self, name: str, *, started_ns: int, finished_ns: int
    ) -> None:
        if not name or finished_ns < started_ns:
            raise ValueError("Latency boundaries must be monotonic")
        self._latencies_ns.setdefault(name, []).append(finished_ns - started_ns)

    def latency_snapshot(self) -> dict[str, dict[str, float | int]]:
        report: dict[str, dict[str, float | int]] = {}
        for name, samples in self._latencies_ns.items():
            ordered = sorted(samples)

            def percentile(fraction: float) -> float:
                index = max(0, math.ceil(len(ordered) * fraction) - 1)
                return ordered[index] / 1_000_000

            report[name] = {
                "count": len(ordered),
                "p50_ms": percentile(0.50),
                "p95_ms": percentile(0.95),
                "p99_ms": percentile(0.99),
            }
        return report

    def reattach(
        self, *, profile_key: str, generation: int, last_ack_sequence: int
    ) -> list[ConversationEvent]:
        if profile_key != self.profile_key:
            raise PermissionError("profile does not own this conversation session")
        if generation <= self._attachment_generation:
            raise ValueError("attachment generation must increase")
        if last_ack_sequence < 0 or last_ack_sequence > self._sequence:
            raise ValueError("future acknowledgement is invalid")
        self._attachment_generation = generation
        return [
            event
            for event in self._event_log
            if event.sequence > last_ack_sequence and event.replayable
        ]

    def accept_adapter_event(self, *, profile_key: str, generation: int) -> bool:
        return (
            profile_key == self.profile_key
            and generation == self._attachment_generation
        )

    def report_audio_heard(
        self, event: ConversationEvent, *, audio_sequence: int
    ) -> bool:
        if (
            event.epoch != self._epoch
            or self._audio_events.get(event.event_id) is not event
            or not event.item_id
            or audio_sequence < 0
            or audio_sequence < self._heard_audio.get(event.item_id, -1)
        ):
            return False
        self._heard_audio[event.item_id] = audio_sequence
        return True

    def interrupt(self, turn_id: str, *, epoch: int) -> ConversationEvent:
        if epoch != self._epoch or turn_id != self._turn_id:
            raise ValueError("stale epoch")
        existing = self._interruptions.get(epoch)
        if existing is not None:
            return existing
        heard = max(self._heard_audio.values(), default=None)
        event = self.emit(
            "interruption.cutoff.committed",
            turn_id=turn_id,
            epoch=epoch,
            payload={"heard_audio_sequence": heard},
            replayable=False,
        )
        assert event is not None
        self._interruptions[epoch] = event
        self._audio_events.clear()
        return event

    def dispatch_tool_once(
        self,
        *,
        turn_id: str,
        epoch: int,
        group_id: str,
        tool_call_id: str,
        approved: bool,
        effect: Callable[[], Any],
    ) -> Any:
        """Perform one approved host effect for a stable tool-call group."""
        if epoch != self._epoch or turn_id != self._turn_id:
            raise ValueError("stale epoch")
        if not group_id or not tool_call_id:
            raise ValueError("Tool effects require group and call identity")
        key = (group_id, tool_call_id)
        with self._tool_lock:
            if key in self._tool_results:
                return self._tool_results[key]
            if not approved:
                raise PermissionError("Hermes approval is required before dispatch")
            result = effect()
            self._tool_results[key] = result
            return result


def run_authoritative_turn(
    session: ConversationSession,
    *,
    turn_id: str,
    task_id: str,
    run_turn: TurnRunner,
    stream_callback: Callable[..., None] | None = None,
) -> Any:
    """Observe the existing Hermes turn without becoming its authority funnel."""

    def project(event_type: str, **kwargs: Any) -> None:
        try:
            session.emit(event_type, turn_id=turn_id, task_id=task_id, **kwargs)
        except Exception:
            # Projection is observational. Queue saturation or an adapter-facing
            # validation failure must never replace the authoritative turn result.
            return

    project("turn.accepted")

    def observed_stream(*args: Any, **kwargs: Any) -> None:
        if stream_callback is not None:
            stream_callback(*args, **kwargs)
        text = args[0] if args and isinstance(args[0], str) else None
        if text is not None:
            project(
                "assistant.text.delta",
                payload={"text": text},
                presentation=True,
            )

    try:
        result = run_turn(observed_stream)
    except BaseException:
        project(
            "persistence.terminal",
            payload={"completed": False, "interrupted": False, "failed": True},
            replayable=False,
        )
        raise
    terminal = result if isinstance(result, dict) else {}
    project(
        "persistence.terminal",
        payload={
            "completed": terminal.get("completed") is True,
            "interrupted": terminal.get("interrupted") is True,
            "failed": terminal.get("failed") is True,
        },
        replayable=False,
    )
    return result


class RealtimeVoiceCoordinator:
    """Relay audio while dispatching every tool call through the Hermes host."""

    def __init__(
        self, provider: RealtimeVoiceProvider, *, dispatch_tool: ToolDispatcher
    ) -> None:
        self._provider = provider
        self._dispatch_tool = dispatch_tool
        self._session: RealtimeSession | None = None
        self._current_item_id: str | None = None
        self._current_audio_events: dict[int, RealtimeEvent] = {}
        self._heard_boundary: HeardAudioBoundary | None = None
        self._tool_results: dict[str, str] = {}

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
            or self._current_audio_events.get(id(event)) is not event
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
        if boundary is not None:
            await session.truncate_response(boundary)
        await session.cancel_response()

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        session = self._require_session()
        async for event in session.events():
            if event.type is RealtimeEventType.AUDIO and event.item_id:
                if event.item_id != self._current_item_id:
                    self._current_item_id = event.item_id
                    self._current_audio_events.clear()
                    self._heard_boundary = None
                self._current_audio_events[id(event)] = event
            if event.type is RealtimeEventType.TOOL_CALL:
                await self._dispatch(event, session)
            yield event

    async def _dispatch(
        self, event: RealtimeEvent, session: RealtimeSession
    ) -> None:
        if not event.call_id or not event.tool_name:
            raise ValueError("Realtime tool_call events require call_id and tool_name")
        if event.call_id in self._tool_results:
            await session.submit_tool_result(
                event.call_id, self._tool_results[event.call_id]
            )
            return
        try:
            result = self._dispatch_tool(event.tool_name, dict(event.arguments))
            if inspect.isawaitable(result):
                result = await result
            output = str(result)
        except Exception as exc:
            output = f"Error: {exc}"
        self._tool_results[event.call_id] = output
        await session.submit_tool_result(event.call_id, output)

    async def close(self) -> None:
        session, self._session = self._session, None
        self._reset_output_state()
        if session is not None:
            await session.close()

    def _reset_output_state(self) -> None:
        self._current_item_id = None
        self._current_audio_events.clear()
        self._heard_boundary = None
