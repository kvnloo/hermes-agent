"""Regression for #144883: hosted-room RPC cannot load profile files on the gateway loop."""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from agent.secret_scope import current_secret_scope
from gateway.session_hosted_rpc import HostedRoomAuthorityRPC
from hermes_constants import get_hermes_home_override
from tools import terminal_scope


@pytest.mark.asyncio
async def test_hosted_room_rpc_scope_build_does_not_block_gateway_loop(tmp_path, monkeypatch):
    home = tmp_path / "profiles" / "hosted"
    home.mkdir(parents=True)
    (home / ".env").write_text(
        "HOSTED_RPC_SCOPE_KEY=from-profile\nTERMINAL_TIMEOUT=77\n", encoding="utf-8",
    )
    (home / "config.yaml").write_text("terminal:\n  backend: local\n", encoding="utf-8")
    authority = SimpleNamespace(
        profile_id=str(home),
        runner=SimpleNamespace(config=SimpleNamespace(multiplex_profiles=True)),
    )
    principal = SimpleNamespace(subject="member", profile_id=str(home))
    rpc = HostedRoomAuthorityRPC(
        authority, asyncio.get_running_loop(), room_id="room", member_id="member",
        profile="hosted", principal=principal, authorize=lambda *_: True,
    )

    async def inspect_results(_params):
        return {
            "home": get_hermes_home_override(),
            "secrets": current_secret_scope(),
            "terminal": terminal_scope.get_terminal_scope(),
        }

    monkeypatch.setattr(rpc, "_results", inspect_results)
    loop_thread = threading.get_ident()
    build_threads = []
    started, release = threading.Event(), threading.Event()
    real_build = terminal_scope.build_profile_terminal_scope

    def stalled_build(*args, **kwargs):
        build_threads.append(threading.get_ident())
        started.set()
        assert release.wait(2.0), "hosted-room RPC blocked the gateway loop during profile policy I/O"
        return real_build(*args, **kwargs)

    monkeypatch.setattr(terminal_scope, "build_profile_terminal_scope", stalled_build)

    async def ticker():
        while not started.is_set():
            await asyncio.sleep(0)
        release.set()

    task = asyncio.create_task(ticker())
    try:
        observed = await rpc._dispatch("results", {})
    finally:
        release.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert started.is_set(), "test did not enter the profile-policy reader"
    assert build_threads and loop_thread not in build_threads, "profile files were read on the loop"
    assert observed["home"] == str(home)
    assert observed["secrets"]["HOSTED_RPC_SCOPE_KEY"] == "from-profile"
    assert observed["terminal"]["TERMINAL_TIMEOUT"] == "77"
