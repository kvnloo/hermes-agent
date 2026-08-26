"""Provider-neutral contracts and Hermes-owned realtime voice coordination."""

from __future__ import annotations

import abc
import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast


@dataclass(frozen=True)
class VoiceSessionConfig:
    """Hermes-owned identity and provider-neutral session preferences."""

    session_id: str
    voice: str | None = None
    instructions: str | None = None


@dataclass(frozen=True)
class VoiceEvent:
    event_id: str
    epoch: int


@dataclass(frozen=True)
class Transcript(VoiceEvent):
    item_id: str
    text: str
    final: bool


@dataclass(frozen=True)
class AssistantGenerated(VoiceEvent):
    turn_id: str
    text: str


@dataclass(frozen=True)
class AssistantHeard(VoiceEvent):
    turn_id: str
    text: str
    interrupted: bool


@dataclass(frozen=True)
class AssistantFinal(VoiceEvent):
    turn_id: str
    text: str


@dataclass(frozen=True)
class ToolCall(VoiceEvent):
    call_id: str
    name: str
    arguments: Mapping[str, Any]
    group_id: str
    group_complete: bool


class RealtimeVoiceSession(abc.ABC):
    """One provider transport session; it never executes Hermes actions."""

    @abc.abstractmethod
    def events(self) -> AsyncIterator[VoiceEvent]:
        """Yield provider-neutral events in transport order."""

    @abc.abstractmethod
    async def send_audio(self, audio: bytes) -> None:
        """Send captured audio bytes to the provider."""

    @abc.abstractmethod
    async def send_text(self, text: str) -> None:
        """Send a finalized transcript from a text-owned surface."""

    @abc.abstractmethod
    async def send_tool_result(
        self, call_id: str, output: str, *, approved: bool
    ) -> None:
        """Return a result produced by the injected Hermes dispatcher."""

    @abc.abstractmethod
    async def continue_response(self) -> None:
        """Request one continuation after a complete tool group settles."""

    @abc.abstractmethod
    async def cancel(self, epoch: int) -> None:
        """Cancel provider work superseded by the new Hermes epoch."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Close transport resources idempotently."""


class RealtimeVoiceProvider(abc.ABC):
    """Factory for provider-owned audio transport and turn-taking sessions."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Stable registry identifier."""

    def is_available(self) -> bool:
        return True

    @abc.abstractmethod
    async def open_session(self, config: VoiceSessionConfig) -> RealtimeVoiceSession:
        """Open a session without acquiring Hermes tool or history authority."""


ToolDispatcher = Callable[[ToolCall], Awaitable[tuple[bool, str]] | tuple[bool, str]]


class RealtimeVoiceCoordinator:
    """Hermes-owned ordering, dedupe, cancellation, and tool-result bridge."""

    def __init__(
        self,
        *,
        provider_name: str,
        session_config: VoiceSessionConfig,
        dispatch_tool: ToolDispatcher,
        legacy_fallback: Callable[[], Any] | None = None,
        queue_size: int = 64,
        scope: str | None = None,
    ):
        if queue_size < 1:
            raise ValueError("queue_size must be positive")
        self.provider_name = provider_name
        self.session_config = session_config
        self.dispatch_tool = dispatch_tool
        self.legacy_fallback = legacy_fallback
        self.scope = scope
        self.session: RealtimeVoiceSession | None = None
        self.epoch = 0
        self.queue: asyncio.Queue[VoiceEvent] = asyncio.Queue(maxsize=queue_size)
        self.transcripts: dict[str, str] = {}
        self.generated_responses: dict[str, str] = {}
        self.heard_responses: dict[str, str] = {}
        self.final_responses: dict[str, str] = {}
        self._event_ids: set[str] = set()
        self._tool_call_ids: set[str] = set()
        self._tool_groups: dict[str, set[str]] = {}
        self._complete_groups: set[str] = set()
        self._continued_groups: set[str] = set()
        self._lock = asyncio.Lock()

    @classmethod
    def for_test(
        cls,
        *,
        session: RealtimeVoiceSession | None = None,
        dispatch_tool: ToolDispatcher | None = None,
        queue_size: int = 64,
    ) -> "RealtimeVoiceCoordinator":
        coordinator = cls(
            provider_name="test",
            session_config=VoiceSessionConfig(session_id="test"),
            dispatch_tool=dispatch_tool or (lambda call: (True, "")),
            queue_size=queue_size,
        )
        coordinator.session = session
        return coordinator

    async def start(self) -> Any:
        from agent.realtime_voice_registry import get_provider

        provider = get_provider(self.provider_name, scope=self.scope)
        if provider is None or not provider.is_available():
            if self.legacy_fallback is None:
                return None
            result = self.legacy_fallback()
            return await result if inspect.isawaitable(result) else result
        self.session = await provider.open_session(self.session_config)
        return self.session

    async def send_text(self, text: str) -> None:
        if self.session is None:
            raise RuntimeError("realtime voice session is not started")
        await self.session.send_text(text)

    async def close(self) -> None:
        if self.session is not None:
            await self.session.close()

    async def run_events(self) -> None:
        """Consume one transport stream with bounded admission."""
        if self.session is None:
            raise RuntimeError("realtime voice session is not started")
        async for event in self.session.events():
            await self.queue.put(event)
            queued = await self.queue.get()
            try:
                await self.accept(queued)
            finally:
                self.queue.task_done()

    async def cancel(self) -> int:
        self.epoch += 1
        if self.session is not None:
            await self.session.cancel(self.epoch)
        return self.epoch

    def submit_nowait(self, event: VoiceEvent) -> None:
        self.queue.put_nowait(event)

    async def accept(self, event: VoiceEvent) -> bool:
        async with self._lock:
            if event.epoch != self.epoch or event.event_id in self._event_ids:
                return False
            if isinstance(event, ToolCall) and event.call_id in self._tool_call_ids:
                self._event_ids.add(event.event_id)
                return False
            self._event_ids.add(event.event_id)
            if isinstance(event, Transcript):
                self.transcripts[event.item_id] = event.text
                return True
            if isinstance(event, AssistantGenerated):
                self.generated_responses[event.turn_id] = event.text
                return True
            if isinstance(event, AssistantHeard):
                self.heard_responses[event.turn_id] = event.text
                return True
            if isinstance(event, AssistantFinal):
                self.final_responses[event.turn_id] = event.text
                return True
            if not isinstance(event, ToolCall):
                return True
            self._tool_call_ids.add(event.call_id)
            group = self._tool_groups.setdefault(event.group_id, set())
            group.add(event.call_id)
            if event.group_complete:
                self._complete_groups.add(event.group_id)

        try:
            result = self.dispatch_tool(event)
            if inspect.isawaitable(result):
                resolved = await result
            else:
                resolved = result
            approved, output = cast(tuple[bool, str], resolved)
        except Exception:
            approved, output = False, "Hermes tool dispatch failed"
        if self.session is None:
            raise RuntimeError("tool event received without an active session")
        await self.session.send_tool_result(event.call_id, output, approved=approved)

        should_continue = False
        async with self._lock:
            self._tool_groups[event.group_id].discard(event.call_id)
            if (
                event.group_id in self._complete_groups
                and not self._tool_groups[event.group_id]
                and event.group_id not in self._continued_groups
            ):
                self._continued_groups.add(event.group_id)
                should_continue = True
        if should_continue:
            await self.session.continue_response()
        return True

    def history_text(self, turn_id: str) -> str | None:
        return self.heard_responses.get(turn_id, self.generated_responses.get(turn_id))


_SECRET_KEYS = frozenset({
    "api_key",
    "authorization",
    "token",
    "access_token",
    "secret",
})
_AUDIO_KEYS = frozenset({"audio", "audio_bytes", "pcm", "payload"})


def redact_voice_audit(value: Any, *, key: str | None = None) -> Any:
    """Return audit-safe event data without credentials or binary audio."""

    normalized = (key or "").lower()
    if normalized in _SECRET_KEYS:
        return "[REDACTED]"
    if normalized in _AUDIO_KEYS and isinstance(value, (bytes, bytearray, memoryview)):
        return "[BINARY REDACTED]"
    if isinstance(value, Mapping):
        return {str(k): redact_voice_audit(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_voice_audit(item) for item in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "[BINARY REDACTED]"
    return value
