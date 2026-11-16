"""Regression for NousResearch/hermes-agent#156319: restart only before gateway accepts turns."""

import os
import sys

import pytest

from agent import process_bootstrap
from gateway import run_bootstrap
from gateway.restart import GATEWAY_SERVICE_RESTART_EXIT_CODE


@pytest.mark.asyncio
async def test_supervised_missing_openai_exits_at_boot_without_killing_turns(monkeypatch):
    # Model the real systemd supervisor, not an interactive Python interpreter.
    monkeypatch.setenv("INVOCATION_ID", "hermes-test-unit")
    monkeypatch.setenv("HERMES_SUPERVISED_CHILD", "1")
    monkeypatch.setitem(sys.modules, "openai", None)
    monkeypatch.setattr(process_bootstrap, "_OPENAI_CLS_CACHE", None)

    # A lazy import from a turn or auxiliary client may never terminate the
    # process: other sessions need the ordinary graceful shutdown path.
    monkeypatch.setattr(os, "_exit", lambda code: pytest.fail(f"hard exit {code} from lazy import"))
    monkeypatch.setattr(
        run_bootstrap,
        "_start_gateway_resolve_terminal_cwd",
        lambda: pytest.fail("gateway proceeded into startup with missing openai"),
    )

    with pytest.raises(SystemExit) as restart:
        await run_bootstrap._start_gateway_runtime()
    assert restart.value.code == GATEWAY_SERVICE_RESTART_EXIT_CODE

    with pytest.raises(ModuleNotFoundError) as missing:
        process_bootstrap._load_openai_cls()
    assert missing.value.name == "openai"
