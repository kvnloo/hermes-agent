from __future__ import annotations

import subprocess
from pathlib import Path
import json

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


def _claims(conn, task_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM task_review_bindings WHERE task_id = ? ORDER BY generation DESC",
        (task_id,),
    ).fetchone()
    source = json.loads(row["source_manifest"])
    return {
        "expected_review_generation": row["generation"],
        "expected_review_nonce": row["nonce"],
        "expected_implementation_run_id": row["implementation_run_id"],
        "expected_source_commit": source["commit"],
        "expected_source_tree": source["tree"],
        "expected_source_hash": row["source_manifest_hash"],
        "expected_artifact_hash": row["artifact_manifest_hash"],
        "reviewer_profile": row["reviewer_profile"],
        "reviewer_actor": row["reviewer_actor"],
        "reviewer_principal": row["reviewer_principal"],
        "reviewer_credential_source": row["reviewer_credential_source"],
    }


def test_valid_independent_exact_binding_approves(conn, tmp_path: Path):
    task_id, _ = _task(conn, tmp_path)
    review = kb.claim_review_task(conn, task_id)
    assert review is not None
    assert kb.complete_task(
        conn, task_id, expected_run_id=review.current_run_id, **_claims(conn, task_id)
    )
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
    assert not kb.complete_task(
        conn, task_id, expected_run_id=review.current_run_id, **_claims(conn, task_id)
    )
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


def test_missing_and_wrong_nonce_claims_fail_closed(conn, tmp_path: Path):
    task_id, _ = _task(conn, tmp_path)
    review = kb.claim_review_task(
        conn, task_id, actor="reviewer", principal="reviewer",
        credential_source="test-credential",
    )
    assert review is not None
    assert not kb.complete_task(conn, task_id, expected_run_id=review.current_run_id)
    assert kb.list_events(conn, task_id)[-1].payload == {
        "reason": "missing_exact_review_claims"
    }
    claims = _claims(conn, task_id)
    claims["expected_review_nonce"] = "0" * 48
    assert not kb.complete_task(
        conn, task_id, expected_run_id=review.current_run_id, **claims
    )
    assert kb.list_events(conn, task_id)[-1].payload == {
        "reason": "review_nonce_mismatch"
    }


def test_reclaimed_review_supersedes_generation_and_nonce(conn, tmp_path: Path):
    task_id, _ = _task(conn, tmp_path)
    first = kb.claim_review_task(conn, task_id)
    assert first is not None
    old = _claims(conn, task_id)
    assert kb.reclaim_task(conn, task_id)
    second = kb.claim_review_task(conn, task_id)
    assert second is not None
    new = _claims(conn, task_id)
    assert new["expected_review_generation"] == old["expected_review_generation"] + 1
    assert new["expected_review_nonce"] != old["expected_review_nonce"]
    assert not kb.complete_task(
        conn, task_id, expected_run_id=second.current_run_id, **old
    )


def test_review_migration_records_explicit_version(conn):
    row = conn.execute(
        "SELECT version FROM kanban_schema_migrations WHERE name = 'artifact_review_gate'"
    ).fetchone()
    assert row["version"] == kb._ARTIFACT_REVIEW_GATE_SCHEMA_VERSION
