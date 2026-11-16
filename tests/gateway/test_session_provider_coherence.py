"""Regression for #156665: a stale Desktop provider must not route an Ollama model to PAYG."""

import pytest

from hermes_state_runtime import RuntimeStoreError


def test_gui_create_rejects_ollama_tag_on_openrouter_but_keeps_real_routes(tmp_path):
    from gateway.session_policy import build_policy

    tagged = "deepseek-v4.1-flash:1017"
    config = {"model": {"default": tagged, "provider": "ollama-cloud"}}
    create = {"source": "gui", "cwd": str(tmp_path), "model": tagged}

    # Leaving the provider to the configured profile must stay on the subscription.
    default = build_policy(create, config)
    assert (default.model, default.provider) == (tagged, "ollama-cloud")

    # A real OpenRouter slug is a deliberate, valid aggregator choice.
    routed = build_policy(
        {**create, "model": "deepseek/deepseek-v4.1-flash-1017", "provider": "openrouter"},
        config,
    )
    assert (routed.model, routed.provider) == ("deepseek/deepseek-v4.1-flash-1017", "openrouter")

    # The leaked pair in the report must fail admission before any session exists.
    with pytest.raises(RuntimeStoreError) as error:
        build_policy({**create, "provider": "openrouter"}, config)
    assert error.value.reason == "invalid_params"
    assert error.value.field == "provider"
    assert "Ollama build tag" in error.value.detail
    assert "ollama-cloud" in error.value.detail
