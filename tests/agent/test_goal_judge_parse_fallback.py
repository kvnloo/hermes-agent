"""Regression for NousResearch/hermes-agent#150886 (reported by 8ullyMaguire).

An HTTP-200 coding-router tool call is not a goal-judge verdict. When a task
fallback is configured, the same auxiliary request must try it before /goal
records a parse failure; exhaustion still participates in the auto-pause guard.
"""

from unittest.mock import MagicMock, patch

import pytest

from agent import auxiliary_client as aux
from hermes_cli.goals import judge_goal


@pytest.fixture(autouse=True)
def _fresh_aux_health():
    aux._reset_aux_unhealthy_cache()
    yield
    aux._reset_aux_unhealthy_cache()


def _client(base_url, content):
    client = MagicMock()
    client.base_url = base_url
    reply = MagicMock()
    reply.choices = [MagicMock()]
    reply.choices[0].message.content = content
    reply.choices[0].message.tool_calls = None
    client.chat.completions.create.return_value = reply
    return client


def _judge_through_configured_chain(fallback_content):
    primary = _client("http://127.0.0.1:1/v1", "<tool_call>read<param_key>filePath</param_key>")
    backup = _client("http://127.0.0.1:2/v1", fallback_content)
    chain = [{"provider": "custom", "model": "strict", "base_url": backup.base_url}]
    with (
        patch.object(aux, "_resolve_task_provider_model", return_value=("auto", None, None, None, None)),
        patch.object(aux, "_get_cached_client", return_value=(primary, "router-combo")),
        patch.object(aux, "_get_auxiliary_task_config", return_value={"fallback_chain": chain}),
        patch.object(aux, "_try_configured_fallback_chain", side_effect=[
            (backup, "strict", "fallback_chain[0](custom)"), (None, None, ""),
        ]),
        patch.object(aux, "_try_main_fallback_chain", return_value=(None, None, "")),
        patch.object(aux, "_try_payment_fallback", return_value=(None, None, "")),
    ):
        verdict = judge_goal("ship the feature", "feature shipped")
    return verdict, primary, backup


def test_malformed_primary_uses_goal_judge_chain_before_pausing():
    result, primary, backup = _judge_through_configured_chain(
        '{"verdict":"done","reason":"verified"}'
    )
    assert result == ("done", "verified", False, None, False)
    assert primary.chat.completions.create.call_count == 1
    assert backup.chat.completions.create.call_count == 1


def test_exhausted_chain_is_still_a_parse_failure_not_transport_failure():
    result, primary, backup = _judge_through_configured_chain(
        "<tool_call>another invalid reply</tool_call>"
    )
    assert result[0] == "continue"
    assert "fallbacks exhausted" in result[1]
    assert result[2:] == (True, None, False)
    assert primary.chat.completions.create.call_count == 1
    assert backup.chat.completions.create.call_count == 1
