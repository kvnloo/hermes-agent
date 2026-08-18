from __future__ import annotations

import subprocess
from pathlib import Path
import inspect
import sqlite3

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
    repo.mkdir(parents=True)
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
    run_id = kb.get_task(conn, task_id).current_run_id
    public = kb.get_review_capability(conn, task_id, expected_run_id=run_id)
    assert public is not None
    return {
        "expected_review_generation": public["review_generation"],
        "expected_review_nonce": public["review_nonce"],
        "expected_implementation_run_id": public["implementation_run_id"],
        "expected_source_commit": public["source_commit"],
        "expected_source_tree": public["source_tree"],
        "expected_source_hash": public["source_manifest_hash"],
        "expected_artifact_hash": public["artifact_manifest_hash"],
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
    review = kb.claim_review_task(conn, task_id, claimer="forged-reviewer-string")
    assert review is not None
    assert not kb.complete_task(
        conn, task_id, expected_run_id=review.current_run_id,
        **_claims(conn, task_id),
    )
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
    review = kb.claim_review_task(conn, task_id)
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


def test_reviewer_identity_is_not_caller_supplied():
    parameters = inspect.signature(kb.claim_review_task).parameters
    assert not {"actor", "principal", "credential_source"} & set(parameters)
    completion = inspect.signature(kb.complete_task).parameters
    assert not {"reviewer_actor", "reviewer_principal", "reviewer_credential_source"} & set(completion)


def test_ready_task_without_implementation_run_cannot_request_review(conn, tmp_path: Path):
    task_id = kb.create_task(conn, title="ready", assignee="builder",
                             workspace_kind="dir", workspace_path=str(tmp_path))
    assert kb.request_review(conn, task_id, reviewer="reviewer") is True
    assert kb.get_task(conn, task_id).status == "review"
    assert kb.complete_task(conn, task_id) is False


def _captain_token(conn, task_id: str, *, now: int = 100, **overrides):
    binding = conn.execute(
        "SELECT * FROM task_review_bindings WHERE task_id = ? ORDER BY generation DESC",
        (task_id,),
    ).fetchone()
    captain = kb.CaptainIdentity("telegram", "captain-7", "chat-9", "telegram-update")
    envelope_values = {
        "authenticated": True, "platform": "telegram", "operator_user_id": "captain-7",
        "chat_id": "chat-9", "message_id": f"message-{task_id}",
        "source": "telegram-update", "received_at": now,
    }
    envelope_values.update(overrides.pop("envelope", {}))
    values = {
        "task_id": task_id, "source_hash": binding["source_manifest_hash"],
        "artifact_hash": binding["artifact_manifest_hash"],
        "decision_generation": binding["generation"], "expires_at": now + 60,
    }
    values.update(overrides)
    return kb.issue_captain_approval_authorization(
        conn, envelope=kb.AuthenticatedCaptainEnvelope(**envelope_values),
        captain=captain, **values,
    )


def test_captain_product_approval_consumes_authenticated_receipt_once(conn, tmp_path):
    task_id, _ = _task(conn, tmp_path)
    token = _captain_token(conn, task_id)
    assert token
    assert kb.approve_task_by_captain(conn, task_id, authorization_token=token, now=101)
    assert not kb.approve_task_by_captain(conn, task_id, authorization_token=token, now=102)
    receipt = conn.execute("SELECT * FROM captain_approval_receipts").fetchone()
    assert receipt["task_id"] == task_id
    assert receipt["operation"] == "captain_product_approve"
    binding = conn.execute(
        "SELECT reviewed_at FROM task_review_bindings WHERE task_id = ?", (task_id,)
    ).fetchone()
    assert binding["reviewed_at"] is None
    event = [e for e in kb.list_events(conn, task_id) if e.kind == "captain_product_approved"][-1]
    assert event.payload["approval_class"] == "captain_product"


@pytest.mark.parametrize("envelope", [
    {"authenticated": False}, {"operator_user_id": "attacker"},
    {"chat_id": "wrong-chat"}, {"source": "request-body"},
])
def test_forged_or_unauthenticated_captain_envelope_is_denied(conn, tmp_path, envelope):
    task_id, _ = _task(conn, tmp_path)
    assert _captain_token(conn, task_id, envelope=envelope) is None


def test_captain_missing_expired_wrong_task_and_hash_are_denied(conn, tmp_path):
    first, _ = _task(conn, tmp_path / "one")
    second, _ = _task(conn, tmp_path / "two")
    assert not kb.approve_task_by_captain(conn, first, authorization_token="missing", now=101)
    expired = _captain_token(conn, first, now=200)
    assert not kb.approve_task_by_captain(conn, first, authorization_token=expired, now=260)
    wrong_task = _captain_token(conn, first, now=300,
                                envelope={"message_id": "wrong-task-token"})
    assert not kb.approve_task_by_captain(conn, second, authorization_token=wrong_task, now=301)
    wrong_hash = _captain_token(conn, first, now=400, source_hash="0" * 64,
                                envelope={"message_id": "wrong-hash-token"})
    assert not kb.approve_task_by_captain(conn, first, authorization_token=wrong_hash, now=401)


def test_transport_callback_binds_server_request_and_is_one_shot(conn, tmp_path):
    task_id, _ = _task(conn, tmp_path)
    nonce = kb.create_captain_approval_request(
        conn, task_id=task_id, platform="telegram", chat_id="chat-9",
        message_id="message-7", expires_at=200, now=100,
    )
    assert nonce
    claims = dict(
        callback_nonce=nonce, platform="telegram", operator_user_id="captain-7",
        chat_id="chat-9", message_id="message-7",
        allowed_user_ids={"captain-7"}, allowed_chat_ids={"chat-9"}, now=101,
    )
    assert kb.approve_captain_callback(conn, **claims)
    assert not kb.approve_captain_callback(conn, **claims)
    assert conn.execute("SELECT COUNT(*) FROM captain_approval_receipts").fetchone()[0] == 1


@pytest.mark.parametrize("field,value", [
    ("operator_user_id", "attacker"), ("chat_id", "other-chat"),
    ("message_id", "copied-message"), ("callback_nonce", "copied-nonce"),
])
def test_transport_callback_rejects_forged_update_fields(conn, tmp_path, field, value):
    task_id, _ = _task(conn, tmp_path)
    nonce = kb.create_captain_approval_request(
        conn, task_id=task_id, platform="telegram", chat_id="chat-9",
        message_id="message-7", expires_at=200, now=100,
    )
    claims = dict(
        callback_nonce=nonce, platform="telegram", operator_user_id="captain-7",
        chat_id="chat-9", message_id="message-7",
        allowed_user_ids={"captain-7"}, allowed_chat_ids={"chat-9"}, now=101,
    )
    claims[field] = value
    assert not kb.approve_captain_callback(conn, **claims)


def _pre_v2_connection(path: Path):
    db = sqlite3.connect(path, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE task_review_bindings (
            id INTEGER PRIMARY KEY, task_id TEXT, generation INTEGER, nonce TEXT,
            implementation_run_id INTEGER, implementation_profile TEXT,
            source_manifest TEXT, source_manifest_hash TEXT,
            artifact_manifest TEXT, artifact_manifest_hash TEXT, requested_at INTEGER
        );
        CREATE TABLE kanban_schema_migrations (
            name TEXT PRIMARY KEY, version INTEGER NOT NULL, applied_at INTEGER NOT NULL
        );
        INSERT INTO kanban_schema_migrations VALUES ('artifact_review_gate', 1, 1);
    """)
    return db


def test_pre_v2_migration_success_rollback_restart_and_idempotence(tmp_path):
    path = tmp_path / "legacy.db"
    db = _pre_v2_connection(path)
    db.execute("CREATE TRIGGER fail_version BEFORE UPDATE ON kanban_schema_migrations "
               "BEGIN SELECT RAISE(ABORT, 'injected migration failure'); END")
    db.close()
    with pytest.raises(sqlite3.IntegrityError):
        kb.connect(path)
    db = sqlite3.connect(path, isolation_level=None)
    db.row_factory = sqlite3.Row
    columns = {row["name"] for row in db.execute("PRAGMA table_info(task_review_bindings)")}
    assert "approval_class" not in columns
    assert db.execute("SELECT name FROM sqlite_master WHERE name='captain_approval_receipts'").fetchone() is None
    assert db.execute("SELECT version FROM kanban_schema_migrations").fetchone()[0] == 1
    db.execute("DROP TRIGGER fail_version")
    db.close()

    retry = kb.connect(path)
    retry.close()
    kb.init_db(path)
    retry = kb.connect(path)
    assert retry.execute("SELECT version FROM kanban_schema_migrations").fetchone()[0] == kb._ARTIFACT_REVIEW_GATE_SCHEMA_VERSION
    assert retry.execute("SELECT name FROM sqlite_master WHERE name='captain_approval_receipts'").fetchone()
    retry.close()


def test_pre_v2_concurrent_first_open_and_production_sentinel(tmp_path):
    path = tmp_path / "legacy-concurrent.db"
    _pre_v2_connection(path).close()
    script = (
        "from pathlib import Path; from hermes_cli import kanban_db as k; "
        f"c=k.connect(Path({str(path)!r})); c.close()"
    )
    processes = [subprocess.Popen(["python", "-c", script]) for _ in range(2)]
    assert [process.wait(timeout=30) for process in processes] == [0, 0]
    db = kb.connect(path)
    assert db.execute(
        "SELECT version FROM kanban_schema_migrations WHERE name='artifact_review_gate'"
    ).fetchone()[0] == kb._ARTIFACT_REVIEW_GATE_SCHEMA_VERSION
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    db.close()
