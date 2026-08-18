import sqlite3
import threading
import time

import pytest

from hermes_cli import kanban_db as kb


def _source(key: str):
    return {
        "source_key": key,
        "trigger_id": "test-tick",
        "trigger_type": "test",
        "destination": "isolated",
        "policy_generation": "g1",
        "policy_snapshot": {"focused": True, "max_spawn": 1},
        "candidate_action": "dispatch_tick",
        "causal_refs": ["event:1"],
    }


def test_dispatch_records_source_before_no_task_decision_and_survives_restart(tmp_path):
    path = tmp_path / "board.db"
    conn = kb.connect(path)
    result = kb.dispatch_once(conn, spawn_fn=lambda *_: 1, wake_source=_source("wake:empty"))
    assert result.spawned == []
    row = conn.execute("SELECT * FROM proactive_wakes").fetchone()
    assert row["outcome"] == "suppressed"
    assert row["completed_at"] >= row["triggered_at"]
    conn.close()

    reopened = kb.connect(path)
    persisted = reopened.execute("SELECT source_key,outcome FROM proactive_wakes").fetchone()
    assert tuple(persisted) == ("wake:empty", "suppressed")
    reopened.close()


def test_replay_is_idempotent_and_does_not_spawn_twice(tmp_path, monkeypatch):
    conn = kb.connect(tmp_path / "board.db")
    monkeypatch.setattr("hermes_cli.profiles.profile_exists", lambda _name: True)
    task_id = kb.create_task(conn, title="work", assignee="worker")
    conn.execute("UPDATE tasks SET status='ready' WHERE id=?", (task_id,))
    calls = []
    first = kb.dispatch_once(conn, spawn_fn=lambda *_: calls.append(1) or 42, wake_source=_source("wake:one"))
    second = kb.dispatch_once(conn, spawn_fn=lambda *_: calls.append(2) or 43, wake_source=_source("wake:one"))
    assert len(first.spawned) == 1
    assert second.spawned == []
    assert calls == [1]
    assert conn.execute("SELECT COUNT(*) FROM proactive_wakes").fetchone()[0] == 1
    wake = conn.execute("SELECT outcome,duplicate_count FROM proactive_wakes").fetchone()
    assert tuple(wake) == ("created", 1)
    attempt = conn.execute("SELECT task_id,run_id,outcome,reason FROM proactive_dispatch_attempts").fetchone()
    assert attempt[0] is not None and attempt[1] is not None
    assert tuple(attempt)[2:] == ("created", "claimable")


def test_concurrent_source_insert_coalesces(tmp_path):
    path = tmp_path / "board.db"
    kb.init_db(path)
    barrier = threading.Barrier(2)
    results = []

    def insert():
        conn = kb.connect(path)
        barrier.wait()
        results.append(kb.begin_proactive_wake(conn, **_source("wake:race"))[1])
        conn.close()

    threads = [threading.Thread(target=insert) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(results) == [False, True]
    conn = kb.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM proactive_wakes").fetchone()[0] == 1


def test_closed_enums_and_foreign_keys_reject_invalid_rows(tmp_path):
    conn = kb.connect(tmp_path / "board.db")
    with pytest.raises(ValueError):
        kb.begin_proactive_wake(conn, **{**_source("bad"), "trigger_type": "unknown"})
    wake_id, _ = kb.begin_proactive_wake(conn, **_source("valid"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO proactive_dispatch_attempts "
            "(wake_id,task_id,outcome,reason,created_at) VALUES (?,?,?,?,?)",
            (wake_id, "dangling", "deferred", "parent_gated", int(time.time())),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE proactive_wakes SET outcome='invented' WHERE id=?", (wake_id,))


def test_every_closed_reason_can_be_observed_without_a_task(tmp_path):
    conn = kb.connect(tmp_path / "board.db")
    observed = set()
    for outcome in kb.PROACTIVE_WAKE_OUTCOMES:
        wake_id, _ = kb.begin_proactive_wake(conn, **_source(f"reason:{outcome}"))
        kb.record_proactive_decision(
            conn, wake_id, outcome=outcome, reason=f"observed:{outcome}",
            detail="bounded diagnostic",
        )
        observed.add(conn.execute(
            "SELECT outcome FROM proactive_dispatch_attempts WHERE wake_id=?", (wake_id,)
        ).fetchone()[0])
    assert observed == kb.PROACTIVE_WAKE_OUTCOMES


def test_compaction_preserves_count_and_hash_evidence(tmp_path):
    conn = kb.connect(tmp_path / "board.db")
    for key in ("old:1", "old:2"):
        wake_id, _ = kb.begin_proactive_wake(conn, **_source(key))
        kb.finish_proactive_wake(conn, wake_id, kb.DispatchResult())
    conn.execute("UPDATE proactive_wakes SET triggered_at=1")
    assert kb.compact_proactive_wakes(conn, before=2) == 2
    assert conn.execute("SELECT COUNT(*) FROM proactive_wakes").fetchone()[0] == 0
    rollup = conn.execute("SELECT count,evidence_hash FROM proactive_wake_rollups").fetchone()
    assert rollup[0] == 2 and len(rollup[1]) == 64
