"""Provider-neutral contracts for persistent, bidirectional voice sessions.

Realtime providers own audio transport and turn-taking. Hermes remains the
owner of tools, approvals, conversation history, and memory; provider tool
calls are events that a host-side coordinator dispatches through Hermes.
"""

from __future__ import annotations

import abc
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RealtimeEventType(str, Enum):
    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    TOOL_CALL = "tool_call"
    TURN_STARTED = "turn_started"
    TURN_ENDED = "turn_ended"
    ERROR = "error"


@dataclass(frozen=True)
class HeardAudioBoundary:
    """Provider output position that the playback surface actually rendered."""

    item_id: str
    audio_end_ms: int


@dataclass(frozen=True)
class SurfaceSessionConfig:
    """Short-lived, least-privilege config for a surface-hosted transport.

    ``session_token`` is a minted session credential, never a provider API key.
    The closed shape prevents plugins from passing arbitrary provider config or
    approval authority into a surface.
    """

    provider: str
    session_id: str
    endpoint: str
    session_token: str
    expires_at: float
    scopes: frozenset[str] = field(default_factory=frozenset)

    MAX_TTL_SECONDS = 300.0
    ALLOWED_SCOPES = frozenset({"audio.send", "events.receive"})

    def validate(self, *, now: float | None = None) -> None:
        current_time = time.time() if now is None else now
        if not all((self.provider, self.session_id, self.endpoint, self.session_token)):
            raise ValueError("Surface session config fields must be non-empty")
        if self.expires_at <= current_time:
            raise ValueError("Surface session config is expired")
        if self.expires_at > current_time + self.MAX_TTL_SECONDS:
            raise ValueError("Surface session config lifetime exceeds the maximum")
        if self.scopes - self.ALLOWED_SCOPES:
            raise ValueError("Surface session config requests an unsupported scope")


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

    async def mint_surface_session(
        self,
        *,
        instructions: str,
        tools: list[dict[str, Any]],
        voice: str | None = None,
    ) -> SurfaceSessionConfig:
        """Mint scoped config for an optional surface-hosted transport."""
        raise NotImplementedError("Provider does not support surface-hosted sessions")
