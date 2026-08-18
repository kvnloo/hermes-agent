from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture
def conn(tmp_path: Path):
    db = kb.connect(tmp_path / "kanban.db")
    try:
        yield db
    finally:
        db.close()


def _task(conn, tmp_path: Path, *, reviewer: str = "reviewer"):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "source.txt").write_text("v1", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "source.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
    task_id = kb.create_task(
        conn, title="bound review", assignee="builder",
        workspace_kind="dir", workspace_path=str(repo),
    )
    implementation = kb.claim_task(conn, task_id)
    assert implementation is not None
    assert kb.request_review(
        conn, task_id, reviewer=reviewer,
        expected_run_id=implementation.current_run_id,
    )
    return task_id, repo


def test_valid_independent_exact_binding_approves(conn, tmp_path: Path):
    task_id, _ = _task(conn, tmp_path)
    review = kb.claim_review_task(conn, task_id)
    assert review is not None
    assert kb.complete_task(conn, task_id, expected_run_id=review.current_run_id)
    binding = conn.execute(
        "SELECT reviewed_at FROM task_review_bindings WHERE task_id = ?", (task_id,)
    ).fetchone()
    assert binding["reviewed_at"] is not None


def test_self_review_is_denied_by_persisted_profiles(conn, tmp_path: Path):
    task_id, _ = _task(conn, tmp_path, reviewer="builder")
    assert kb.claim_review_task(conn, task_id, claimer="forged-reviewer-string") is None
    event = kb.list_events(conn, task_id)[-1]
    assert event.kind == "review_approval_denied"
    assert event.payload == {"reason": "self_review"}


def test_stale_source_actual_completion_api_denies_durably(conn, tmp_path: Path):
    task_id, repo = _task(conn, tmp_path)
    review = kb.claim_review_task(conn, task_id)
    assert review is not None
    (repo / "source.txt").write_text("tampered", encoding="utf-8")
    assert not kb.complete_task(conn, task_id, expected_run_id=review.current_run_id)
    assert kb.get_task(conn, task_id).status == "running"
    event = kb.list_events(conn, task_id)[-1]
    assert event.kind == "review_approval_denied"
    assert event.payload == {"reason": "stale_source_hash"}


def test_changes_invalidate_generation_and_rereview_mints_next(conn, tmp_path: Path):
    task_id, _ = _task(conn, tmp_path)
    review = kb.claim_review_task(conn, task_id)
    assert review is not None
    assert kb.request_changes(
        conn, task_id, reason="rework", expected_run_id=review.current_run_id
    ) == (True, "builder")
    old = conn.execute(
        "SELECT generation, invalidated_at FROM task_review_bindings WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    assert old["generation"] == 1 and old["invalidated_at"] is not None
    implementation = kb.claim_task(conn, task_id)
    assert implementation is not None
    assert kb.request_review(
        conn, task_id, reviewer="reviewer",
        expected_run_id=implementation.current_run_id,
    )
    generations = conn.execute(
        "SELECT generation FROM task_review_bindings WHERE task_id = ? ORDER BY generation",
        (task_id,),
    ).fetchall()
    assert [row["generation"] for row in generations] == [1, 2]
