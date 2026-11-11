"""Native Anthropic must honor PluginLlm's caller cap (#153099).

Reported by friendly-neighborhood-coding-man; network transport is intercepted.
"""

from types import SimpleNamespace

from agent.auxiliary_client import _AnthropicCompletionsAdapter, _build_call_kwargs
from agent.plugin_llm import PluginLlm, _TrustPolicy, make_plugin_llm_for_test


def test_plugin_llm_explicit_cap_reaches_native_anthropic_messages(monkeypatch):
    sent = {}
    monkeypatch.setattr(
        "agent.anthropic_adapter.create_anthropic_message",
        lambda _client, api_kwargs, **_: sent.update(api_kwargs) or SimpleNamespace(content=[]),
    )
    monkeypatch.setattr(
        "agent.transports.get_transport",
        lambda _mode: SimpleNamespace(
            normalize_response=lambda _response, **_: SimpleNamespace(
                content="ok", tool_calls=None, reasoning=None, finish_reason="stop"
            )
        ),
    )
    model = "claude-opus-4-8"
    messages = [{"role": "user", "content": "hi"}]

    def native_call(**kw):
        host_kwargs, _ = PluginLlm._host_kwargs(kw)
        request = _build_call_kwargs(
            provider="anthropic", model=model, messages=host_kwargs["messages"],
            max_tokens=host_kwargs["max_tokens"],
        )
        response = _AnthropicCompletionsAdapter(object(), model).create(**request)
        return "anthropic", model, response

    llm = make_plugin_llm_for_test(
        plugin_id="native-cap", policy=_TrustPolicy(plugin_id="native-cap"),
        sync_caller=native_call,
    )
    assert llm.complete(messages, max_tokens=600).text == "ok"
    assert sent["max_tokens"] == 600

    sent.clear()
    llm.complete(messages)
    assert sent["max_tokens"] == 128_000  # Native model default is unchanged.
