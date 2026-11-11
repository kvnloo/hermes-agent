"""Cache-break diagnostics through the real retry loop, without provider traffic."""

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def detector(monkeypatch, tmp_path):
    monkeypatch.setattr("hermes_cli._early_recovery.restore_interrupted_pull", lambda root: False)
    import agent.conversation_loop as loop
    import agent.turn_request_assembly as assembly

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    clock = SimpleNamespace(now=1000.0)
    monkeypatch.setattr(assembly, "time", SimpleNamespace(time=lambda: clock.now), raising=False)
    agent = SimpleNamespace(
        api_mode="anthropic_messages", provider="anthropic", session_id="cache-break-test",
        _credential_pool_entry_id="credential-one",
        context_compressor=SimpleNamespace(compression_count=0),
    )
    state = SimpleNamespace(retry_count=0, max_retries=1, current_turn_user_idx=2)

    @dataclass
    class Verdict:
        action: str = "fallthrough"

    def guard(agent):
        return Verdict()

    def build(agent):
        return Verdict()

    def call(agent):
        return Verdict()

    def check(agent):
        return Verdict("break")

    monkeypatch.setattr(loop, "nous_rate_limit_guard", guard)
    monkeypatch.setattr(loop, "build_api_request", build)
    monkeypatch.setattr(loop, "perform_api_call", call)
    monkeypatch.setattr(loop, "check_api_response", check)
    wire = [
        {"role": "user", "content": [{"type": "text", "text": "PRIVATE question"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "PRIVATE answer"}]},
        {"role": "user", "content": [{"type": "text", "text": "PRIVATE followup"}]},
    ]
    path = tmp_path / ".z0int/state/posture/cache-breaks.jsonl"

    def send(messages=wire, *, read=0, write=900, uncached=100):
        state.api_kwargs = {"messages": messages}
        state.response = SimpleNamespace(usage=SimpleNamespace(
            input_tokens=uncached, output_tokens=10,
            cache_read_input_tokens=read, cache_creation_input_tokens=write,
        ))
        loop._run_api_retry_loop(agent, state)

    return SimpleNamespace(agent=agent, clock=clock, wire=wire, path=path, send=send)


def test_cache_break_records_first_changed_wire_message(detector):
    d = detector
    original = copy.deepcopy(d.wire)
    d.send()
    assert not d.path.exists()
    d.clock.now += 20
    d.agent._credential_pool_entry_id = "credential-two"
    d.agent.context_compressor.compression_count += 1
    d.wire[1]["content"][0]["text"] = "PRIVATE changed answer"
    d.send(read=100, write=800)
    row = json.loads(d.path.read_text())
    assert row == {
        "ts": 1020.0, "session": "cache-break-test", "gap_s": 20.0,
        "prev_in": 1000, "in": 1000, "cache_read": 100, "write": 800,
        "cred_prev": "credential-one", "cred": "credential-two",
        "msgs_prev": 3, "msgs": 3, "first_diff_idx": 1, "anchor_idx": 2,
        "compacted": True,
    }
    assert "PRIVATE" not in d.path.read_text()
    expected = [hashlib.sha256(json.dumps(m, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                for m in d.wire]
    assert d.agent._cache_break_previous["hashes"] == expected
    assert d.wire[0] == original[0]
    d.clock.now += 1
    d.send()
    row = json.loads(d.path.read_text().splitlines()[-1])
    assert row["first_diff_idx"] == -1
    assert row["compacted"] is False


@pytest.mark.parametrize("gap,read,session,mode,expected", [
    (269, 499, "cache-break-test", "anthropic_messages", True),
    (270, 0, "cache-break-test", "anthropic_messages", False),
    (1, 500, "cache-break-test", "anthropic_messages", False),
    (1, 0, "new-session", "anthropic_messages", False),
    (1, 0, "cache-break-test", "chat_completions", False),
])
def test_cache_break_threshold_and_session_scope(detector, gap, read, session, mode, expected):
    d = detector
    d.send()
    d.clock.now += gap
    d.agent.session_id = session
    d.agent.api_mode = mode
    d.send(read=read)
    assert d.path.exists() is expected
