"""Session-authorized, read-only operational snapshots for native inspection sheets."""
from typing import Literal

from .base import Params, Result, WireEnum
from .registry import method


class OperationalView(WireEnum):
    mcp_list = "mcp-list"
    mcp_status = "mcp-status"
    mcp_tools = "mcp-tools"
    mcp_catalog = "mcp-catalog"
    ssh_list = "ssh-list"


class OperationalReportParams(Params):
    session_id: str
    view: OperationalView


class OperationalReportRow(Result):
    name: str
    details: list[str]


class OperationalReportState(WireEnum):
    ready = "ready"
    unavailable = "unavailable"


class OperationalReportResult(Result):
    view: OperationalView
    scope: str
    state: OperationalReportState
    read_only: Literal[True]
    rows: list[OperationalReportRow]
    message: str


method("operations.report", params=OperationalReportParams, result=OperationalReportResult,
       doc="Read only cached MCP/config/catalog or this session profile's SSH terminal target. "
           "Never connects, reloads, authenticates, executes SSH, or mutates settings.")
