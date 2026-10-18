"""Owned agent hub. Snapshot flags are hints; every intent rechecks live authority."""
from typing import Literal

from pydantic import Field

from .base import JsonValue, Result
from .common import SessionParams
from .registry import method


class AgentActions(Result):
    send: bool
    stop: bool
    transcript: bool


class AgentHubRow(Result):
    id: str
    subagent_id: str | None = None
    child_session_id: str | None = None
    parent_id: str | None = None
    goal: str
    model: str | None = None
    status: str
    last_tool: str | None = None
    actions: AgentActions


class AgentHubResult(Result):
    agents: list[AgentHubRow]


method("subagent.hub", params=SessionParams, result=AgentHubResult,
       doc="Live and persisted descendant roster, with explicit supported actions.")


class AgentTranscriptParams(SessionParams):
    child_session_id: str = Field(min_length=1)
    offset: int = Field(default=0, ge=0, strict=True)
    limit: int = Field(default=50, ge=1, le=100, strict=True)


class AgentTranscriptResult(Result):
    child_session_id: str
    messages: list[dict[str, JsonValue]]
    next_offset: int | None = None
    available: bool = False


method("subagent.transcript", params=AgentTranscriptParams, result=AgentTranscriptResult,
       doc="Read a canonical page of an owned descendant's full stored transcript, also while running.")


class AgentControlParams(SessionParams):
    subagent_id: str = Field(min_length=1)
    child_session_id: str = Field(min_length=1)


class AgentMessageParams(AgentControlParams):
    text: str = Field(min_length=1, max_length=32000, strict=True)


class AgentControlResult(Result):
    status: Literal["queued", "cancel_requested", "rejected"]


method("subagent.message", params=AgentMessageParams, result=AgentControlResult,
       doc="Queue steering to an exact owned live child, never revive a completed child. Queued is not delivered.")
method("subagent.stop", params=AgentControlParams, result=AgentControlResult,
       doc="Cooperatively request cancellation; acknowledgement is not terminal truth.")
