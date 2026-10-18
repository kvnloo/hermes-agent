"""Owner-scoped projections of the existing process and subagent registries."""

from typing import Literal

from pydantic import Field

from .base import Payload, Result
from .common import SessionParams
from .registry import event, method


class JobsChangedPayload(Payload):
    job_id: str


event("jobs.changed", JobsChangedPayload, doc="Owned process started or exited; invalidate the jobs snapshot.")


class JobSnapshot(Result):
    id: str
    kind: Literal["process", "subagent"]
    title: str
    state: str
    started: float
    owner_session_id: str
    parent_id: str | None = None
    can_cancel: bool = False


class JobsListResult(Result):
    jobs: list[JobSnapshot]


class JobIdParams(SessionParams):
    job_id: str = Field(min_length=1)


class JobsTailParams(JobIdParams):
    lines: int = Field(default=100, ge=1, le=500)


class JobsTailResult(Result):
    job_id: str
    text: str
    available: bool
    truncated: bool


class JobsCancelResult(Result):
    job_id: str
    accepted: bool


method("jobs.list", params=SessionParams, result=JobsListResult,
       doc="Background processes and live subagents owned by the calling session only.")
method("jobs.tail", params=JobsTailParams, result=JobsTailResult,
       doc="Last N lines (bounded to 16 KiB) of an owned job's output; does not consume notifications.")
method("jobs.cancel", params=JobIdParams, result=JobsCancelResult,
       doc="Cancel one owned running job; foreign and unknown ids are rejected.")
