"""Deterministic gateway history bound — Telegram context-rot guard.

LLM hygiene can fire, wait 10s, then proceed uncompressed (#90845 / #92318).
Cooldown then skips later attempts. This bound is the fail-closed window the
model actually sees.
"""

from gateway.history_bound import _BOUNDARY_PREFIX, bound_history_to_hard_limit


def _msgs(n: int, prefix: str = "m") -> list:
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"{prefix}{i}"} for i in range(n)]


def test_bound_noop_under_limit():
    history = _msgs(10)
    out = bound_history_to_hard_limit(history, hard_msg_limit=10)
    assert out is history


def test_bound_noop_empty():
    assert bound_history_to_hard_limit([], 10) == []
    assert bound_history_to_hard_limit(None, 10) is None


def test_bound_keeps_head_stub_and_newest_tail():
    history = _msgs(20)
    out = bound_history_to_hard_limit(history, hard_msg_limit=10, protect_first_n=3)
    assert len(out) == 10
    assert [m["content"] for m in out[:3]] == ["m0", "m1", "m2"]
    assert out[3]["role"] == "assistant"
    assert _BOUNDARY_PREFIX in out[3]["content"]
    assert "Omitted 11 earlier messages" in out[3]["content"]
    assert [m["content"] for m in out[4:]] == [f"m{i}" for i in range(14, 20)]
    # Original transcript object is not mutated.
    assert len(history) == 20


def test_bound_preserves_latest_user_turn():
    history = _msgs(30)
    history[-1] = {"role": "user", "content": "latest-ask"}
    out = bound_history_to_hard_limit(history, hard_msg_limit=8, protect_first_n=2)
    assert out[-1]["content"] == "latest-ask"
    assert len(out) == 8


def test_parent_session_scale_does_not_leak_middle_tasks():
    """A 20k-message Telegram DM must not feed the middle of the transcript."""
    history = _msgs(500, prefix="taskA-") + _msgs(500, prefix="taskB-")
    history.append({"role": "user", "content": "why the unrelated blender scene"})
    out = bound_history_to_hard_limit(history, hard_msg_limit=250, protect_first_n=3)
    assert len(out) == 250
    blob = " ".join(m["content"] for m in out)
    assert "why the unrelated blender scene" in blob
    # Middle-task rows are in the omitted window (index 3..750).
    assert "taskA-400" not in blob
    assert "taskB-100" not in blob
