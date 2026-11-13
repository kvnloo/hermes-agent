"""Regression for #846: engine-owned model switches bypass only the cache confirm."""

from types import SimpleNamespace

import pytest

from agent.context_engine import ContextEngine
from agent.usage_anchor import capture_usage_anchor
from hermes_cli.model_selection_guards import (
    _context_cache_guard,
    selection_context_for_agent,
    selection_warnings,
)


class LegacyEngine:
    """An older engine with no model-switch capability declaration."""

    def __init__(self, tokens):
        self.last_prompt_tokens = tokens


class HandlingEngine(LegacyEngine):
    handles_model_switch = True


class OrdinaryEngine(LegacyEngine):
    handles_model_switch = False


@pytest.fixture(autouse=True)
def cache_guard_only(monkeypatch):
    monkeypatch.setattr("hermes_cli.config.load_config", dict)
    monkeypatch.setattr("hermes_cli.model_selection_guards._GUARDS", (_context_cache_guard,))


def _assert_warnings(context, engine_type, tokens):
    warnings = selection_warnings("new/model", provider="openrouter", selection_context=context)
    if engine_type is HandlingEngine or tokens < 100_000:
        assert warnings == []
    else:
        assert len(warnings) == 1
        warning = warnings[0]
        assert (warning.kind, warning.title, warning.model, warning.provider) == (
            "context_cache", "Large Context Switch Warning", "new/model", "openrouter")
        assert warning.message == "\n".join([
            "!!! LARGE CONTEXT MODEL SWITCH !!!",
            "",
            "This session holds ~150,000 tokens of context.",
            "Switching to new/model makes the next reply re-read all of it uncached (providers key "
            "prompt caches per model) \u2014 a one-time full-price input cost.",
            "",
            "Threshold: model.switch_context_confirm_tokens (currently 100,000; 0 disables this check).",
            "Confirm only if you intend to switch now."])
    return warnings


@pytest.mark.parametrize("engine_type", [HandlingEngine, LegacyEngine, OrdinaryEngine])
@pytest.mark.parametrize("tokens", [150_000, 40_000])
def test_live_engine_switch_confirm(engine_type, tokens):
    agent = SimpleNamespace(model="old/model", context_compressor=engine_type(tokens))
    context = selection_context_for_agent(agent)
    assert (context.context_tokens, context.current_model) == (tokens, "old/model")
    _assert_warnings(context, engine_type, tokens)


def _persisted_db(tokens):
    messages = [{"role": "user", "content": "A persisted conversation."}]
    anchor = capture_usage_anchor(tokens, 0, messages)
    return SimpleNamespace(
        get_messages_as_conversation=lambda sid: messages,
        get_session_model_config_value=lambda sid, key, default: anchor,
    )


@pytest.mark.parametrize("engine_type", [HandlingEngine, LegacyEngine, OrdinaryEngine])
@pytest.mark.parametrize("tokens", [150_000, 40_000])
def test_cli_persisted_usage_keeps_active_engine_capability(engine_type, tokens):
    from hermes_cli.cli_model_switch_mixin import _one_turn_selection_context

    cli = SimpleNamespace(
        agent=SimpleNamespace(model="old/model", context_compressor=engine_type(0)),
        model="old/model", session_id="seam-session", _session_db=_persisted_db(tokens),
    )
    context = _one_turn_selection_context(cli)
    assert context.context_tokens == tokens
    _assert_warnings(context, engine_type, tokens)


@pytest.mark.asyncio
@pytest.mark.parametrize("engine_type", [HandlingEngine, LegacyEngine, OrdinaryEngine])
@pytest.mark.parametrize("tokens", [150_000, 40_000])
@pytest.mark.parametrize("measured", [True, False], ids=["live-usage", "persisted-usage"])
async def test_gateway_selection_refusal_uses_active_engine(engine_type, tokens, measured):
    from gateway.session_mutation_model import _selection_guard_refusal

    agent = SimpleNamespace(model="old/model", context_compressor=engine_type(tokens if measured else 0))
    authority = SimpleNamespace(
        db=_persisted_db(tokens), runner=SimpleNamespace(_resident_agent_for=lambda route: agent))
    current = SimpleNamespace(model="old/model", provider="openrouter", base_url="", api_key="")
    result = SimpleNamespace(new_model="new/model", target_provider="openrouter", base_url="", api_key="",
                             model_info=None, api_mode="")
    refusal = await _selection_guard_refusal(
        authority, SimpleNamespace(route="session-route"), {},
        {"target": "seam-session", "target_revision": 1}, current, result)
    if engine_type is HandlingEngine or tokens < 100_000:
        assert refusal is None
    else:
        assert refusal["status"] == "confirmation_required"
        assert refusal["warnings"][0]["kind"] == "context_cache"
        assert "!!! LARGE CONTEXT MODEL SWITCH !!!" in refusal["confirm_message"]


def test_base_engine_does_not_claim_model_switches():
    assert ContextEngine.handles_model_switch is False


def test_engine_capability_does_not_leak_between_agents():
    handling = SimpleNamespace(model="old/model", context_compressor=HandlingEngine(150_000))
    legacy = SimpleNamespace(model="old/model", context_compressor=LegacyEngine(150_000))
    _assert_warnings(selection_context_for_agent(handling), HandlingEngine, 150_000)
    _assert_warnings(selection_context_for_agent(legacy), LegacyEngine, 150_000)
    _assert_warnings(selection_context_for_agent(handling), HandlingEngine, 150_000)
