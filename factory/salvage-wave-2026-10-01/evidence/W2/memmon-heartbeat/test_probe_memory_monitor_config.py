"""Probe (not a contract test): what each candidate passes to start_memory_monitoring
for malformed logging.memory_monitor values. Uses a fake start so a 0/negative interval
cannot spin the real monitor loop (stop_event.wait(0) returns immediately)."""
from __future__ import annotations

import json
import threading

import pytest

import gateway.run as gateway_run
from gateway import memory_monitor as mm
from gateway.config import GatewayConfig

from tests.gateway.test_memory_monitor_gateway_wiring import _boot, _make_runner_cls

CASES = {
    "interval-abc": "    enabled: true\n    interval_seconds: abc\n",
    "interval-0": "    enabled: true\n    interval_seconds: 0\n",
    "interval-neg5": "    enabled: true\n    interval_seconds: -5\n",
    "enabled-string-false": "    enabled: 'false'\n",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(CASES) + ["scalar-false"])
async def test_probe(case, tmp_path, monkeypatch, capsys):
    seen: dict = {}
    runner_cls = _make_runner_cls(seen, running=True, exit_with_failure=False)
    _boot(monkeypatch, tmp_path, CASES.get(case), runner_cls)
    if case == "scalar-false":
        (tmp_path / "config.yaml").write_text("logging:\n  memory_monitor: false\n", encoding="utf-8")
    calls: list = []
    monkeypatch.setattr(mm, "start_memory_monitoring",
                        lambda interval_seconds=300.0, *a, **k: calls.append(float(interval_seconds)) or True)
    err = None
    try:
        ok = await gateway_run.start_gateway(config=GatewayConfig(), replace=False, verbosity=None)
    except BaseException as exc:  # record, don't fail
        ok, err = None, f"{type(exc).__name__}: {exc}"
    with open("/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad/memmon-probe.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"case": case, "start_calls": calls, "ok": ok, "error": err}) + "\n")
