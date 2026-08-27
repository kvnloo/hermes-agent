"""Provider-neutral contracts for persistent, bidirectional voice sessions.

Providers transport audio and propose calls. Hermes remains authoritative for
tools, approvals, history, identity, cancellation, and replay.
"""

from __future__ import annotations

import abc
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

REALTIME_VOICE_INTERFACE_VERSION = "hermes.realtime_voice.v1"


class RealtimeEventType(str, Enum):
    AUDIO = "audio"
    AUDIO_DONE = "audio_done"
    TRANSCRIPT = "transcript"
    INPUT_TRANSCRIPT = "input_transcript"
    OUTPUT_TRANSCRIPT = "output_transcript"
    TOOL_CALL = "tool_call"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    SESSION_CONNECTED = "session_connected"
    SESSION_DISCONNECTED = "session_disconnected"
    SESSION_RECONNECTED = "session_reconnected"
    RESPONSE_COMPLETED = "response_completed"
    RESPONSE_CANCELLED = "response_cancelled"
    ERROR = "error"


@dataclass(frozen=True)
class HeardAudioBoundary:
    """Playback receipt for one exact response, item, and cancellation epoch."""

    item_id: str
    audio_end_ms: int
    response_id: str | None = None
    cancellation_epoch: int = 0


@dataclass(frozen=True)
class RealtimeEvent:
    """One replay-safe normalized event emitted by a provider adapter."""

    type: RealtimeEventType
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    surface_connection_id: str = ""
    turn_id: str | None = None
    response_id: str | None = None
    provider_session_id: str | None = None
    cancellation_epoch: int = 0
    producer_sequence: int = 0
    occurred_monotonic_ns: int = field(default_factory=time.monotonic_ns)
    audio_bytes: bytes | None = None
    text: str | None = None
    final: bool = False
    revision: int = 0
    call_id: str | None = None
    tool_group_id: str | None = None
    tool_name: str | None = None
    item_id: str | None = None
    audio_start_ms: int | None = None
    audio_end_ms: int | None = None
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def audio(cls, pcm: bytes, *, item_id: str | None = None, **identity: Any) -> "RealtimeEvent":
        return cls(type=RealtimeEventType.AUDIO, audio_bytes=pcm, item_id=item_id, **identity)

    @classmethod
    def transcript(cls, text: str, *, final: bool = False, **identity: Any) -> "RealtimeEvent":
        return cls(type=RealtimeEventType.TRANSCRIPT, text=text, final=final, **identity)

    @classmethod
    def tool_call(cls, call_id: str, name: str, arguments: dict[str, Any], **identity: Any) -> "RealtimeEvent":
        return cls(type=RealtimeEventType.TOOL_CALL, call_id=call_id, tool_name=name,
                   arguments=dict(arguments), **identity)


class RealtimeSession(abc.ABC):
    """An open provider transport; it never dispatches Hermes tools itself."""

    @abc.abstractmethod
    async def send_audio(self, pcm: bytes) -> None: ...

    @abc.abstractmethod
    def events(self) -> AsyncIterator[RealtimeEvent]: ...

    @abc.abstractmethod
    async def submit_tool_result(self, call_id: str, output: str) -> None: ...

    async def truncate_response(self, boundary: HeardAudioBoundary) -> None:
        """Truncate provider history when supported; local rejection is mandatory."""

    @abc.abstractmethod
    async def cancel_response(self) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...


class RealtimeVoiceProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @property
    def display_name(self) -> str:
        return self.name.title()

    def is_available(self) -> bool:
        return True

    def get_setup_schema(self) -> dict[str, Any]:
        return {"name": self.display_name, "badge": "", "tag": "", "env_vars": []}

    @abc.abstractmethod
    async def open_session(self, *, instructions: str, tools: list[dict[str, Any]],
                           voice: str | None = None) -> RealtimeSession: ...