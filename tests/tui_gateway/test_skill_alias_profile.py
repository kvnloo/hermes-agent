"""Real installed skill aliases use the selected profile's config (#106063)."""

from pathlib import Path
from unittest.mock import Mock

from tui_gateway import server


def test_skill_alias_dispatches_real_profile_skill(tmp_path, monkeypatch):
    launch = tmp_path / "launch"
    launch.mkdir()
    selected = tmp_path / "selected"
    for home in (launch, selected):
        skill = home / "skills" / "research"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: research\ndescription: Compare alternatives.\n---\n\nUse this profile research checklist.\n",
            encoding="utf-8",
        )
        (home / "config.yaml").write_text(
            f"quick_commands:\n  {home.name}-review:\n    type: alias\n    target: /research preset\n", encoding="utf-8",
        )
    monkeypatch.setenv("HERMES_HOME", str(launch))
    monkeypatch.setattr(server, "_hermes_home", launch)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    initial_override = server.get_hermes_home_override()
    for home in (launch, selected, launch):
        worker = Mock()
        worker.run.side_effect = AssertionError("skill alias reached slash worker")
        sid = "real-skill-alias"
        monkeypatch.setitem(server._sessions, sid, {
            "session_key": sid, "profile_home": str(home), "cwd": str(tmp_path),
            "agent": None, "slash_worker": worker,
        })
        response = server.handle_request({
            "id": "alias", "method": "slash.exec", "params": {
                "command": f"{home.name}-review compare databases", "session_id": sid,
            },
        })
        assert "result" in response, response
        assert response["result"]["type"] == "skill", response
        assert "Use this profile research checklist." in response["result"]["message"]
        assert "preset compare databases" in response["result"]["message"]
        worker.run.assert_not_called()
        assert server.get_hermes_home_override() == initial_override
