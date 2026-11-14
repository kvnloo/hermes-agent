"""A token embedded in a source URL (``https://user:TOKEN@host/...``) never reaches install output."""
from __future__ import annotations

import pytest
from rich.console import Console

TOKEN = "s3cr3tTOKEN"


@pytest.mark.parametrize("url", [f"https://user:{TOKEN}@127.0.0.1:9/x/y.git", f"https://{TOKEN}@127.0.0.1:9/x/y.git"])
def test_plugin_install_failure_never_prints_the_url_token(tmp_path, monkeypatch, capsys, url):
    from hermes_cli.plugins_cmd import cmd_install

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    with pytest.raises(SystemExit):
        cmd_install(url)  # real git clone against a closed local port
    out = capsys.readouterr().out
    assert "Could not download the plugin from https://127.0.0.1:9/x/y.git" in out
    assert TOKEN not in out


def test_skills_hub_messages_never_print_the_url_token(tmp_path, monkeypatch):
    from hermes_cli.skills_hub import do_install, do_tap

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    console = Console(record=True, width=200)
    url = f"https://user:{TOKEN}@127.0.0.1:9/s/SKILL.md"
    do_install(url, console=console, source_id="url", skip_confirm=True)  # real fetch, closed port
    do_tap("add", url, console=console)
    out = console.export_text()
    assert "Could not download 'https://user:***@127.0.0.1:9/s/SKILL.md'" in out
    assert "Added tap: https://user:***@127.0.0.1:9/s/SKILL.md" in out
    assert TOKEN not in out


@pytest.mark.parametrize("skip_confirm", [True, False])
def test_unnamed_url_skill_never_prints_credentials(skip_confirm, monkeypatch):
    """Both the prompt and non-interactive refusal must mask credentials before a scan."""
    from hermes_cli import skills_hub
    from tools.skills_hub_models import SkillBundle

    url = f"https://user:{TOKEN}@127.0.0.1:9/SKILL.md"
    bundle = SkillBundle(
        name="", files={"SKILL.md": "# Untitled skill\n"}, source="url",
        identifier=url, trust_level="community",
        metadata={"url": url, "awaiting_name": True},
    )
    if not skip_confirm:
        monkeypatch.setattr(skills_hub, "_line_input", lambda _prompt: None)
    console = Console(record=True, width=240)

    assert skills_hub._resolve_url_bundle_name(
        console, bundle, None, url, name_override="", skip_confirm=skip_confirm
    ) is False
    output = console.export_text()
    assert "https://user:***@127.0.0.1:9/SKILL.md" in output
    assert TOKEN not in output
