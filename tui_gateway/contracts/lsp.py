"""Read-only semantic LSP queries; positions are one-based UTF-16 code units."""
from typing import Literal

from pydantic import Field

from .base import Result
from .common import SessionParams
from .registry import method


class LspQueryParams(SessionParams):
    operation: Literal["references", "symbols", "hover"]
    path: str = Field(min_length=1)
    line: int = Field(default=1, ge=1, strict=True)
    col: int = Field(default=1, ge=1, strict=True)


class LspPosition(Result):
    line: int = Field(ge=1, strict=True)
    col: int = Field(ge=1, strict=True)


class LspRange(Result):
    start: LspPosition
    end: LspPosition


class LspLocation(Result):
    path: str
    range: LspRange


class LspSymbol(Result):
    id: str
    name: str
    kind: int
    location: LspLocation
    selection: LspRange
    children: list["LspSymbol"]


class LspBase(Result):
    path: str
    server: str | None
    position_encoding: Literal["utf-16"] = "utf-16"


class LspReferences(LspBase):
    kind: Literal["references"]
    locations: list[LspLocation]


class LspSymbols(LspBase):
    kind: Literal["symbols"]
    symbols: list[LspSymbol]


class LspHoverContent(Result):
    format: Literal["markdown", "plaintext", "code"]
    text: str
    language: str | None = None


class LspHover(LspBase):
    kind: Literal["hover"]
    contents: list[LspHoverContent]
    range: LspRange | None


class LspFailure(LspBase):
    kind: Literal["unavailable", "error"]
    operation: Literal["references", "symbols", "hover"]
    message: str


class LspQueryResult(Result):
    lsp_result: LspReferences | LspSymbols | LspHover | LspFailure


method("lsp.query", params=LspQueryParams, result=LspQueryResult,
       doc="Read-only references, document symbols or hover from the session-local Hermes LSP service; never a model call.")
