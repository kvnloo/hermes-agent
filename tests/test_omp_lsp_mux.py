"""Hermes attaches to the OMP LSP mux and does not spawn its own server."""

import asyncio
import os

import pytest

from agent.lsp.omp_mux import SERVER_FOR_FILE, attach_omp_mux, omp_server_command
from agent.lsp.protocol import encode_message, read_message


async def _serve(path: str, seen: list[dict]) -> asyncio.AbstractServer:
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        msg = await read_message(reader)
        seen.append(msg)
        method = msg.get("method") if isinstance(msg, dict) else None
        if method == SERVER_FOR_FILE:
            result = {"command": "/usr/bin/pyright-langserver", "args": ["--stdio"], "cwd": "/work"}
        else:
            result = {"key": "sha256:test", "spawned": False, "pid": 1}
        writer.write(encode_message({"jsonrpc": "2.0", "id": msg["id"], "result": result}))
        await writer.drain()
        if method != SERVER_FOR_FILE:
            await reader.read(1)

    server = await asyncio.start_unix_server(handle, path=path)
    return server


@pytest.mark.asyncio
async def test_omp_mux_lookup_uses_the_socket_and_attach_does_not_spawn(tmp_path, monkeypatch):
    socket = tmp_path / "lsp-mux.sock"
    seen: list[dict] = []
    server = await _serve(str(socket), seen)
    monkeypatch.setenv("OMP_LSP_MUX_SOCKET", str(socket))
    try:
        resolved = await omp_server_command("/work", ".py")
        assert resolved == {"command": "/usr/bin/pyright-langserver", "args": ["--stdio"], "cwd": "/work"}
        proc = await attach_omp_mux(["/usr/bin/pyright-langserver", "--stdio"], "/work")
        assert proc.pid == 0
        assert seen[0]["method"] == "omp/serverForFile"
        assert seen[1]["method"] == "omp/muxConnect"
        assert seen[1]["params"]["command"] == "/usr/bin/pyright-langserver"
        await proc.wait()
    finally:
        server.close()
        await server.wait_closed()
        os.environ.pop("OMP_LSP_MUX_SOCKET", None)
