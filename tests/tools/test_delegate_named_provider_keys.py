"""Named delegation providers keep their scoped keys on matching endpoints (#150172)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools.delegate_tool_config import (
    _resolve_child_runtime,
    _resolve_delegation_credentials,
)


@patch("hermes_cli.runtime_provider.resolve_runtime_provider")
def test_named_provider_base_url_uses_scoped_key(mock_resolve):
    endpoint = "https://token-plan-sgp.xiaomimimo.com/v1"
    mock_resolve.return_value = {
        "provider": "custom",
        "base_url": endpoint,
        "api_key": "xiaomi-scoped-key",
        "api_mode": "chat_completions",
    }
    parent = SimpleNamespace(api_key="minimax-parent-key")
    config = {
        "provider": "xiaomi",
        "model": "mimo-v2.6-pro",
        "base_url": endpoint,
    }

    resolved = _resolve_delegation_credentials(config, parent)
    assert resolved["provider"] == "xiaomi"
    assert resolved["base_url"] == endpoint
    assert resolved["api_key"] == "xiaomi-scoped-key"
    assert resolved["api_key"] != parent.api_key
    mock_resolve.assert_called_once_with(
        requested="xiaomi", target_model="mimo-v2.6-pro"
    )

    # A differently configured host must not receive the scoped provider key.
    with pytest.raises(ValueError, match="delegation.base_url differs"):
        _resolve_delegation_credentials(
            {**config, "base_url": "https://other-provider.invalid/v1"}, parent
        )


@pytest.mark.parametrize("trailing_slash", [False, True])
def test_named_provider_key_reaches_child_request(trailing_slash):
    import httpx
    from openai import OpenAI

    from hermes_cli.runtime_provider import frozen_runtime_config

    endpoint = "https://named-provider.invalid/v1"
    config = {
        "provider": "custom:test-delegation",
        "model": "child-model",
        "base_url": endpoint + ("/" if trailing_slash else ""),
    }
    parent = SimpleNamespace(
        model="parent-model", provider="minimax", api_key="parent-test-key",
        base_url="https://parent-provider.invalid/v1", api_mode="anthropic_messages",
    )
    with frozen_runtime_config({"providers": {"test-delegation": {
        "api": endpoint, "api_key": "named-test-key", "api_mode": "chat_completions",
    }}}):
        credentials = _resolve_delegation_credentials(config, parent)
    runtime = _resolve_child_runtime(
        parent, config, parent.api_key, model=credentials["model"],
        override_provider=credentials["provider"], override_base_url=credentials["base_url"],
        override_api_key=credentials["api_key"], override_api_mode=credentials["api_mode"],
        override_acp_command=credentials.get("command"), override_acp_args=credentials.get("args"),
    )
    assert runtime["requested_provider"] == config["provider"]
    assert runtime["api_mode"] == "chat_completions"

    def respond(request):
        assert str(request.url) == endpoint + "/chat/completions"
        assert request.headers["authorization"] == "Bearer named-test-key"
        return httpx.Response(200, json={
            "id": "test-completion", "object": "chat.completion", "created": 0,
            "model": "child-model", "choices": [{
                "index": 0, "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }],
        })

    with OpenAI(
        base_url=runtime["base_url"], api_key=runtime["api_key"], max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    ) as client:
        completion = client.chat.completions.create(
            model=runtime["model"], messages=[{"role": "user", "content": "test"}],
        )
    assert completion.choices[0].message.content == "ok"
