"""A profile's CLAUDE_CONFIG_DIR picks which Claude Code login the gateway borrows."""
from pathlib import Path

import pytest

import agent.secret_scope as ss
from agent.anthropic_credentials import claude_code_credentials_path


@pytest.fixture(autouse=True)
def _reset_multiplex():
    yield
    ss.set_multiplex_active(False)


def test_profile_scope_selects_its_own_claude_login(monkeypatch, tmp_path):
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    ss.set_multiplex_active(True)
    tok = ss.set_secret_scope({"CLAUDE_CONFIG_DIR": str(tmp_path / "sub2")})
    try:
        scoped = claude_code_credentials_path()
    finally:
        ss.reset_secret_scope(tok)
    tok = ss.set_secret_scope({})
    try:
        default = claude_code_credentials_path()
    finally:
        ss.reset_secret_scope(tok)
    assert scoped == tmp_path / "sub2" / ".credentials.json"
    assert default == Path.home() / ".claude" / ".credentials.json"


def test_unscoped_multiplexed_read_keeps_process_setting(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    ss.set_multiplex_active(True)
    assert claude_code_credentials_path() == tmp_path / ".credentials.json"


def test_single_profile_process_env_still_works(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert claude_code_credentials_path() == tmp_path / ".credentials.json"
