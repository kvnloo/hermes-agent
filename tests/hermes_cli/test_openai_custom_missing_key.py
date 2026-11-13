"""Regression for #154794: keyless custom routes to the OpenAI API fail before dispatch."""

import json

import pytest

from hermes_cli.auth import AuthError
from hermes_cli.runtime_provider import resolve_runtime_provider

OPENAI_URL = "https://api.openai.com/v1"
LOCAL_URL = "http://127.0.0.1:11434/v1"


def _configure(tmp_path, monkeypatch, *, provider="custom", base_url=OPENAI_URL):
    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text(json.dumps({
        "model": {"default": "gpt-4o", "provider": provider, "base_url": base_url},
    }), encoding="utf-8")
    (home / ".env").write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_HOME", str(home))
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENROUTER_API_KEY",
                 "CUSTOM_BASE_URL", "HERMES_MODEL", "HERMES_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    return home


def test_bare_custom_openai_without_key_refused_before_request(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    with pytest.raises(AuthError, match="OPENAI_API_KEY") as exc:
        resolve_runtime_provider(requested="custom", explicit_base_url=OPENAI_URL, target_model="gpt-4o")
    assert exc.value.code == "missing_api_key"
    assert "request was not sent" in str(exc.value)


def test_inherited_openai_default_blocked_by_cron_preflight(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch, provider="openai")
    from cron.scheduler_preflight import _preflight_check_provider_key

    config = {"model": {"default": "gpt-4o", "provider": "openai", "base_url": OPENAI_URL}}
    reason = _preflight_check_provider_key({"id": "daily", "model": None, "provider": None}, config)
    assert reason is not None
    assert "provider credential missing" in reason
    assert "OPENAI_API_KEY" in reason


def test_keyless_local_custom_remains_supported(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch, base_url=LOCAL_URL)
    runtime = resolve_runtime_provider(requested="custom", explicit_base_url=LOCAL_URL)
    assert runtime["api_key"] == "no-key-required"
    assert runtime["base_url"] == LOCAL_URL


def test_custom_openai_with_key_remains_supported(tmp_path, monkeypatch):
    home = _configure(tmp_path, monkeypatch)
    (home / ".env").write_text("OPENAI_API_KEY=sk-test-valid-0123456789\n", encoding="utf-8")
    runtime = resolve_runtime_provider(requested="custom", explicit_base_url=OPENAI_URL)
    assert runtime["api_key"] == "sk-test-valid-0123456789"
