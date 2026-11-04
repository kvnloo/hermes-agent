"""Codex auxiliary cache affinity must match the main transport (#148675).

The real auxiliary Responses request builder must bind a physical session header and
stable conversation cache-routing header without reaching the network.
"""

from types import SimpleNamespace

from agent.auxiliary_client import (
    _CodexCompletionsAdapter,
    reset_runtime_main,
    set_runtime_main,
)


def test_codex_aux_cache_key_and_session_headers_survive_tool_round():
    token = set_runtime_main(
        "openai-codex", "gpt-5.5",
        session_id="physical-card-2", cache_scope="logical-card-root",
    )
    try:
        adapter = _CodexCompletionsAdapter(
            SimpleNamespace(base_url="https://chatgpt.com/backend-api/codex"),
            "gpt-5.5",
        )
        history = [
            {"role": "system", "content": "stable instructions"},
            {"role": "user", "content": "make a plan"},
        ]
        tool_round = [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "call_1", "type": "function",
                 "function": {"name": "lookup", "arguments": "{}"}},
            ]},
            {"role": "tool", "tool_call_id": "call_1", "content": "found it"},
        ]
        first, _, _ = adapter._build_responses_kwargs({
            "messages": history, "extra_headers": {"x-trace": "kept"},
        })
        second, _, _ = adapter._build_responses_kwargs({
            "messages": [*history, *tool_round], "extra_headers": {"x-trace": "kept"},
        })
    finally:
        reset_runtime_main(token)

    assert first["prompt_cache_key"] == second["prompt_cache_key"]
    for request in (first, second):
        headers = request["extra_headers"]
        assert headers["session_id"] == "physical-card-2"
        assert headers["x-client-request-id"] == request["prompt_cache_key"]
        assert headers["x-trace"] == "kept"


def test_codex_aux_affinity_not_injected_on_standard_responses_endpoint():
    token = set_runtime_main(
        "openai-codex", "gpt-5.5", session_id="physical-card-2",
    )
    try:
        adapter = _CodexCompletionsAdapter(
            SimpleNamespace(base_url="https://api.openai.com/v1"), "gpt-5.5",
        )
        request, _, _ = adapter._build_responses_kwargs({
            "messages": [{"role": "user", "content": "hello"}],
            "extra_headers": {"x-trace": "kept"},
        })
    finally:
        reset_runtime_main(token)

    assert request["extra_headers"] == {"x-trace": "kept"}
