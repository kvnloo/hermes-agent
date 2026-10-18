"""Optional execute_code presentation companions; stdout remains the model-facing truth."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from .base import Payload


class EvalView(Payload):
    id: str
    kind: Literal["table", "json", "markdown"]
    # Unicode code-point offset into this cell's literal output, not bytes/UTF-16.
    start: int = Field(ge=0)
    printed: str
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class EvalWork(Payload):
    id: str
    tool: str
    status: Literal["running", "done", "error", "cancelled", "timeout", "background"]
    parent_id: str | None = None
    preview: str = ""


class EvalCell(Payload):
    id: str
    code: str
    language: str = "python"
    status: Literal["pending", "running", "done", "error", "cancelled", "timeout", "background"]
    output: str = ""
    error: str | None = None
    events: list[EvalWork] = Field(default_factory=list)
    views: list[EvalView] = Field(default_factory=list)


class EvalDisplay(Payload):
    version: Literal[1] = 1
    cells: list[EvalCell]


class EvalUpdatePayload(Payload):
    tool_id: str
    cell: EvalCell
    # Monotonic within this call, including its completion snapshot.
    revision: int = Field(ge=0)
