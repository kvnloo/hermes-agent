"""Exact installed skill names stay canonical beside longer aliases (#133258)."""

from pathlib import Path

import pytest

from tui_gateway import server


@pytest.fixture
def skill_catalog(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    skill = home / "skills" / "research"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: research\ndescription: Compare alternatives.\n---\n\nUse the authored research checklist.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    sid = "canonical-skill-consumer"
    monkeypatch.setitem(server._sessions, sid, {
        "session_key": sid, "profile_home": str(home), "cwd": str(tmp_path), "agent": None,
    })

    def catalog(quick_name):
        (home / "config.yaml").write_text(
            f"quick_commands:\n  {quick_name}:\n    type: alias\n    target: /research\n",
            encoding="utf-8",
        )
        response = server.handle_request({
            "id": "catalog", "method": "commands.catalog", "params": {"session_id": sid},
        })
        assert "result" in response, response
        return response["result"], sid

    return catalog


def test_exact_skill_is_canonical_and_dispatches_its_body(skill_catalog):
    catalog, sid = skill_catalog("research-skill")
    assert "/research" in catalog["skills"]
    assert catalog["canon"].get("/research") == "/research"
    assert catalog["canon"]["/research-skill"] == "/research-skill"
    response = server.handle_request({
        "id": "dispatch", "method": "command.dispatch", "params": {
            "session_id": sid, "name": catalog["canon"]["/research"].lstrip("/"), "arg": "compare databases",
        },
    })
    assert response["result"]["type"] == "skill", response
    assert "Use the authored research checklist." in response["result"]["message"]
    assert "compare databases" in response["result"]["message"]


def test_skill_catalog_preserves_existing_canonical_command(skill_catalog):
    catalog, _ = skill_catalog("Research")
    assert "/research" in catalog["skills"]
    assert catalog["canon"]["/research"] == "/Research"
