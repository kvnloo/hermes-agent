"""`hermes doctor` Context Health: failures that otherwise only show up as a worse agent.

A configured context engine that does not resolve falls back to the built-in compressor with one
log line, so a session can run for days without the engine the user chose. A user engine whose
``register_context_engine`` sits past the discovery sniff (first 8 KiB of ``__init__.py``) is the
real-world way this happens: a long module docstring is enough.
"""

from __future__ import annotations

from hermes_cli.doctor_context import _check_context_health


def _home(tmp_path, monkeypatch, config: str):
    home = tmp_path / ".hermes"
    (home / "memories").mkdir(parents=True)
    (home / "config.yaml").write_text(config, encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr("hermes_cli.doctor_context._prompt_prefix_row", lambda: None)
    return home


def _engine(home, name: str, docstring_bytes: int):
    d = home / "plugins" / name
    d.mkdir(parents=True)
    (d / "__init__.py").write_text(
        f'"""{"x" * docstring_bytes}"""\n\ndef register(ctx):\n    ctx.register_context_engine(None)\n',
        encoding="utf-8",
    )


def test_engine_hidden_past_discovery_sniff_is_reported(tmp_path, monkeypatch, capsys):
    home = _home(tmp_path, monkeypatch, "context:\n  engine: longdoc\n")
    _engine(home, "longdoc", 9000)

    finding = _check_context_health(False)

    assert any(
        "context.engine 'longdoc' does not resolve" in i for i in finding.manual_issues
    )
    assert "silently use the built-in compressor" in capsys.readouterr().out


def test_discoverable_engine_and_default_compressor_are_clean(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch, "context:\n  engine: shortdoc\n")
    _engine(home, "shortdoc", 100)
    assert _check_context_health(False).manual_issues == []

    _home(tmp_path / "b", monkeypatch, "model: x\n")
    assert _check_context_health(False).manual_issues == []


def test_memory_near_its_char_limit_is_reported_before_writes_are_refused(
    tmp_path, monkeypatch, capsys
):
    home = _home(
        tmp_path,
        monkeypatch,
        "memory:\n  memory_char_limit: 100\n  user_char_limit: 100\n",
    )
    (home / "memories" / "MEMORY.md").write_text("a" * 95, encoding="utf-8")
    (home / "memories" / "USER.md").write_text("b" * 10, encoding="utf-8")

    finding = _check_context_health(False)

    assert [i for i in finding.manual_issues if i.startswith("MEMORY.md is 95% full")]
    assert not [i for i in finding.manual_issues if i.startswith("USER.md")]
    assert "MEMORY.md 95/100 chars (95%)" in capsys.readouterr().out
