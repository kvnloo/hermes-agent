from pathlib import Path
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


def test_dispatcher_blocks_preflight_failure_after_one_spawn_attempt(tmp_path, monkeypatch):
    import hermes_cli.kanban_db as kb

    monkeypatch.setattr(kb, "_memory_pressure_level", lambda: "ok")
    db_path = tmp_path / "kanban.db"
    conn = kb.connect(db_path=db_path)
    try:
        task_id = kb.create_task(
            conn,
            title="pinned",
            assignee="default",
            workspace_kind="dir",
            workspace_path=str(tmp_path),
        )

        def reject(*_args, **_kwargs):
            raise kb.WorkerPreflightError("profile 'default' lacks provider 'xai-oauth'")

        result = kb.dispatch_once(
            conn,
            spawn_fn=reject,
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
