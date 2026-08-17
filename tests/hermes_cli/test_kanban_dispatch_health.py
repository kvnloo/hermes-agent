from __future__ import annotations

import time
from pathlib import Path

from hermes_cli import kanban_db as kb


def test_missing_reviewer_profile_persists_reason_and_coalesces_sla(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes_cli import profiles

    monkeypatch.setattr(profiles, "profile_exists", lambda _name: False)
    with kb.connect(db_path=tmp_path / "missing.db") as conn:
        task_id = kb.create_task(conn, title="review", assignee="reviewer")
        old = int(time.time()) - kb.DEFAULT_CLAIM_SLA_SECONDS - 10
        conn.execute(
            "UPDATE tasks SET ready_since = ? WHERE id = ?", (old, task_id)
        )

        first = kb.dispatch_once(conn, spawn_fn=lambda *_args: 1)
        task = kb.get_task(conn, task_id)
        assert task is not None
        assert task.status == "ready"
        assert task.dispatch_reason == "nonspawnable_profile"
        assert task.dispatch_attempt_count == 1
        assert task.last_considered_at is not None
        assert first.claim_sla_breached == [
            (task_id, "nonspawnable_profile", kb.DEFAULT_CLAIM_SLA_SECONDS + 10)
        ]

        second = kb.dispatch_once(conn, spawn_fn=lambda *_args: 1)
        task = kb.get_task(conn, task_id)
        assert task is not None
        assert task.dispatch_attempt_count == 2
        assert second.claim_sla_breached == []
        events = [e for e in kb.list_events(conn, task_id) if e.kind == "dispatch_claim_sla"]
        assert len(events) == 1


def test_poison_head_does_not_prevent_dispatchable_reviewer_canary(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes_cli import profiles

    monkeypatch.setattr(profiles, "profile_exists", lambda name: name == "reviewer")
    spawned: list[str] = []

    def spawn(task, _workspace):
        spawned.append(task.id)
        return 4242

    with kb.connect(db_path=tmp_path / "poison.db") as conn:
        poison = kb.create_task(conn, title="bad lane", assignee="missing", priority=100)
        canary = kb.create_task(conn, title="reviewer no-op canary", assignee="reviewer")
        result = kb.dispatch_once(conn, spawn_fn=spawn)

        assert result.skipped_nonspawnable == [poison]
        assert spawned == [canary]
        poison_task = kb.get_task(conn, poison)
        assert poison_task is not None
        assert poison_task.dispatch_reason == "nonspawnable_profile"
        claimed = kb.get_task(conn, canary)
        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.dispatch_reason == "claimable"
        assert kb.complete_task(conn, canary, expected_run_id=claimed.current_run_id)
        completed = kb.get_task(conn, canary)
        assert completed is not None
        assert completed.status == "done"


def test_global_capacity_records_every_ready_task_without_claiming(
    tmp_path: Path, all_assignees_spawnable
) -> None:
    with kb.connect(db_path=tmp_path / "capacity.db") as conn:
        running_id = kb.create_task(conn, title="running", assignee="worker")
        assert kb.claim_task(conn, running_id) is not None
        waiting = [
            kb.create_task(conn, title=f"waiting {index}", assignee="reviewer")
            for index in range(2)
        ]

        result = kb.dispatch_once(conn, max_in_progress=1, spawn_fn=lambda *_args: 1)
        assert result.spawned == []
        for task_id in waiting:
            task = kb.get_task(conn, task_id)
            assert task is not None
            assert task.status == "ready"
            assert task.dispatch_reason == "global_capacity"
            assert task.dispatch_attempt_count == 1
