"""Guardrails against kanban runaway loops.

Field shape: a goal card that ends every run blocked hits the unblock-loop
breaker (``block_loop_detected`` -> ``triage``), the dispatcher's
auto-decompose tick re-specifies it (``specified`` -> ``todo`` -> ``ready``)
and a worker respawns ~1 min later. One card ran 487 times in ~23 h this
way; an operator ``block --kind needs_input`` was refused because the card
sat in triage between runs. Three guards, each tested here:

1. The auto-decompose feed skips loop-escalated triage cards.
2. A typed human hold (``block_task``) works from ``triage``.
3. A per-task run-rate breaker parks any card that starts too many runs
   in an hour, whatever path keeps re-queueing it.
"""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_dispatch as kbd


@pytest.fixture
def kanban_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("HERMES_KANBAN_MAX_RUNS_PER_HOUR", raising=False)
    kb.init_db()
    return home


def _run(conn, tid):
    with kb.write_txn(conn):
        conn.execute("UPDATE tasks SET status='ready' WHERE id=?", (tid,))
    assert kb.claim_task(conn, tid, claimer="worker") is not None


def _loop_escalated(conn, title="goal card") -> str:
    """Drive a card into triage through the unblock-loop breaker."""
    tid = kb.create_task(conn, title=title, assignee="worker")
    _run(conn, tid)
    assert kb.block_task(conn, tid, reason="parked: run done", kind="needs_input")
    assert kb.unblock_task(conn, tid)
    _run(conn, tid)
    assert kb.block_task(conn, tid, reason="parked: run done", kind="needs_input")
    task = kb.get_task(conn, tid)
    assert task.status == "triage"
    assert kb.is_loop_escalated(task)
    return tid


# --- 1. auto-decompose must not re-arm a loop-escalated card ----------------


def test_auto_decompose_tick_skips_loop_escalated_triage(kanban_home, monkeypatch):
    from gateway import kanban_watchers_dispatcher as kwd
    from hermes_cli import kanban_decompose

    with kbc.connect_closing() as conn:
        looped = _loop_escalated(conn)
        fresh = kb.create_task(conn, title="fresh one-liner", assignee="worker", triage=True)
        assert kb.get_task(conn, fresh).status == "triage"
        assert not kb.is_loop_escalated(kb.get_task(conn, fresh))

    seen: list[str] = []

    def fake_decompose(task_id, author=None):
        seen.append(task_id)
        return SimpleNamespace(ok=True, fanout=False, child_ids=None, reason=None)

    monkeypatch.setattr(kanban_decompose, "decompose_task", fake_decompose)
    monkeypatch.setattr(kwd, "_board_slugs", lambda kb_mod: ["default"])
    settings = kwd._DispatcherSettings(60.0, None, None, 2, 0, True, None, None)
    dispatcher = kwd._KanbanDispatcher(SimpleNamespace(DEFAULT_BOARD="default"), settings)

    assert dispatcher.auto_decompose_tick(5) == 1
    assert seen == [fresh]
    # Human-invoked sweeps still see the whole column.
    assert set(kanban_decompose.list_triage_ids()) == {looped, fresh}


# --- 2. a human hold works from triage ----------------------------------------


def test_needs_input_hold_from_triage_parks_blocked_and_sticks(kanban_home):
    with kbc.connect_closing() as conn:
        tid = _loop_escalated(conn)
        assert kb.block_task(conn, tid, reason="HOLD for Kevin", kind="needs_input")
        held = kb.get_task(conn, tid)
        assert held.status == "blocked"
        assert held.block_kind == "needs_input"
        # Loop memory survives the hold: it is a human decision, not a recurrence.
        assert held.block_recurrences == kb.BLOCK_RECURRENCE_LIMIT
        ev = [e for e in kb.list_events(conn, tid) if e.kind == "blocked"][-1].payload
        assert ev["source_status"] == "triage"
        kb.recompute_ready(conn)
        assert kb.get_task(conn, tid).status == "blocked"
        # Only an explicit unblock releases it.
        assert kb.unblock_task(conn, tid)
        assert kb.get_task(conn, tid).status == "ready"


@pytest.mark.parametrize("kind", [None, "dependency"])
def test_triage_hold_refuses_untyped_and_dependency(kanban_home, kind):
    with kbc.connect_closing() as conn:
        tid = _loop_escalated(conn)
        assert not kb.block_task(conn, tid, reason="x", kind=kind)
        assert kb.get_task(conn, tid).status == "triage"


# --- 3. per-task run-rate breaker ---------------------------------------------


def _seed_runs(conn, tid, n, *, started_at=None):
    now = int(time.time()) if started_at is None else started_at
    with kb.write_txn(conn):
        for i in range(n):
            conn.execute(
                "INSERT INTO task_runs (task_id, profile, status, outcome, started_at, ended_at) "
                "VALUES (?, 'worker', 'done', 'blocked', ?, ?)", (tid, now - 60 - i, now - 30 - i),
            )


def _spawner(spawns):
    def fake_spawn(task, workspace, board=None):
        spawns.append(task.id)
        return 4242
    return fake_spawn


def test_run_rate_breaker_parks_card_and_unblock_rearms(kanban_home, all_assignees_spawnable, monkeypatch):
    monkeypatch.setenv("HERMES_KANBAN_MAX_RUNS_PER_HOUR", "5")
    spawns: list[str] = []
    with kbc.connect_closing() as conn:
        tid = kb.create_task(conn, title="spinner", assignee="worker")
        _seed_runs(conn, tid, 5)
        kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
        task = kb.get_task(conn, tid)
        assert tid not in spawns
        assert (task.status, task.block_kind) == ("blocked", "needs_input")
        trip = [e for e in kb.list_events(conn, tid) if e.kind == "blocked"][-1].payload
        assert trip["breaker"] == kb.RUN_RATE_BREAKER
        assert trip["runs"] == 5 and trip["limit"] == 5
        # Sticky across ticks: recompute_ready must not promote it back.
        kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
        assert kb.get_task(conn, tid).status == "blocked"
        assert tid not in spawns
        # An operator unblock buys a fresh budget (runs before the trip no longer count).
        assert kb.unblock_task(conn, tid)
        assert kb.runs_in_rate_window(conn, tid) == 0
        kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
        assert tid in spawns


def test_run_rate_breaker_ignores_old_runs_and_can_be_disabled(kanban_home, all_assignees_spawnable, monkeypatch):
    monkeypatch.setenv("HERMES_KANBAN_MAX_RUNS_PER_HOUR", "5")
    spawns: list[str] = []
    with kbc.connect_closing() as conn:
        old = kb.create_task(conn, title="old runs", assignee="worker")
        _seed_runs(conn, old, 10, started_at=int(time.time()) - 2 * kb.RUN_RATE_WINDOW_SECONDS)
        off = kb.create_task(conn, title="breaker off", assignee="worker")
        _seed_runs(conn, off, 10)
        kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
        assert old in spawns
        assert kb.get_task(conn, off).status == "blocked"

        monkeypatch.setenv("HERMES_KANBAN_MAX_RUNS_PER_HOUR", "0")
        assert kb.resolve_max_runs_per_hour() == 0
        assert kb.unblock_task(conn, off)
        _seed_runs(conn, off, 10)  # fresh runs after the trip
        kbd.dispatch_once(conn, spawn_fn=_spawner(spawns))
        assert off in spawns


def test_run_rate_breaker_does_not_count_refused_spawns(kanban_home, monkeypatch):
    """A host that refuses to place a worker retries on its own cooldown; those rows ran no model."""
    monkeypatch.setenv("HERMES_KANBAN_MAX_RUNS_PER_HOUR", "3")
    with kbc.connect_closing() as conn:
        tid = kb.create_task(conn, title="bus down", assignee="worker")
        now = int(time.time())
        with kb.write_txn(conn):
            for i, outcome in enumerate(["spawn_failed", "rate_limited"] * 3):
                conn.execute(
                    "INSERT INTO task_runs (task_id, profile, status, outcome, started_at, ended_at) "
                    "VALUES (?, 'worker', 'done', ?, ?, ?)", (tid, outcome, now - 60 - i, now - 30 - i),
                )
        assert kb.runs_in_rate_window(conn, tid) == 0
        assert kbd.check_respawn_guard(conn, tid) != kbd.RUN_RATE_GUARD


@pytest.mark.parametrize("raw,expected", [
    ("", kb.DEFAULT_MAX_RUNS_PER_HOUR), ("7", 7), ("0", 0), ("-3", kb.DEFAULT_MAX_RUNS_PER_HOUR),
    ("lots", kb.DEFAULT_MAX_RUNS_PER_HOUR),
])
def test_resolve_max_runs_per_hour_env(kanban_home, monkeypatch, raw, expected):
    monkeypatch.setenv("HERMES_KANBAN_MAX_RUNS_PER_HOUR", raw)
    assert kb.resolve_max_runs_per_hour() == expected
