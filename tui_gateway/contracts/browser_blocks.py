"""Tern browser block discovery and explicit user handover."""
from pydantic import Field

from .base import Result
from .common import SessionParams
from .registry import method


class BrowserBlock(Result):
    target_id: str
    title: str
    url: str
    owner: int | None = None
    owned: bool
    available: bool


class BrowserBlocksResult(Result):
    available: bool
    blocks: list[BrowserBlock]


class BrowserBlockParams(SessionParams):
    target_id: str


class BrowserTargetResult(Result):
    target_id: str
    title: str
    url: str
    in_tern: bool
    frame: str | None = None


class BrowserFrameParams(BrowserBlockParams):
    frame: str = Field(pattern=r"^(main|(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))*)$")


class BrowserReleaseResult(Result):
    target_id: str
    released: bool


method("browser.blocks", params=SessionParams, result=BrowserBlocksResult,
       doc="List Tern browser blocks without granting drive permission.")
method("browser.adopt", params=BrowserBlockParams, result=BrowserTargetResult,
       doc="Explicit user intent: hand one undriven Tern browser block to this session.")
method("browser.focus", params=BrowserBlockParams, result=BrowserTargetResult,
       doc="Focus only an agent-owned or explicitly adopted browser block.")
method("browser.frame", params=BrowserFrameParams, result=BrowserTargetResult,
       doc="User selects a verified native frame for evaluation; other child-frame operations fail closed.")
method("browser.release", params=BrowserBlockParams, result=BrowserReleaseResult,
       doc="User releases an adopted block, or closes an agent-created block, after confirmed cleanup.")
