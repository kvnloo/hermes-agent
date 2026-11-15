"""A symlinked Hermes home must reach the running Webapp gateway's control socket.

Regression for NousResearch/hermes-agent#149810, reported by rudidev08.
"""
import asyncio
import json
from argparse import Namespace
from pathlib import Path

import pytest

from hermes_cli import gateway_client, webapp_launcher
from hermes_cli.gateway_runtime_discovery import _private_node


@pytest.mark.platforms("posix")
def test_status_uses_the_real_home_behind_a_symlink(tmp_path, monkeypatch, capsys):
    real_home = tmp_path / "real-home"
    real_home.mkdir(mode=0o700)
    (real_home / "config.yaml").write_text(
        "webapp:\n  enabled: true\n  host: 127.0.0.1\n  port: 9121\n", encoding="utf-8"
    )
    link_home = tmp_path / "link-home"
    link_home.symlink_to(real_home, target_is_directory=True)
    monkeypatch.setenv("HERMES_HOME", str(link_home))
    queries = []

    def control_query(home, request):
        # Exercise the real gateway control-path guard, which rejects symlink nodes.
        _private_node(Path(home), kind="directory", home=True)
        queries.append(Path(home))
        assert json.loads(request)["verb"] == "webapp-status"
        return b'{"ok":true,"result":{"state":"serving","url":"http://127.0.0.1:9121"}}\n'

    monkeypatch.setattr(gateway_client, "private_control_query", control_query)
    assert webapp_launcher.cmd_webapp(Namespace(status=True)) == 0
    assert queries == [real_home]
    assert "Serving at http://127.0.0.1:9121" in capsys.readouterr().out


@pytest.mark.platforms("linux", "macos")
@pytest.mark.parametrize("mode", [0o700, 0o777], ids=["private", "world-writable"])
def test_status_through_the_private_control_socket(tmp_path, monkeypatch, capsys, mode):
    from gateway.control_socket import GatewayControlServer

    real_home = tmp_path / "real-home"
    real_home.mkdir(mode=0o700)
    (real_home / "config.yaml").write_text("webapp:\n  enabled: true\n", encoding="utf-8")
    link_home = tmp_path / "link-home"
    link_home.symlink_to(real_home, target_is_directory=True)
    monkeypatch.setenv("HERMES_HOME", str(link_home))
    peers = []

    def status(params, peer):
        assert params == {}
        assert peer.startswith("uid:")
        peers.append(peer)
        return {"state": "serving", "url": "http://127.0.0.1:9121"}

    async def scenario():
        server = GatewayControlServer(real_home)
        server.private_handlers["webapp-status"] = status
        assert await server.start()
        try:
            real_home.chmod(mode)
            return await asyncio.to_thread(webapp_launcher.cmd_webapp, Namespace(status=True))
        finally:
            real_home.chmod(0o700)
            await server.stop()

    result = asyncio.run(scenario())
    output = capsys.readouterr().out
    if mode == 0o700:
        assert result == 0
        assert len(peers) == 1
        assert "Serving at http://127.0.0.1:9121" in output
    else:
        assert result == 1
        assert peers == []
        assert "Serving at" not in output
