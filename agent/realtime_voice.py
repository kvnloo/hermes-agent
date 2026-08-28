"""Provider-neutral contracts for persistent, bidirectional voice sessions.

Realtime providers own audio transport and turn-taking. Hermes remains the
owner of tools, approvals, conversation history, and memory; provider tool
calls are events that a host-side coordinator dispatches through Hermes.
"""

from __future__ import annotations

import abc
import copy
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

_SENSITIVE_EVENT_KEYS = frozenset(
    {"audio_bytes", "raw_audio", "provider_secret", "secret", "token", "password", "reasoning"}
)


class RealtimeEventType(str, Enum):
    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    TOOL_CALL = "tool_call"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    ERROR = "error"


def _immutable_copy(value: Any) -> Any:
    """Defensively copy event data into recursively immutable containers."""
    if isinstance(value, dict):
        return MappingProxyType({key: _immutable_copy(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_immutable_copy(item) for item in value)
    if isinstance(value, set):
        return frozenset(_immutable_copy(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_immutable_copy(item) for item in value)
    return copy.deepcopy(value)


def _wire_copy(value: Any) -> Any:
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _wire_copy(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_wire_copy(item) for item in value]
    return copy.deepcopy(value)


def _reject_sensitive_payload(value: Any) -> None:
    if isinstance(value, dict) or hasattr(value, "items"):
        for key, item in value.items():
            if str(key).lower() in _SENSITIVE_EVENT_KEYS:
                raise ValueError("sensitive data is forbidden in conversation events")
            _reject_sensitive_payload(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _reject_sensitive_payload(item)


@dataclass(frozen=True)
class ConversationEvent:
    """Immutable, provider-neutral event emitted by a conversation session."""

    session_id: str
    turn_id: str
    sequence: int
    epoch: int
    event_id: str
    event_type: str
    monotonic_ns: int = field(default_factory=time.monotonic_ns)
    task_id: str | None = None
    item_id: str | None = None
    tool_call_id: str | None = None
    group_id: str | None = None
    payload: Any = field(default_factory=lambda: MappingProxyType({}))
    replayable: bool = True

    def __post_init__(self) -> None:
        if not self.session_id or not self.turn_id or self.sequence < 1 or self.epoch < 0:
            raise ValueError("ConversationEvent identity is malformed")
        _reject_sensitive_payload(self.payload)
        object.__setattr__(self, "payload", _immutable_copy(self.payload))

    def to_wire(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "task_id": self.task_id,
            "sequence": self.sequence,
            "epoch": self.epoch,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "monotonic_ns": self.monotonic_ns,
            "item_id": self.item_id,
            "tool_call_id": self.tool_call_id,
            "group_id": self.group_id,
            "payload": _wire_copy(self.payload),
            "replayable": self.replayable,
        }

    @classmethod
    def from_wire(cls, value: dict[str, Any]) -> "ConversationEvent":
        expected = {
            "session_id", "turn_id", "task_id", "sequence", "epoch", "event_id",
            "event_type", "monotonic_ns", "item_id", "tool_call_id", "group_id",
            "payload", "replayable",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("ConversationEvent wire envelope is malformed")
        return cls(**value)


@dataclass(frozen=True)
class HeardAudioBoundary:
    """Provider output position that the playback surface actually rendered."""

    item_id: str
    audio_end_ms: int


@dataclass(frozen=True)
class RealtimeEvent:
    """One ordered event emitted by a :class:`RealtimeSession`."""

    type: RealtimeEventType
    audio_bytes: bytes | None = None
    text: str | None = None
    final: bool = False
    call_id: str | None = None
    tool_name: str | None = None
    item_id: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def audio(cls, pcm: bytes, *, item_id: str | None = None) -> "RealtimeEvent":
        return cls(type=RealtimeEventType.AUDIO, audio_bytes=pcm, item_id=item_id)

    @classmethod
    def transcript(cls, text: str, *, final: bool = False) -> "RealtimeEvent":
        return cls(type=RealtimeEventType.TRANSCRIPT, text=text, final=final)

    @classmethod
    def tool_call(
        cls, call_id: str, name: str, arguments: dict[str, Any]
    ) -> "RealtimeEvent":
        return cls(
            type=RealtimeEventType.TOOL_CALL,
            call_id=call_id,
            tool_name=name,
            arguments=dict(arguments),
        )


class RealtimeSession(abc.ABC):
    """An open provider transport; it never dispatches Hermes tools itself."""

    @abc.abstractmethod
    async def send_audio(self, pcm: bytes) -> None:
        """Send a chunk of PCM input audio."""

    @abc.abstractmethod
    def events(self) -> AsyncIterator[RealtimeEvent]:
        """Yield ordered audio, transcript, tool-call, and turn events."""

    @abc.abstractmethod
    async def submit_tool_result(self, call_id: str, output: str) -> None:
        """Return a Hermes-dispatched tool result to the voice model."""

    async def truncate_response(self, boundary: HeardAudioBoundary) -> None:
        """Truncate provider history to heard audio when supported."""

    @abc.abstractmethod
    async def cancel_response(self) -> None:
        """Cancel current output for barge-in."""

    @abc.abstractmethod
    async def close(self) -> None:
        """Release provider and audio resources. Must be idempotent."""


class RealtimeVoiceProvider(abc.ABC):
    """Factory for provider-specific realtime voice sessions."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Stable lowercase plugin identifier."""

    @property
    def display_name(self) -> str:
        return self.name.title()

    def is_available(self) -> bool:
        return True

    def get_setup_schema(self) -> dict[str, Any]:
        return {"name": self.display_name, "badge": "", "tag": "", "env_vars": []}

    @abc.abstractmethod
    async def open_session(
        self,
        *,
        instructions: str,
        tools: list[dict[str, Any]],
        voice: str | None = None,
    ) -> RealtimeSession:
        """Open a session using Hermes-supplied instructions and tool schemas."""
