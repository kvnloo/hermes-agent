"""Request-path cache receipts and warm-session admission against the deployed burn law."""
import json
import time
from datetime import datetime, timezone, UTC
from types import SimpleNamespace as NS

import pytest

from agent import burn_pace_gate as gate
from agent.turn_api_call import perform_api_call


@pytest.fixture(autouse=True)
def cache_home(tmp_path, monkeypatch):
    monkeypatch.setattr(gate.Path, "home", lambda: tmp_path)
    path = tmp_path / ".z0int/state/posture/cache-breaks.jsonl"
    monkeypatch.setattr(gate, "_cache_breaks_path", lambda: path)
    return path


def agent():
    return NS(provider="anthropic", api_mode="anthropic_messages", session_id="session-a",
              _anthropic_api_key="test-key-a", model="claude-sonnet", base_url="", platform="cli",
              _has_stream_consumers=lambda: True, _has_pending_redirect=lambda: False,
              thinking_callback=None)


def response(read=0, write=1000):
    return NS(usage={"input_tokens": 100, "cache_read_input_tokens": read,
                     "cache_creation_input_tokens": write, "output_tokens": 1})


@pytest.mark.parametrize("gap,read,expected", [(269, 549, 1), (270, 0, 0), (10, 550, 0)])
def test_request_path_records_cache_break(cache_home, monkeypatch, gap, read, expected):
    a = agent()
    clock = [1000.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    monkeypatch.setattr("hermes_cli.middleware.run_llm_execution_middleware",
                        lambda kwargs, call, **_: call(kwargs))
    replies = iter([response(), response(read, 0)])
    a._interruptible_streaming_api_call = lambda *args, **kwargs: next(replies)
    kwargs = dict(_original_api_kwargs={}, _llm_middleware_trace=[], _moa_prepared_request=None,
                  _retry=NS(), thinking_spinner=None, retry_count=0, api_call_count=1,
                  api_request_id="request", effective_task_id="task", turn_id="turn", interrupted=False)
    with gate.cache_session(a):
        assert cache_home.exists()
        perform_api_call(a, api_kwargs={"messages": [{"role": "user", "content": "hello"}]}, **kwargs)
    clock[0] += gap
    a._anthropic_api_key = "test-key-b"
    with gate.cache_session(a):
        perform_api_call(a, api_kwargs={"messages": [{}, {}]}, **kwargs)
    rows = [json.loads(line) for line in cache_home.read_text().splitlines()]
    assert len(rows) == expected
    if expected:
        row = rows[0]
        assert row == {"ts": 1269.0, "session": "session-a", "gap_s": 269.0,
                       "prev_in": 1100, "in": 649, "cache_read": 549, "write": 0,
                       "cred_prev": row["cred_prev"], "cred": row["cred"], "msgs_prev": 1, "msgs": 2}
        assert row["cred_prev"] != row["cred"]
        assert "test-key" not in cache_home.read_text()


@pytest.mark.parametrize("gap,used,sticky", [(299, 94, True), (300, 94, False), (10, 95, False)])
def test_warm_session_respects_hard_stop(cache_home, monkeypatch, gap, used, sticky):
    if not gate._DEFAULT.exists():
        pytest.skip("deployed z0 burn law is not installed")
    monkeypatch.setenv("HERMES_POOL_ADMISSION", str(gate._DEFAULT))
    monkeypatch.setenv("BURN_GATE_HOME", str(cache_home.parents[3]))
    monkeypatch.delenv("HERMES_BURN_GATE_OVERRIDE", raising=False)
    monkeypatch.setattr(gate, "_mod", {"path": None, "mtime": None, "module": None})
    home = cache_home.parents[3]
    mapping = home / ".config/burn-gate/pool-lanes.json"
    mapping.parent.mkdir(parents=True)
    mapping.write_text(json.dumps({"anthropic": {"a": "hot", "b": "cool"}}))
    a = agent()
    rows = [NS(label="b", runtime_api_key="test-key-b", last_status="ok"),
            NS(label="a", runtime_api_key="test-key-a", last_status="ok")]
    now = time.time()
    with gate.cache_session(a):
        gate.record_call(a, response(), [{}])
    a._cache_last_call["ts"] = now - gap
    monkeypatch.setattr(time, "time", lambda: now)
    (cache_home.parent / "burn-pace.jsonl").write_text(json.dumps({
        "at": datetime.fromtimestamp(now, UTC).isoformat(),
        "lanes": {"hot": {"weekly_used_pct": used, "pace_ratio": 2},
                  "cool": {"weekly_used_pct": 10, "pace_ratio": 0.5}},
    }) + "\n")
    with gate.cache_session(a):
        assert gate.admit("anthropic", rows, a.model) == ([rows[1]] if sticky else [rows[0]])
        with gate.cache_session(agent()):
            assert gate.admit("anthropic", rows, a.model) == [rows[0]]
    assert gate.admit("anthropic", rows, a.model) == [rows[0]]
