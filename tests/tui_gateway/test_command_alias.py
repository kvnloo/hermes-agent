"""Original PR #106088 alias routing and argument contracts, moved for file-size policy."""

from unittest.mock import Mock

from tui_gateway import server
from tui_gateway.command_alias import alias_skill_target


def test_slash_exec_routes_quick_command_alias_to_skill(monkeypatch):
    """A quick-command alias whose target is a skill must reach command.dispatch,
    not the slash worker. On the worker path the CLI queues the loaded skill onto
    _pending_input, which only the interactive REPL drains, so it is silently
    dropped on desktop/TUI (#106063)."""
    import agent.skill_commands as sc_mod

    sid = "test-alias-skill"
    worker = Mock()
    worker.run.side_effect = AssertionError("skill alias reached slash worker")
    monkeypatch.setitem(server._sessions, sid, {"session_key": sid, "agent": None, "slash_worker": worker})

    monkeypatch.setattr(
        server, "_load_cfg",
        lambda: {"quick_commands": {"tr": {"type": "alias", "target": "/trading-tr-hermes"}}},
    )
    fake_cmds = {"/trading-tr-hermes": {"name": "trading-tr-hermes", "description": "Trading skill"}}
    monkeypatch.setattr(sc_mod, "get_skill_commands", lambda: fake_cmds)
    monkeypatch.setattr(sc_mod, "scan_skill_commands", lambda: fake_cmds)
    monkeypatch.setattr(
        sc_mod, "build_skill_invocation_message",
        lambda key, arg, task_id="": f"[IMPORTANT: run {key.lstrip('/')}] {arg}".strip(),
    )

    resp = server.handle_request({
        "id": "r1",
        "method": "slash.exec",
        "params": {"command": "tr EURUSD", "session_id": sid},
    })

    assert "error" not in resp, resp
    result = resp["result"]
    assert result["type"] == "skill"
    assert result["name"] == "trading-tr-hermes"
    # The user's argument reaches the resolved skill.
    assert "EURUSD" in result["message"]
    worker.run.assert_not_called()


def test_alias_skill_target_resolution(monkeypatch):
    """alias_skill_target resolves only alias→skill, prepends the target's own
    args, and returns None for non-alias / exec / non-skill targets."""
    import agent.skill_commands as sc_mod

    session = {"session_key": "s", "agent": None}
    cfg = {"quick_commands": {
        "tr": {"type": "alias", "target": "/trading-tr-hermes preset"},
        "sh": {"type": "alias", "target": "/some-helper"},
        "run": {"type": "exec", "command": "echo hi"},
    }}
    monkeypatch.setattr(server, "_load_cfg", lambda: cfg)
    # Only /trading-tr-hermes is a skill; /some-helper is not.
    monkeypatch.setattr(
        sc_mod, "get_skill_commands",
        lambda: {"/trading-tr-hermes": {"name": "trading-tr-hermes"}},
    )

    def is_skill(name):
        return server._profile_skill_command(session, name)

    # alias→skill: target's embedded arg is prepended to the user arg.
    assert alias_skill_target(server._load_cfg(), "tr", "EURUSD", is_skill) == ("trading-tr-hermes", "preset EURUSD")
    # alias→skill with no user arg keeps just the target's embedded arg.
    assert alias_skill_target(server._load_cfg(), "tr", "", is_skill) == ("trading-tr-hermes", "preset")
    # alias whose target is not a skill → None (worker/plugin path unchanged).
    assert alias_skill_target(server._load_cfg(), "sh", "", is_skill) is None
    # exec-type quick command → None.
    assert alias_skill_target(server._load_cfg(), "run", "", is_skill) is None
    # unknown base → None.
    assert alias_skill_target(server._load_cfg(), "nope", "", is_skill) is None
