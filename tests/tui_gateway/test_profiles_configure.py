"""profiles.describe / profiles.configure use the MCP ``enabled`` key the runtime reads.

Every runtime resolver (``enabled_mcp_server_names``, coding_context, oneshot, the gateway's
tool-name resolver) keys an MCP server's on/off state off ``mcp_servers.<name>.enabled``. The
profile editor used to read and write a separate ``disabled`` key, so a server toggled off in
the editor stayed live at runtime and a server with ``enabled: false`` showed as on.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import hermes_yaml as yaml

import tui_gateway.server as server


@pytest.fixture
def profile_dir(tmp_path, monkeypatch) -> Path:
    """A temp HERMES_HOME root with one named profile, ``bot``, at ``<root>/profiles/bot``."""
    root = tmp_path / "hermes_home"
    path = root / "profiles" / "bot"
    path.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(root))
    return path


def _write_mcp(profile_dir: Path, servers: dict) -> None:
    (profile_dir / "config.yaml").write_text(yaml.safe_dump({"mcp_servers": servers}), encoding="utf-8")


def _read_mcp(profile_dir: Path) -> dict:
    return yaml.safe_load((profile_dir / "config.yaml").read_text(encoding="utf-8"))["mcp_servers"]


def _call(method: str, params: dict) -> dict:
    resp = server._methods[method](1, {"name": "bot", **params})
    assert "error" not in resp, resp.get("error")
    return resp["result"]


def _described() -> dict:
    return {s["name"]: s["enabled"] for s in _call("profiles.describe", {})["mcp_servers"]}


def _write_skill(profile_dir: Path, name: str, *, frontmatter_name: str | None = None) -> None:
    target = profile_dir / "skills" / name
    target.mkdir(parents=True, exist_ok=True)
    skill_name = frontmatter_name or name
    (target / "SKILL.md").write_text(
        f"---\nname: {skill_name}\ndescription: test skill\n---\n\n# {skill_name}\n",
        encoding="utf-8",
    )


def _read_config(profile_dir: Path) -> dict:
    path = profile_dir / "config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_configure_skill_checklist_edits_allowlist_directly(profile_dir):
    _write_skill(profile_dir, "notes")
    (profile_dir / "config.yaml").write_text(
        "skills:\n  enabled: []\n  disabled: []\n", encoding="utf-8"
    )

    _call("profiles.configure", {"disabled_skills": []})
    cfg = _read_config(profile_dir)
    assert cfg["skills"]["enabled"] == ["notes"]
    assert cfg["skills"]["disabled"] == []

    _call("profiles.configure", {"disabled_skills": ["notes"]})
    cfg = _read_config(profile_dir)
    assert cfg["skills"]["enabled"] == []
    assert cfg["skills"]["disabled"] == []


def _disabled_in_snapshot() -> list[str]:
    """Mirror the actual Desktop editor: save the names profiles.describe sent."""
    return [s["name"] for s in _call("profiles.describe", {})["skills"] if not s["enabled"]]


def test_profile_editor_frontmatter_identity_hidden_noop_save(profile_dir):
    _write_skill(profile_dir, "dir-name-x", frontmatter_name="front-name-x")
    config_path = profile_dir / "config.yaml"
    config_path.write_text("skills:\\n  enabled: [git]\\n  disabled: []\\n", encoding="utf-8")

    snapshot = _call("profiles.describe", {})["skills"]
    assert {"name": "front-name-x", "enabled": False, "locked": False} in snapshot
    assert not any(s["name"] == "dir-name-x" for s in snapshot)
    before = config_path.read_bytes()

    result = _call("profiles.configure", {"disabled_skills": _disabled_in_snapshot()})
    assert result["applied"]["skills"] is True
    assert config_path.read_bytes() == before
    assert _read_config(profile_dir)["skills"] == {"enabled": ["git"], "disabled": []}


@pytest.mark.parametrize("allow_name,expected_enabled,expected_disabled", [
    ("front-name-x", [], []),            # exact frontmatter entry removed
    ("dir-name-x", ["dir-name-x"], ["front-name-x"]),  # folder alias requires an exception
])
def test_profile_editor_can_disable_allowed_frontmatter_alias(
    profile_dir, allow_name, expected_enabled, expected_disabled
):
    _write_skill(profile_dir, "dir-name-x", frontmatter_name="front-name-x")
    config_path = profile_dir / "config.yaml"
    config_path.write_text(
        f"skills:\\n  enabled: [{allow_name}]\\n  disabled: []\\n", encoding="utf-8"
    )
    snapshot = _call("profiles.describe", {})["skills"]
    assert any(s["name"] == "front-name-x" and s["enabled"] for s in snapshot)
    disabled = [s["name"] for s in snapshot if not s["enabled"]] + ["front-name-x"]

    result = _call("profiles.configure", {"disabled_skills": disabled})
    assert result["applied"]["skills"] is True
    assert _read_config(profile_dir)["skills"]["enabled"] == expected_enabled
    assert _read_config(profile_dir)["skills"]["disabled"] == expected_disabled
    after = _call("profiles.describe", {})["skills"]
    assert any(s["name"] == "front-name-x" and not s["enabled"] for s in after)


def test_profile_editor_external_dirs_filter_noop_save(profile_dir):
    shared = profile_dir.parent / "shared-library"
    filtered = shared / "filtered-dir"
    filtered.mkdir(parents=True)
    (filtered / "SKILL.md").write_text(
        "---\\nname: filtered-front\\ndescription: external\\n---\\nBody\\n", encoding="utf-8"
    )
    config_path = profile_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump({"skills": {
        "enabled": ["git"], "disabled": [],
        "external_dirs": [{"path": str(shared), "exclude": ["filtered-dir"]}],
    }}), encoding="utf-8")
    from agent.skill_utils import _external_dirs_cache_clear
    _external_dirs_cache_clear()
    snapshot = _call("profiles.describe", {})["skills"]
    assert any(s["name"] == "filtered-front" and not s["enabled"] for s in snapshot)
    before = config_path.read_bytes()
    result = _call("profiles.configure", {"disabled_skills": _disabled_in_snapshot()})
    assert result["applied"]["skills"] is True
    assert config_path.read_bytes() == before
    assert _read_config(profile_dir)["skills"]["disabled"] == []


def test_describe_matches_the_runtime_once_legacy_disabled_is_migrated(profile_dir):
    """Describe reads ``enabled``; a legacy ``disabled: true`` reads as off, and the config
    migration turns it into the ``enabled: false`` the runtime resolver honours."""
    from hermes_cli.config_migrations import run_migrations
    from hermes_cli.tools_config import enabled_mcp_server_names
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override

    _write_mcp(profile_dir, {
        "on": {"command": "on", "enabled": True},
        "off": {"command": "off", "enabled": False},
        # `hermes mcp add` writes `enabled: true`; the old editor then only added `disabled: true`.
        "legacy-off": {"command": "legacy", "enabled": True, "disabled": True},
        "implicit-on": {"command": "implicit"},
    })
    expected = {"on": True, "off": False, "legacy-off": False, "implicit-on": True}
    assert _described() == expected

    token = set_hermes_home_override(profile_dir)
    try:
        run_migrations(45, {"env_added": [], "config_added": [], "warnings": []}, quiet=True)
    finally:
        reset_hermes_home_override(token)

    live = enabled_mcp_server_names({"mcp_servers": _read_mcp(profile_dir)})
    assert {name: name in live for name in expected} == expected == _described()


def test_configure_toggle_is_what_the_runtime_resolver_and_describe_see(profile_dir):
    from hermes_cli.tools_config import enabled_mcp_server_names

    _write_mcp(profile_dir, {
        "keep": {"command": "keep", "enabled": False},
        "drop": {"command": "drop"},
        "legacy": {"command": "legacy", "disabled": True},
    })

    _call("profiles.configure", {"enabled_mcp_servers": ["keep", "legacy"]})

    on_disk = _read_mcp(profile_dir)
    assert not any("disabled" in entry for entry in on_disk.values())
    assert enabled_mcp_server_names({"mcp_servers": on_disk}) == {"keep", "legacy"}
    assert _described() == {"keep": True, "drop": False, "legacy": True}
