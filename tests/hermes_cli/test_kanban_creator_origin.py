"""All explicit creator paths share durable lineage without graph coupling."""
import pytest


@pytest.mark.parametrize("surface", ["db", "builtin", "cli"])
def test_creator_origin_survives_without_dependency_parent(tmp_path, monkeypatch, capsys, surface):
    from hermes_cli import kanban_db as kb, kanban_db_connect as kbc, kanban_db_notify as kn
    from hermes_cli.kanban_db_graph import decompose_triage_task

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_KANBAN_TASK", raising=False)
    kb.init_db()
    with kbc.connect_closing() as conn:
        owner = kb.create_task(conn, title="owner", session_id="durable", triage=True)
        kn.add_notify_sub(conn, task_id=owner, platform="telegram", chat_id="chat",
                         delivery_mode="wake", notifier_profile="default")
        if surface == "builtin":
            tid = decompose_triage_task(conn, owner, root_assignee="default",
                                       children=[{"title": "child"}])[0]
        elif surface == "db":
            tid = kb.create_task(conn, title="child", creator_task_id=owner)
        else:
            import json
            import argparse
            from hermes_cli.kanban import kanban_command
            from hermes_cli.kanban_parser import build_parser
            parser = argparse.ArgumentParser()
            build_parser(parser.add_subparsers())
            monkeypatch.setenv("HERMES_KANBAN_TASK", owner)
            assert kanban_command(parser.parse_args(["kanban", "create", "child", "--json"])) == 0
            tid = json.loads(capsys.readouterr().out)["id"]
        assert kb.get_task(conn, tid).session_id == "durable"
        subs = kn.list_notify_subs(conn, tid)
        assert len(subs) == 1 and subs[0]["delivery_mode"] == "wake"
        assert not conn.execute("SELECT 1 FROM task_links WHERE child_id = ?", (tid,)).fetchone()
        # No ambient identity guessing in the storage API.
        plain = kb.create_task(conn, title="plain", session_id="explicit")
        assert kb.get_task(conn, plain).session_id == "explicit"
        assert not kn.list_notify_subs(conn, plain)


@pytest.mark.parametrize("env_session, worker, want", [
    ("chat-1", False, "chat-1"),   # card made from a chat's terminal carries that chat
    (None, False, None),           # plain shell: no session to stamp
    ("worker-run", True, "durable"),  # a worker's card keeps its creator's session, not its own
])
def test_cli_create_stamps_chat_session(tmp_path, monkeypatch, capsys, env_session, worker, want):
    import argparse
    import json
    from hermes_cli import kanban_db as kb, kanban_db_connect as kbc
    from hermes_cli.kanban import kanban_command
    from hermes_cli.kanban_parser import build_parser

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_KANBAN_TASK", raising=False)
    monkeypatch.delenv("HERMES_SESSION_ID", raising=False)
    kb.init_db()
    with kbc.connect_closing() as conn:
        owner = kb.create_task(conn, title="owner", session_id="durable", triage=True)
    if env_session:
        monkeypatch.setenv("HERMES_SESSION_ID", env_session)
    if worker:
        monkeypatch.setenv("HERMES_KANBAN_TASK", owner)
    parser = argparse.ArgumentParser()
    build_parser(parser.add_subparsers())
    assert kanban_command(parser.parse_args(["kanban", "create", "child", "--json"])) == 0
    tid = json.loads(capsys.readouterr().out)["id"]
    with kbc.connect_closing() as conn:
        assert kb.get_task(conn, tid).session_id == want
