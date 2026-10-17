"""Tern browser block discovery and explicit user handover."""
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


method("browser.blocks", params=SessionParams, result=BrowserBlocksResult,
       doc="List Tern browser blocks without granting drive permission.")
method("browser.adopt", params=BrowserBlockParams, result=BrowserTargetResult,
       doc="Explicit user intent: hand one undriven Tern browser block to this session.")
method("browser.focus", params=BrowserBlockParams, result=BrowserTargetResult,
       doc="Focus only an agent-owned or explicitly adopted browser block.")
