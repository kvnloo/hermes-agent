from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


def test_worker_route_preflight_uses_profile_scoped_runtime_resolver(tmp_path, monkeypatch):
    import hermes_cli.runtime_provider as runtime_provider
    from hermes_cli.kanban_db import _preflight_worker_route
    from hermes_constants import get_hermes_home

    profile_home = tmp_path / "profiles" / "worker"
    profile_home.mkdir(parents=True)
    seen = {}

    def resolve(*, requested, target_model):
        seen["provider"] = requested
        seen["model"] = target_model
        seen["home"] = get_hermes_home()
        return {"provider": requested, "api_key": "synthetic"}

    monkeypatch.setattr(runtime_provider, "resolve_runtime_provider", resolve)
    task = SimpleNamespace(provider_override="xai-oauth", model_override="grok-code-fast-1")

    _preflight_worker_route(task, profile_home)

    assert seen == {
        "provider": "xai-oauth",
        "model": "grok-code-fast-1",
        "home": profile_home,
    }


def test_worker_route_preflight_gives_profile_provider_and_model_guidance(tmp_path, monkeypatch):
    import hermes_cli.runtime_provider as runtime_provider
    from hermes_cli.auth import AuthError
    from hermes_cli.kanban_db import _preflight_worker_route

    def reject(**_kwargs):
        raise AuthError("missing credential", provider="xai-oauth", code="missing")

    monkeypatch.setattr(runtime_provider, "resolve_runtime_provider", reject)
    task = SimpleNamespace(
        assignee="worker",
        provider_override="xai-oauth",
        model_override="grok-code-fast-1",
    )

    with pytest.raises(RuntimeError) as exc_info:
        _preflight_worker_route(task, tmp_path)

    message = str(exc_info.value)
    assert "worker" in message
    assert "xai-oauth" in message
    assert "grok-code-fast-1" in message
    assert "hermes -p worker auth login xai-oauth" in message


def _prepare_dispatch(monkeypatch, tmp_path, kb):
    root = tmp_path / ".hermes"
    root.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(root))
    monkeypatch.setattr(kb, "_memory_pressure_level", lambda: "ok")
    monkeypatch.setattr(kb, "_resolve_hermes_argv", lambda: ["hermes"])
    monkeypatch.setattr(kb, "_retag_legacy_worker_sessions", lambda _root: None)


def test_dispatcher_blocks_real_pinned_auth_failure_after_one_attempt(tmp_path, monkeypatch):
    import hermes_cli.kanban_db as kb
    import hermes_cli.runtime_provider as runtime_provider
    from hermes_cli.auth import AuthError

    _prepare_dispatch(monkeypatch, tmp_path, kb)

    def reject(**_kwargs):
        raise AuthError("missing credential", provider="xai-oauth", code="missing")

    monkeypatch.setattr(runtime_provider, "resolve_runtime_provider", reject)
    db_path = tmp_path / "kanban.db"
    conn = kb.connect(db_path=db_path)
    try:
        task_id = kb.create_task(
            conn,
            title="pinned",
            assignee="default",
            workspace_kind="dir",
            workspace_path=str(tmp_path),
            provider_override="xai-oauth",
            model_override="grok-code-fast-1",
        )

        result = kb.dispatch_once(
            conn,
            failure_limit=3,
            reconcile_orphans=False,
        )

        task = kb.get_task(conn, task_id)
        assert task is not None
        assert result.auto_blocked == [task_id]
        assert task.status == "blocked"
        assert task.consecutive_failures == 1
    finally:
        conn.close()


@pytest.mark.parametrize(
    "failure",
    [
        OSError("auth store temporarily locked"),
        pytest.param(
            ("qwen_auth_read_failed", "failed to read credential store"),
            id="typed-auth-store-read-failure",
        ),
    ],
)
def test_dispatcher_does_not_immediately_block_unexpected_resolver_failure(
    tmp_path, monkeypatch, failure
):
    import hermes_cli.kanban_db as kb
    import hermes_cli.runtime_provider as runtime_provider
    from hermes_cli.auth import AuthError

    _prepare_dispatch(monkeypatch, tmp_path, kb)

    def reject(**_kwargs):
        if isinstance(failure, tuple):
            code, message = failure
            raise AuthError(message, provider="qwen-oauth", code=code)
        raise failure

    monkeypatch.setattr(runtime_provider, "resolve_runtime_provider", reject)
    conn = kb.connect(db_path=tmp_path / "kanban.db")
    try:
        task_id = kb.create_task(
            conn,
            title="pinned",
            assignee="default",
            workspace_kind="dir",
            workspace_path=str(tmp_path),
            provider_override="xai-oauth",
            model_override="grok-code-fast-1",
        )

        result = kb.dispatch_once(
            conn,
            failure_limit=3,
            reconcile_orphans=False,
        )

        task = kb.get_task(conn, task_id)
        assert task is not None
        assert result.auto_blocked == []
        assert task.status != "blocked"
        assert task.consecutive_failures == 1
        expected = failure[1] if isinstance(failure, tuple) else str(failure)
        assert task.last_failure_error == expected
    finally:
        conn.close()


@pytest.mark.parametrize("provider", [None, ""])
def test_default_spawn_unpinned_worker_skips_credential_resolution(
    tmp_path, monkeypatch, provider
):
    import hermes_cli.kanban_db as kb
    import hermes_cli.runtime_provider as runtime_provider

    _prepare_dispatch(monkeypatch, tmp_path, kb)
    monkeypatch.setattr(
        runtime_provider,
        "resolve_runtime_provider",
        lambda **_kwargs: pytest.fail("unpinned worker resolved credentials"),
    )

    class FakeProc:
        pid = 42

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: FakeProc())
    task = kb.Task(
        id="t_unpinned",
        title="unpinned",
        body=None,
        assignee="default",
        status="running",
        priority=0,
        created_by="test",
        created_at=1,
        started_at=None,
        completed_at=None,
        workspace_kind="dir",
        workspace_path=str(tmp_path),
        claim_lock="lock",
        claim_expires=None,
        tenant=None,
        provider_override=provider,
    )

    assert kb._default_spawn(task, str(tmp_path)) == 42


def test_dispatch_dry_run_skips_pinned_credential_resolution(tmp_path, monkeypatch):
    import hermes_cli.kanban_db as kb
    import hermes_cli.runtime_provider as runtime_provider

    _prepare_dispatch(monkeypatch, tmp_path, kb)
    monkeypatch.setattr(
        runtime_provider,
        "resolve_runtime_provider",
        lambda **_kwargs: pytest.fail("dry run resolved credentials"),
    )
    conn = kb.connect(db_path=tmp_path / "kanban.db")
    try:
        task_id = kb.create_task(
            conn,
            title="pinned dry run",
            assignee="default",
            workspace_kind="dir",
            workspace_path=str(tmp_path),
            provider_override="xai-oauth",
            model_override="grok-code-fast-1",
        )

        result = kb.dispatch_once(conn, dry_run=True, reconcile_orphans=False)

        assert [item[0] for item in result.spawned] == [task_id]
    finally:
        conn.close()
