"""A subscription primary at its limit: the switch notice names the per-token bill and the reset,
and opt-in ``fallback.on_subscription_limit`` (switch | wait | ask) decides whether to switch.
Real config.yaml in the sandboxed HERMES_HOME and the real fallback resolver (an OpenRouter entry
with its own key: building the client never touches the network)."""
from unittest.mock import patch

import pytest

from agent.error_classifier import FailoverReason
from hermes_constants import get_hermes_home
from run_agent import AIAgent

NOW = 1_700_000_000
RESET = NOW + 3600
METERED = {"provider": "openrouter", "model": "openai/gpt-5", "base_url": "https://openrouter.ai/api/v1",
           "api_key": "sk-or-v1-test"}
SAME_BACKEND = {"provider": "openai-codex", "model": "gpt-5.5"}


def _codex_agent(clarify=None, chain=(METERED,)):
    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="codex-oauth", provider="openai-codex", base_url="https://chatgpt.com/backend-api/codex",
            model="gpt-5.5", quiet_mode=True, skip_context_files=True, skip_memory=True,
            fallback_model=list(chain), clarify_callback=clarify,
        )
    agent.client = None
    return agent


def _switch(agent, policy):
    (get_hermes_home() / "config.yaml").write_text(f"fallback:\n  on_subscription_limit: {policy}\n")
    with patch("agent.fallback_cooldown.time.time", return_value=NOW):
        return agent._try_activate_fallback(reason=FailoverReason.rate_limit, reset_at=RESET)


def test_subscription_to_metered_switch_says_billed_per_token_and_reset_time():
    agent = _codex_agent()
    assert _switch(agent, "switch") is True
    assert agent.model == "openai/gpt-5"
    notice = " ".join(agent._pending_fallback_notice)
    assert "gpt-5.5 via openai-codex limit reached (resets " in notice
    assert "Continuing on openai/gpt-5 via openrouter, billed per token." in notice
    assert "Back on gpt-5.5 at the first turn after the reset." in notice


@pytest.mark.parametrize(("policy", "answer", "switched", "asked"), [
    ("wait", None, False, 0),
    ("ask", 0, True, 1),
    ("ask", 1, False, 1),
])
@pytest.mark.parametrize("chain", [(METERED,), (SAME_BACKEND, METERED)], ids=["metered-first", "skipped-entry-first"])
def test_on_subscription_limit_policy_gates_the_metered_switch(policy, answer, switched, asked, chain):
    calls = []

    def clarify(questions):
        calls.append(questions)
        return {"answers": {"q0": questions[0]["choices_offered"][answer]}, "outcome": "submitted"}

    agent = _codex_agent(clarify, chain)
    assert _switch(agent, policy) is switched
    assert (agent.model == "openai/gpt-5") is switched
    assert len(calls) == asked
    if not switched:  # still on the primary; the retry loop's next walk does not re-ask
        assert agent._fallback_index == 0
        assert _switch(agent, policy) is False
        assert len(calls) == asked


def test_ask_skips_resolver_error_and_prompts_for_next_metered_route():
    """An unusable candidate cannot abort the guarded walk before a usable fallback."""
    broken = {**METERED, "model": "openai/broken-client"}
    asked = []

    def clarify(questions):
        asked.append(questions)
        return {"answers": {"q0": questions[0]["choices_offered"][0]}, "outcome": "submitted"}

    agent = _codex_agent(clarify, chain=(broken, METERED))
    from agent.route_binding import resolve_route_entry_client

    def fail_broken_client(entry, provider, model):
        if model == broken["model"]:
            raise ValueError("candidate client cannot be constructed")
        return resolve_route_entry_client(entry, provider, model)

    # The real resolver handles the second entry; only the first models a
    # provider-client construction error that the fallback walk normally catches.
    with patch("agent.fallback_billing.resolve_route_entry_client", side_effect=fail_broken_client):
        assert _switch(agent, "ask") is True

    assert agent.model == METERED["model"]
    assert len(asked) == 1
    assert METERED["model"] in asked[0][0]["question"]
    assert "Continuing on openai/gpt-5 via openrouter, billed per token." in " ".join(agent._pending_fallback_notice)
