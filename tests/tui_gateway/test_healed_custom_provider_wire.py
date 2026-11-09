"""Regression for the saved-provider heal in #132648 / PR #151956.

An empty or bare-custom provider saved with an old protocol must resume on
the recovered named entry's current endpoint AND wire.
"""

import json

import pytest

import hermes_cli.runtime_provider as rp
from tui_gateway import server


@pytest.mark.parametrize("saved_provider", [None, "custom"])
def test_healed_session_uses_current_entry_wire(monkeypatch, saved_provider):
    config = {
        "model": {"default": "model-a", "provider": "custom:entry-a"},
        "custom_providers": [
            {
                "name": "entry-a", "base_url": "https://a.example/v1",
                "api_key": "sk-entry-a", "api_mode": "chat_completions",
                "models": {"model-a": {}},
            },
            {
                "name": "entry-b", "base_url": "https://b.example/v1",
                "api_key": "sk-entry-b", "api_mode": "anthropic_messages",
                "models": {"model-b": {}},
            },
        ],
    }
    monkeypatch.setattr(rp, "load_config", lambda: config)
    monkeypatch.setattr(rp, "_get_model_config", lambda: config["model"])
    monkeypatch.setattr(rp, "_try_resolve_from_custom_pool", lambda *args, **kwargs: None)
    monkeypatch.setattr(server, "_load_cfg", lambda: config)

    row = {
        "model": "model-b",
        "model_config": json.dumps({
            "model": "model-b", "provider": saved_provider,
            "api_mode": "chat_completions",
        }),
    }
    overrides = server._stored_session_runtime_overrides(row)
    model, runtime = server._resolve_agent_model_runtime(
        overrides["model_override"], overrides.get("provider_override")
    )

    assert model == "model-b"
    assert runtime["requested_provider"] == "custom:entry-b"
    assert runtime["base_url"] == "https://b.example/v1"
    assert runtime["api_key"] == "sk-entry-b"
    assert runtime["api_mode"] == "anthropic_messages"
