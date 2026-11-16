"""A fully-refusing init-time fallback ladder must say why at WARNING before dying.

One burned primary (an exhausted single-entry OpenRouter pool, for example) plus fallback
entries that cannot resolve credentials raises the generic ``No LLM provider configured``
RuntimeError. Without a WARNING naming each refused entry and its reason, the failure is
indistinguishable from actual config loss in gateway.log.
"""

import logging
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _isolated_recovery_marker(monkeypatch, tmp_path):
    # Linked worktrees can keep Git metadata inside the protected install home.
    monkeypatch.setattr(
        "hermes_cli._early_recovery.interrupted_pull_marker",
        lambda root: tmp_path / "hermes-update-pull",
    )


def _agent(provider="openrouter"):
    return SimpleNamespace(
        provider=provider,
        model="z-ai/glm-5.3-flash",
        base_url=None,
        api_key=None,
        _fallback_activated=False,
    )


_LADDER = [
    {"provider": "deepseek", "model": "deepseek-v4-pro"},
    {"provider": "kimi", "model": "kimi-k3"},
]


_LADDER_REASONS = (
    "deepseek",
    "no usable credentials",
    "kimi",
    "kimi auth handshake refused",
)


class _Pool:
    def __init__(self, available):
        self._available = available

    def has_credentials(self):
        return True

    def has_available(self, *, model=None):
        return self._available


@pytest.mark.parametrize(
    "primary, ladder, pool_available, raise_match, expected",
    [
        ("openrouter", _LADDER, True, "No LLM provider configured", _LADDER_REASONS),
        # Explicit non-OpenRouter primary: provider-specific missing-credentials error.
        ("anthropic", _LADDER, True, "no API key was found", _LADDER_REASONS),
        # #119533: a burned primary pool with no ladder at all must still be named.
        ("openrouter", [], False, "No LLM provider configured", ("credential pool exhausted",)),
    ],
)
def test_fully_refusing_ladder_warns_with_each_reason(
    monkeypatch, caplog, primary, ladder, pool_available, raise_match, expected
):
    """Primary resolves no client; deepseek resolves none (missing key), kimi raises."""
    from agent import agent_init

    def _fake_resolve(provider, model=None, **kwargs):
        if provider == "kimi":
            raise RuntimeError("kimi auth handshake refused")
        return (None, None)

    monkeypatch.setattr("agent.auxiliary_client.resolve_provider_client", _fake_resolve)
    monkeypatch.setattr(
        "hermes_cli.fallback_config.resolve_entry_api_key", lambda entry: None
    )
    monkeypatch.setattr(
        "agent.credential_pool.load_pool", lambda provider: _Pool(pool_available)
    )

    with caplog.at_level(logging.WARNING, logger="run_agent"):
        with pytest.raises(RuntimeError, match=raise_match):
            agent_init._routed_client_kwargs(_agent(primary), ladder, 60)

    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    text = warnings[0].getMessage()
    assert primary in text
    for fragment in expected:
        assert fragment in text


def test_recovered_ladder_does_not_warn(monkeypatch, caplog):
    """An entry refusing while a later one serves the init is degraded config, not a failure."""
    from agent import agent_init

    class _Client:
        pass

    def _fake_resolve(provider, model=None, **kwargs):
        if provider == "kimi":
            return (_Client(), model)
        return (None, None)

    monkeypatch.setattr("agent.auxiliary_client.resolve_provider_client", _fake_resolve)
    monkeypatch.setattr(
        "hermes_cli.fallback_config.resolve_entry_api_key", lambda entry: None
    )
    monkeypatch.setattr(
        agent_init,
        "_client_kwargs_from_routed",
        lambda client, timeout: {"api_key": "k"},
    )

    agent = _agent()
    with caplog.at_level(logging.WARNING, logger="run_agent"):
        kwargs = agent_init._routed_client_kwargs(agent, _LADDER, 60)

    assert kwargs == {"api_key": "k"}
    assert agent.provider == "kimi"
    assert agent._fallback_activated
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_named_profile_keeps_base_url_when_key_comes_from_provider(monkeypatch):
    """#149695: a profile endpoint must survive a router-supplied API key."""
    from agent import agent_init

    expected_url = "https://eu.openrouter.ai/api/v1"
    calls = []

    class _Client:
        pass

    def _resolve(provider, model=None, **kwargs):
        calls.append((provider, model, kwargs))
        return _Client(), model

    monkeypatch.setattr("agent.auxiliary_client.resolve_provider_client", _resolve)
    monkeypatch.setattr(
        agent_init, "_client_kwargs_from_routed",
        lambda client, timeout: {"api_key": "profile-key", "base_url": expected_url},
    )
    agent = _agent()
    agent.base_url = expected_url
    result = agent_init._routed_client_kwargs(agent, None, 60)
    assert result["base_url"] == expected_url
    assert calls == [("openrouter", agent.model, {
        "raw_codex": True, "explicit_base_url": expected_url,
    })]


def test_named_profile_endpoint_reaches_sdk_request(monkeypatch, tmp_path):
    """Resolve a profile's pooled key and inspect the SDK's outbound request."""
    import json

    import httpx
    from openai import OpenAI

    from agent import agent_init, auxiliary_client

    profile = tmp_path / "profiles" / "europe"
    profile.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(profile))
    expected_url = "https://eu.openrouter.ai/api/v1"
    key = "sk-test-profile-key"
    model = "test/model:free"
    (profile / "config.yaml").write_text(
        f"model:\n  provider: openrouter\n  default: {model}\n"
        f"  base_url: {expected_url}\n",
        encoding="utf-8",
    )
    (profile / "auth.json").write_text(json.dumps({
        "credential_pool": {"openrouter": [{
            "provider": "openrouter", "id": "test-profile", "label": "test",
            "auth_type": "api_key", "priority": 0, "source": "manual",
            "access_token": key,
        }]},
    }), encoding="utf-8")
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={
            "id": "test-response", "object": "chat.completion", "created": 0,
            "model": model, "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": "profile endpoint ok"}}],
        })

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        monkeypatch.setattr(
            auxiliary_client, "_openai_http_client_kwargs",
            lambda base_url: {"http_client": transport},
        )
        agent = _agent()
        agent.model = model
        agent.base_url = expected_url
        kwargs = agent_init._routed_client_kwargs(agent, None, 60)
        assert kwargs["base_url"].rstrip("/") == expected_url
        assert kwargs["api_key"] == key
        with OpenAI(**kwargs, http_client=transport) as client:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": "test"}],
            )
        assert response.choices[0].message.content == "profile endpoint ok"
    assert len(requests) == 1
    assert str(requests[0].url) == f"{expected_url}/chat/completions"
    assert requests[0].headers["authorization"] == f"Bearer {key}"
