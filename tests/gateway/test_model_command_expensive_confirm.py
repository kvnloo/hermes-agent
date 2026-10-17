"""Gateway typed ``/model <name>`` must route through the expensive-model
confirmation gate.

The pickers (Telegram/Discord inline keyboards, TUI, dashboard) confirm
expensive models via their own UI affordances; the typed text command
previously bypassed the guard entirely — a user typing
``/model openai/gpt-5.5-pro`` switched silently while the picker warned.
These tests pin the typed path:

- warning fires → handler returns the slash-confirm prompt, switch NOT applied
- confirm ("once") → switch applies (session override set)
- cancel → switch not applied, current model unchanged
- no warning (cheap model) → switch applies immediately, no prompt
"""

from types import SimpleNamespace

import pytest
import hermes_yaml as yaml

from gateway.config import Platform
from gateway.platforms.event import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource


def _make_runner():
    runner = object.__new__(GatewayRunner)
    runner.adapters = {}
    runner._voice_mode = {}
    runner._session_model_overrides = {}
    runner._running_agents = {}
    return runner


def _make_event(text):
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=SessionSource(platform=Platform.TELEGRAM, chat_id="12345", chat_type="dm"),
    )


def _fake_switch_result():
    from hermes_cli.model_switch import ModelSwitchResult

    return ModelSwitchResult(
        success=True,
        new_model="openai/gpt-5.5-pro",
        target_provider="openrouter",
        provider_changed=False,
        api_key="sk-test",
        base_url="https://openrouter.ai/api/v1",
        api_mode="chat_completions",
        provider_label="OpenRouter",
    )


def _fake_warning():
    return SimpleNamespace(
        message=(
            "!!! EXPENSIVE MODEL WARNING !!!\n"
            "openai/gpt-5.5-pro has known pricing above Hermes' safety threshold.\n"
            "did you mean to select openai/gpt-5.5?"
        ),
    )


def _setup_isolated_home(tmp_path, monkeypatch, *, warn):
    import gateway.run as gateway_run

    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    cfg_path = hermes_home / "config.yaml"
    cfg_path.write_text(
        yaml.safe_dump({"model": {"default": "old-model", "provider": "openrouter"}, "providers": {}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(gateway_run, "_hermes_home", hermes_home)
    monkeypatch.setattr("agent.models_dev.fetch_models_dev", lambda: {})
    monkeypatch.setattr(
        "hermes_cli.model_switch.switch_model",
        lambda **kw: _fake_switch_result(),
    )
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: hermes_home)
    monkeypatch.setattr("hermes_cli.config.get_hermes_home", lambda: hermes_home)
    monkeypatch.setattr(
        "hermes_cli.model_cost_guard.expensive_model_warning",
        (lambda *a, **kw: _fake_warning()) if warn else (lambda *a, **kw: None),
    )
    return cfg_path


@pytest.mark.asyncio
async def test_typed_model_expensive_confirm_once_applies_switch(tmp_path, monkeypatch):
    """Resolving the confirm with "once" applies the switch."""
    _setup_isolated_home(tmp_path, monkeypatch, warn=True)
    runner = _make_runner()
    runner._evict_cached_agent = lambda session_key: None

    captured = {}

    async def _fake_request_slash_confirm(**kwargs):
        captured.update(kwargs)
        return None  # buttons rendered

    runner._request_slash_confirm = _fake_request_slash_confirm

    await runner._handle_model_command(_make_event("/model openai/gpt-5.5-pro"))
    assert runner._session_model_overrides == {}

    reply = await captured["handler"]("once")

    assert "gpt-5.5-pro" in reply
    overrides = list(runner._session_model_overrides.values())
    assert len(overrides) == 1
    assert overrides[0]["model"] == "openai/gpt-5.5-pro"




def _seed_openrouter_price_cache(monkeypatch):
    import time

    import agent.models_dev as models_dev

    cache = {
        "openrouter": {
            "name": "OpenRouter",
            "env": ["OPENROUTER_API_KEY"],
            "api": "https://openrouter.ai/api/v1",
            "models": {
                "openai/gpt-5.5-pro": {"cost": {"input": 50.0, "output": 200.0}},
            },
        },
    }
    monkeypatch.setattr(models_dev, "_models_dev_cache", cache)
    monkeypatch.setattr(models_dev, "_models_dev_cache_time", time.time())
    reads = []

    def _fetch_models_dev(force_refresh=False, *, allow_network=True):
        reads.append(allow_network)
        if allow_network:
            raise AssertionError("selection guard attempted a models.dev refresh")
        return cache

    monkeypatch.setattr(models_dev, "fetch_models_dev", _fetch_models_dev)
    return reads


@pytest.mark.parametrize(("choice", "should_switch"), [("once", True), ("cancel", False)])
@pytest.mark.asyncio
async def test_typed_gateway_switch_confirms_from_local_guard_before_switch_seam(
    tmp_path, monkeypatch, choice, should_switch,
):
    from hermes_cli.model_cost_guard import expensive_model_warning

    _setup_isolated_home(tmp_path, monkeypatch, warn=False)
    monkeypatch.setattr("hermes_cli.model_cost_guard.expensive_model_warning", expensive_model_warning)
    monkeypatch.setattr("gateway.code_skew.detect_code_skew", lambda: None)
    monkeypatch.setattr(
        "hermes_cli.context_switch_guard.enrich_model_switch_warnings_for_gateway",
        lambda *_args, **_kwargs: None,
    )

    def _blocked_before_consent(*_args, **_kwargs):
        raise AssertionError("switch validation or capabilities ran before consent")

    monkeypatch.setattr("hermes_cli.models_validate.validate_requested_model", _blocked_before_consent)
    monkeypatch.setattr("hermes_cli.model_switch.get_model_capabilities", _blocked_before_consent)
    monkeypatch.setattr("hermes_cli.model_switch.get_model_info", _blocked_before_consent)
    metadata_reads = _seed_openrouter_price_cache(monkeypatch)
    runner = _make_runner()
    runner._evict_cached_agent = lambda _session_key: None
    events = []
    approved = {"value": False}

    def _switch_model(**_kwargs):
        assert approved["value"]
        events.append("switch")
        return _fake_switch_result()

    monkeypatch.setattr("hermes_cli.model_switch.switch_model", _switch_model)
    captured = {}

    async def _request_slash_confirm(**kwargs):
        captured.update(kwargs)
        events.append("prompt")
        return None

    runner._request_slash_confirm = _request_slash_confirm

    await runner._handle_model_command(
        _make_event("/model openai/gpt-5.5-pro --provider openrouter"))

    assert events == ["prompt"]
    assert metadata_reads and all(read is False for read in metadata_reads)
    assert runner._session_model_overrides == {}

    approved["value"] = should_switch
    reply = await captured["handler"](choice)
    if should_switch:
        assert "gpt-5.5-pro" in reply
        assert events == ["prompt", "switch"]
        overrides = list(runner._session_model_overrides.values())
        assert len(overrides) == 1
        assert overrides[0]["model"] == "openai/gpt-5.5-pro"
    else:
        assert "cancel" in reply.lower()
        assert events == ["prompt"]
        assert runner._session_model_overrides == {}
@pytest.mark.asyncio
async def test_failed_inplace_swap_aborts_commit(tmp_path, monkeypatch):
    """A failed in-place agent swap must be a no-op, not a dead session.

    Regression for #50163: the resolution pipeline succeeds (valid model name)
    but the cached agent's ``switch_model()`` raises mid-conversation (bad key /
    unreachable URL). The agent rolls itself back to the old working model; the
    gateway must NOT then commit the broken model as a session override or evict
    the working cached agent — otherwise the next message rebuilds a dead agent
    and the conversation is lost.
    """
    _setup_isolated_home(tmp_path, monkeypatch, warn=False)
    runner = _make_runner()

    # Working cached agent whose in-place swap fails (and rolls itself back).
    class _FailingAgent:
        def __init__(self):
            self.model = "old-model"
            self.provider = "openrouter"

        def switch_model(self, **kwargs):
            # Mirrors agent_runtime_helpers.switch_model: the real method
            # restores old state then re-raises. We keep model unchanged.
            raise RuntimeError("connection refused: bad base_url")

    import threading

    agent = _FailingAgent()
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    session_key = runner._session_key_for_source(_make_event("/model x").source)
    runner._agent_cache[session_key] = [agent, None]
    runner._session_db = None

    evicted = []
    runner._evict_cached_agent = lambda sk: evicted.append(sk)

    result = await runner._handle_model_command(_make_event("/model openai/gpt-5.5-pro"))

    # Error surfaced to the user, not a success confirmation.
    assert result is not None
    assert "failed" in result.lower()
    # The broken switch must NOT have been committed anywhere.
    assert runner._session_model_overrides == {}
    # The working cached agent must NOT have been evicted.
    assert evicted == []
    # The agent stayed on its old model (rolled back).
    assert agent.model == "old-model"

@pytest.mark.asyncio
async def test_registered_guard_failure_rejects_typed_switch_without_mutation(tmp_path, monkeypatch):
    """A real registered-guard fault is a recoverable refusal, not a warning-free switch."""
    from dataclasses import replace
    from unittest.mock import AsyncMock

    from hermes_cli.model_cost_guard import expensive_model_warning

    config_path = _setup_isolated_home(tmp_path, monkeypatch, warn=False)
    monkeypatch.setattr("hermes_cli.model_cost_guard.expensive_model_warning", expensive_model_warning)
    monkeypatch.setattr("gateway.code_skew.detect_code_skew", lambda: None)
    monkeypatch.setattr(
        "hermes_cli.context_switch_guard.enrich_model_switch_warnings_for_gateway",
        lambda *_args, **_kwargs: None,
    )
    result = replace(
        _fake_switch_result(), new_model="guard-fault-model", target_provider="anthropic",
    )
    switch_calls = []

    def _switch_model(**_kwargs):
        switch_calls.append(True)
        return result

    monkeypatch.setattr("hermes_cli.model_switch.switch_model", _switch_model)
    failures = []

    def _broken_metadata(provider, model):
        failures.append((provider, model))
        raise RuntimeError("registered guard metadata failure")

    monkeypatch.setattr("agent.models_dev.get_model_info", _broken_metadata)
    before = config_path.read_bytes()
    runner = _make_runner()
    runner._record_switch_metrics = lambda *_args, **_kwargs: None
    runner._evict_cached_agent = lambda *_args, **_kwargs: None
    runner._model_switch_confirmation = AsyncMock(return_value="switched")
    event = _make_event("/model guard-fault-model --provider anthropic")
    old_override = {"model": "old-model", "provider": "openrouter"}
    session_key = runner._session_key_for_source(event.source)
    runner._session_model_overrides[session_key] = old_override.copy()
    before_overrides = {session_key: old_override.copy()}

    reply = await runner._handle_model_command(event)

    assert reply is not None
    assert "staying on old-model" in reply.lower()
    assert "no model change was made" in reply.lower()
    assert failures == [("anthropic", "guard-fault-model")]
    assert switch_calls == []
    assert runner._session_model_overrides == before_overrides
    assert config_path.read_bytes() == before
