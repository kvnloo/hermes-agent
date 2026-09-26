
import json

import pytest

# Tail-only receipt reads: the retained listing renders just a 200-char output
# preview, so hydrating whole outputs is pure waste. These tests pin the
# contract: tail mode returns the exact decoded suffix for adversarial
# outputs, falls back safely on unfamiliar shapes, and never touches the
# full-hydration path that get()/read_log() rely on.

_TAIL_OUTPUTS = {
    "long_plain": "x" * 50_000,
    "escapes": 'line "quoted"\ttab\\slash\n' * 8_000,
    "ends_with_backslash": "abc\\" * 10_000,
    "ends_with_escape": ("data\\u0041" ) * 10_000,
    "emoji": "🎉 done\n" * 8_000,
    "exactly_200": "q" * 200,
    "shorter_than_tail": "short",
    "empty": "",
    # Tail-window cut lands inside an escape run; the boundary must not split it.
    "escape_run_in_window": "A" * 50_000 + "\\u0041" * 2_000 + "Z" * 500,
}


def _write_receipt(home_dir, proc_id, output, owner, ensure_ascii=False):
    from tools.process_registry_results import _RESULT_FIELDS
    receipt = {field: f"v-{field}" for field in _RESULT_FIELDS}
    receipt.update(id=proc_id, parent_session_id=owner, output=output,
                   started_at=1_700_000_000.0)
    path = home_dir / "logs" / "process-results" / f"{proc_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=ensure_ascii), encoding="utf-8")
    return path


def _tail_fixture_paths(home_dir, owner):
    paths = {}
    for name, output in _TAIL_OUTPUTS.items():
        proc_id = f"proc_tail{name.replace('_', '')[:12]}"
        paths[name] = _write_receipt(home_dir, proc_id, output, owner)
    # Literal \uXXXX escapes in the raw file (ensure_ascii=True), including an
    # all-escape output whose 64-char window has no safe cut: must fall back.
    paths["ascii_escapes"] = _write_receipt(
        home_dir, "proc_tailasciiesc", "é→✓" * 8_000, owner, ensure_ascii=True)
    paths["all_escape_fallback"] = _write_receipt(
        home_dir, "proc_tailallesc", "é" * 20_000, owner, ensure_ascii=True)
    # Non-BMP via ensure_ascii=True: surrogate pairs (12 raw chars per char).
    # The tail cut must never land between a high and low surrogate.
    paths["nonbmp_escapes"] = _write_receipt(
        home_dir, "proc_tailnonbmp", "🎉" * 300 + "A" * 11, owner, ensure_ascii=True)
    paths["nonbmp_mixed"] = _write_receipt(
        home_dir, "proc_tailnonbmp2", "🎉" * 199 + "A" * 11, owner, ensure_ascii=True)
    # Lone surrogate (from surrogate-escaped argv/paths): not a pair, just a
    # 6-char token; must round-trip, not crash or pair up.
    paths["lone_surrogate"] = _write_receipt(
        home_dir, "proc_taillone", "A\ud83cB" * 5_000, owner, ensure_ascii=True)
    # Hand-written receipt: output not last, odd key order — exercises the
    # full-parse fallback (fast path must refuse, tail must stay correct).
    odd_path = home_dir / "logs" / "process-results" / "proc_tailoddorder.json"
    odd_path.parent.mkdir(parents=True, exist_ok=True)
    odd_path.write_text(json.dumps(
        {"id": "proc_tailoddorder", "output": "O" * 5_000,
         "command": "weird", "parent_session_id": owner}), encoding="utf-8")
    paths["odd_order_fallback"] = odd_path
    return paths


def test_tail_read_matches_full_decode_for_adversarial_outputs(tmp_path, monkeypatch):
    from tools.process_registry_results import _load_receipt_tail, _load_tail_or_full
    from hermes_constants import get_hermes_home
    owner = "tail-owner"
    monkeypatch.setenv("HERMES_SESSION_ID", owner)
    home = get_hermes_home()
    paths = _tail_fixture_paths(home, owner)
    # Hand-written receipt: output not last, odd key order — the fast path must
    # refuse it, and the fallback must still load the true tail.
    odd_path = paths.pop("odd_order_fallback")
    with pytest.raises(ValueError):
        _load_receipt_tail(odd_path, 200)
    recovered = _load_tail_or_full(odd_path, 200)
    assert recovered["output"] == "O" * 200
    assert recovered["command"] == "weird"
    for name, path in paths.items():
        full = json.loads(path.read_text(encoding="utf-8"))
        fast = _load_receipt_tail(path, 200)
        expected = dict(full)
        expected["output"] = full["output"][-200:]
        assert fast == expected, name


def test_listing_uses_tail_mode_and_lookup_stays_full(tmp_path, monkeypatch):
    import time
    from tools.process_registry import ProcessRegistry
    from tools.process_registry_results import load_completed_results
    from agent import redact
    monkeypatch.setattr(redact, "_REDACT_ENABLED", False)
    owner = "tail-owner"
    monkeypatch.setenv("HERMES_SESSION_ID", owner)
    from tools.process_registry import ProcessSession
    output = "payload\n" * 20_000  # ~160KB retained output
    session = ProcessSession(
        id="proc_taillisting", command="echo hi", cwd=str(tmp_path),
        task_id="owner-1", owner_task_id="owner-1", session_key="chat-1",
        parent_session_id=owner, started_at=time.time(),
        output_buffer=output, exited=True, exit_code=0,
    )
    registry = ProcessRegistry()
    registry._running[session.id] = session
    registry._move_to_finished(session)

    full = load_completed_results()
    assert full[session.id].output_buffer == output
    tail = load_completed_results(tail_chars=200)
    assert tail[session.id].output_buffer == output[-200:]
    assert len(tail[session.id].output_buffer) <= 200

    # The listing renders only the preview and must agree with the tail read.
    rows = ProcessRegistry().list_sessions(task_id="owner-1", include_retained=True)
    assert [r["session_id"] for r in rows] == [session.id]
    assert rows[0]["output_preview"] == output[-200:]
    assert rows[0]["output_preview"] == tail[session.id].output_buffer
    # Exact lookup keeps full hydration for get()/read_log().
    assert ProcessRegistry().get(session.id).output_buffer == output
