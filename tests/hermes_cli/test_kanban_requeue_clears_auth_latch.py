"""#121281: a requeue after a REAL auth failure is a fresh attempt.

A spawn that fails with a 401 stamps ``tasks.last_failure_error`` and
``check_respawn_guard`` parks the card as ``blocker_auth``. That is right
until the operator (or the dependency graph) sends the card back to work:
only ``unblock_task`` cleared the stamp, so every other requeue path left a
``ready`` card guarded forever, with nothing spawning and the breaker unable
to trip. Each requeue path below must clear the latch; the controls pin that
an un-requeued failure still parks, ``unblock_task`` still works, the breaker
counter survives the requeue, and a fresh failure after it parks again.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_dispatch as kbd

AUTH_401 = "provider authentication failed (401)"
NOW = 5_000_000


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    return home


@pytest.fixture
def clock(monkeypatch):
    """Whole-second clock shared by the DB writes, so each step lands on its own second."""
    state = {"t": NOW}
    monkeypatch.setattr(kb.time, "time", lambda: state["t"])
    return state


def _tick(clock, seconds=60):
    clock["t"] += seconds


def _auth_fail(conn, tid, **kw):
    """The dispatcher's own spawn-failure path, with a real 401."""
    return kbd._record_task_failure(
        conn, tid, AUTH_401, outcome="spawn_failed",
        release_claim=True, end_run=True, **kw,
    )


def _blocked_by_auth(conn, clock, title, **kw):
    tid = kb.create_task(conn, title=title, assignee="a")
    assert kb.claim_task(conn, tid) is not None
    assert _auth_fail(conn, tid, force_trip=True, **kw) is True
    assert kb.get_task(conn, tid).status == "blocked"
    assert kbd.check_respawn_guard(conn, tid) == "blocker_auth"
    _tick(clock)
    return tid


def _ready_after_auth(conn, clock, title):
    """Auth failure under the breaker limit: the card goes back to ``ready`` stamped."""
    tid = kb.create_task(conn, title=title, assignee="a")
    assert kb.claim_task(conn, tid) is not None
    assert _auth_fail(conn, tid) is False
    assert kb.get_task(conn, tid).status == "ready"
    assert kbd.check_respawn_guard(conn, tid) == "blocker_auth"
    _tick(clock)
    return tid


@pytest.fixture
def dashboard(kanban_home):
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    plugin_file = Path(__file__).resolve().parents[2] / "plugins" / "kanban" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("hermes_dashboard_plugin_kanban_121281_test", plugin_file)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    app = fastapi.FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/kanban")
    return TestClient(app)


# --- requeue paths -----------------------------------------------------------


def test_promote_task_after_auth_failure_is_fresh_attempt(kanban_home, clock):
    with kbc.connect() as conn:
        tid = _blocked_by_auth(conn, clock, "promote")
        assert kb.promote_task(conn, tid, actor="operator") == (True, None)
        assert kb.get_task(conn, tid).status == "ready"
        assert kbd.check_respawn_guard(conn, tid) is None


def test_dashboard_drag_to_ready_after_auth_failure_is_fresh_attempt(kanban_home, clock, dashboard):
    """``_set_status_direct`` (``status`` event): the parked card is dragged out
    of ``ready`` and back after the credential is fixed."""
    with kbc.connect() as conn:
        tid = _ready_after_auth(conn, clock, "drag")
    for status in ("todo", "ready"):
        r = dashboard.patch(f"/api/plugins/kanban/tasks/{tid}", json={"status": status})
        assert r.status_code == 200, r.text
        _tick(clock)
    with kbc.connect() as conn:
        assert kb.get_task(conn, tid).status == "ready"
        assert kbd.check_respawn_guard(conn, tid) is None


def test_recompute_ready_auto_promotion_after_auth_failure_is_fresh_attempt(kanban_home, clock):
    """``recompute_ready`` (``promoted`` event): a plain breaker trip is released
    once the limit is raised, and the released card must actually spawn."""
    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="auto-promote", assignee="a")
        assert kb.claim_task(conn, tid) is not None
        assert _auth_fail(conn, tid, failure_limit=1) is True
        assert kb.get_task(conn, tid).status == "blocked"
        _tick(clock)
        assert kb.recompute_ready(conn, failure_limit=3) == 1
        assert kb.get_task(conn, tid).status == "ready"
        assert kbd.check_respawn_guard(conn, tid) is None


def test_reopen_review_task_after_auth_failure_is_fresh_attempt(kanban_home, clock):
    """``reopen_review_task`` (``review_reopened`` event): the reviewer spawn
    failed on auth, the operator sends the card back to the implementer."""
    with kbc.connect() as conn:
        tid = kb.create_task(conn, title="reopen", assignee="a")
        assert kb.claim_task(conn, tid) is not None
        run = kb.get_task(conn, tid).current_run_id
        assert kb.request_review(conn, tid, summary="ready", reviewer="rev", expected_run_id=run)
        _tick(clock)
        assert kb.claim_review_task(conn, tid) is not None
        assert _auth_fail(conn, tid) is False
        assert kb.get_task(conn, tid).status == "review"
        assert kbd.check_respawn_guard(conn, tid, lane="review") == "blocker_auth"
        _tick(clock)
        assert kb.reopen_review_task(conn, tid)
        assert kb.get_task(conn, tid).status == "ready"
        assert kbd.check_respawn_guard(conn, tid) is None


# --- controls ----------------------------------------------------------------


def test_control_auth_failure_without_requeue_still_parks(kanban_home, clock):
    with kbc.connect() as conn:
        ready = _ready_after_auth(conn, clock, "no-requeue-ready")
        blocked = _blocked_by_auth(conn, clock, "no-requeue-blocked")
        _tick(clock, 3_600)
        assert kbd.check_respawn_guard(conn, ready) == "blocker_auth"
        assert kbd.check_respawn_guard(conn, blocked) == "blocker_auth"


def test_control_unblock_task_still_clears(kanban_home, clock):
    with kbc.connect() as conn:
        tid = _blocked_by_auth(conn, clock, "unblock")
        assert kb.unblock_task(conn, tid)
        assert kb.get_task(conn, tid).status == "ready"
        assert kbd.check_respawn_guard(conn, tid) is None


def test_control_fresh_auth_failure_after_requeue_parks_again(kanban_home, clock):
    """The requeue grants ONE fresh attempt: the breaker counter is kept, and a
    still-broken credential parks the card again."""
    with kbc.connect() as conn:
        tid = _blocked_by_auth(conn, clock, "fail-again")
        assert kb.promote_task(conn, tid, actor="operator") == (True, None)
        assert kb.get_task(conn, tid).consecutive_failures == 1
        _tick(clock)
        assert kb.claim_task(conn, tid) is not None
        _tick(clock)
        _auth_fail(conn, tid)  # the kept counter may trip the breaker here; either way it parks
        assert kb.get_task(conn, tid).consecutive_failures == 2
        assert kbd.check_respawn_guard(conn, tid) == "blocker_auth"


def test_ready_auth_failure_review_handoff_clears_latch(kanban_home, clock, dashboard):
    """``request_review`` (dashboard PATCH status=review with a new assignee): the
    reviewer is a fresh profile and must get its attempt; the counter stays."""
    with kbc.connect() as conn:
        tid = _ready_after_auth(conn, clock, "review handoff")
    r = dashboard.patch(f"/api/plugins/kanban/tasks/{tid}",
                        json={"status": "review", "assignee": "rev", "summary": "external implementation ready"})
    assert r.status_code == 200, r.text
    with kbc.connect() as conn:
        task = kb.get_task(conn, tid)
        assert (task.status, task.assignee, task.consecutive_failures) == ("review", "rev", 1)
        assert task.last_failure_error is None
        assert kbd.check_respawn_guard(conn, tid, lane="review") is None


def test_dependency_unlink_requeues_auth_parked_todo(kanban_home, clock):
    """A gated child keeps its stamp while ``todo``; the unlink that makes it
    ``ready`` again is a requeue and clears it (counter kept)."""
    with kbc.connect() as conn:
        child = _ready_after_auth(conn, clock, "gated child")
        parent = kb.create_task(conn, title="unfinished parent", assignee="a")
        assert kb.link_tasks(conn, parent, child)
        kb.recompute_ready(conn)
        task = kb.get_task(conn, child)
        assert (task.status, task.last_failure_error, task.consecutive_failures) == ("todo", AUTH_401, 1)
        _tick(clock)
        assert kb.unlink_tasks(conn, parent, child)
        task = kb.get_task(conn, child)
        assert (task.status, task.last_failure_error, task.consecutive_failures) == ("ready", None, 1)
        assert kbd.check_respawn_guard(conn, child) is None

