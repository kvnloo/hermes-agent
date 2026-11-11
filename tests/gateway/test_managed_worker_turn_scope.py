"""A gateway turn executor runs in its own uncapped scope beside the gateway, not in the gateway cgroup.

Every managed worker (and every tool it runs, with their page cache and slab) used to be charged to
hermes-gateway.service, so the gateway's cgroup read 9.5 GB while its own process held < 1 GB.
"""
import asyncio
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tools import process_registry as pr
from gateway import session_managed_worker as smw
import gateway.session_worker_spawn as spawn_mod
import gateway.session_managed_worker_log as log_mod


@pytest.fixture
def supervised(monkeypatch):
    monkeypatch.setattr(pr, "_IS_LINUX", True)
    monkeypatch.setattr(pr, "_is_supervised_gateway_process", lambda: True)
    monkeypatch.setattr(pr, "_systemd_run_user_scope_available", lambda: True)
    monkeypatch.setattr(pr, "_own_slice", lambda: "agent.slice")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/systemd-run")


ARGV = [sys.executable, "-m", "agent.managed_worker"]


def test_turn_scope_wraps_the_worker_with_no_memory_limit(supervised):
    argv = pr.turn_scope_argv(ARGV, "sess/1:x")
    assert argv[:4] == ["/usr/bin/systemd-run", "--user", "--scope", "--quiet"]
    assert argv[-3:] == ARGV
    unit = argv[argv.index("--unit") + 1]
    assert unit.startswith("hermes-turn-sess-1-x-") and unit.endswith(".scope") is False
    assert argv[argv.index("--slice") + 1] == "agent.slice"
    joined = " ".join(argv)
    # Owner rule 2026-11-07: no memory caps on turns; ranking belongs to the OOM policy.
    assert "MemoryMax" not in joined and "MemoryHigh" not in joined and "MemorySwapMax" not in joined


def test_turn_scope_is_a_no_op_outside_a_supervised_gateway(monkeypatch):
    monkeypatch.setattr(pr, "_is_supervised_gateway_process", lambda: False)
    assert pr.turn_scope_argv(ARGV, "s") == ARGV


def test_turn_scope_is_a_no_op_without_a_user_manager(monkeypatch):
    monkeypatch.setattr(pr, "_IS_LINUX", True)
    monkeypatch.setattr(pr, "_is_supervised_gateway_process", lambda: True)
    monkeypatch.setattr(pr, "_systemd_run_user_scope_available", lambda: False)
    assert pr.turn_scope_argv(ARGV, "s") == ARGV


def test_own_slice_reads_the_parent_slice(monkeypatch, tmp_path):
    cg = tmp_path / "cgroup"
    cg.write_text("0::/user.slice/user-1000.slice/user@1000.service/agent.slice/hermes-gateway.service\n")
    assert pr._own_slice(cg) == "agent.slice"
    cg.write_text("0::/user.slice/user-1000.slice/user@1000.service/app.slice/x.scope\n")
    assert pr._own_slice(cg) == "app.slice"
    cg.write_text("0::/\n")
    assert pr._own_slice(cg) is None


def test_managed_worker_spawn_goes_through_the_turn_scope(monkeypatch, supervised):
    seen = {}

    async def fake_acquire(spawn, argv, **kwargs):
        seen["argv"], seen["env"] = argv, kwargs["env"]
        raise RuntimeError("stop after spawn argv")

    monkeypatch.setattr(spawn_mod, "acquire_process", fake_acquire)
    monkeypatch.setattr(log_mod, "worker_log_path", lambda profile: None)
    monkeypatch.setattr(smw, "_worker_env", lambda authority: {"PATH": "/usr/bin"})
    monkeypatch.setattr(pr, "systemd_user_bus_env", lambda base=None: {**(base or {}), "XDG_RUNTIME_DIR": "/run/user/1"})
    authority = SimpleNamespace(profile_id="p")
    ref = SimpleNamespace(session_id="sess1")
    with pytest.raises(RuntimeError, match="stop after spawn argv"):
        asyncio.run(smw._spawn_registered_worker(authority, ref, {"generation": 1}))
    assert seen["argv"][0] == "/usr/bin/systemd-run" and seen["argv"][-3:] == ARGV
    assert seen["env"]["XDG_RUNTIME_DIR"] == "/run/user/1"
