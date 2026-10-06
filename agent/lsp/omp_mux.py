"""Join the language server OMP already runs.

OMP's mux owns the process. Hermes asks that mux which command to use, then
attaches with ``omp/muxConnect``. It does not spawn its own binary.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from agent.lsp.protocol import LSPProtocolError, encode_message, read_message

OMP_LSP_MUX_SOCKET = "OMP_LSP_MUX_SOCKET"
SERVER_FOR_FILE = "omp/serverForFile"
MUX_CONNECT = "omp/muxConnect"


class MuxProc:
    """Socket pair that satisfies the few Process calls the LSP client makes."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.stdin = writer
        self.stdout = reader
        self.stderr = None
        self.returncode: Optional[int] = None
        self.pid = 0

    def kill(self) -> None:
        self.returncode = 0
        self.stdin.close()

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = 0
            self.stdin.close()
        return self.returncode


def mux_socket() -> str:
    return os.environ.get(OMP_LSP_MUX_SOCKET, "").strip()


async def _exchange(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, method: str, params: dict, req_id: str) -> dict:
    writer.write(encode_message({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}))
    await writer.drain()
    msg = await read_message(reader)
    if not isinstance(msg, dict):
        raise LSPProtocolError("OMP LSP mux closed before a reply")
    error = msg.get("error")
    if isinstance(error, dict):
        raise LSPProtocolError(str(error.get("message") or "OMP LSP mux error"))
    result = msg.get("result")
    return result if isinstance(result, dict) else {}


async def omp_server_command(cwd: str, extension: str) -> Optional[dict]:
    """Ask the mux for the command OMP resolved. None when the socket is unset or OMP has no server."""
    socket = mux_socket()
    if not socket:
        return None
    reader, writer = await asyncio.open_unix_connection(socket)
    try:
        result = await _exchange(reader, writer, SERVER_FOR_FILE, {"cwd": cwd, "extension": extension}, "server-for-file")
    finally:
        writer.close()
    command = result.get("command")
    if not isinstance(command, str) or not command:
        return None
    args = result.get("args")
    return {
        "command": command,
        "args": [arg for arg in args if isinstance(arg, str)] if isinstance(args, list) else [],
        "cwd": result.get("cwd") if isinstance(result.get("cwd"), str) and result.get("cwd") else cwd,
    }


async def attach_omp_mux(command: list[str], cwd: str) -> MuxProc:
    """Bind a mux link to the server OMP identified. The caller must not spawn locally."""
    socket = mux_socket()
    if not socket:
        raise LSPProtocolError("OMP LSP mux socket is not set")
    if not command:
        raise LSPProtocolError("OMP LSP mux connect needs a command")
    reader, writer = await asyncio.open_unix_connection(socket)
    await _exchange(
        reader,
        writer,
        MUX_CONNECT,
        {"command": command[0], "args": command[1:], "cwd": cwd},
        "mux-connect",
    )
    return MuxProc(reader, writer)
