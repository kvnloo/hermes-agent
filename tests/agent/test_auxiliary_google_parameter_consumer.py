"""Google-shaped parameter errors must recover through the real fallback consumer (#125497)."""
from copy import deepcopy
from types import SimpleNamespace

from agent.auxiliary_client import _FallbackDestination, _call_fallback_candidate_sync


def test_google_unknown_reasoning_retries_fallback_with_only_reasoning_removed():
    sent = []
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content="fixture completion"), finish_reason="stop")])

    class GooglePayloadError(Exception):
        status_code = 400

    def create(**kwargs):
        sent.append(deepcopy(kwargs))
        assert len(sent) <= 2, "parameter recovery must not resend indefinitely"
        if "reasoning" in kwargs.get("extra_body", {}):
            raise GooglePayloadError(
                'Invalid JSON payload received. Unknown name "reasoning": Cannot find field.')
        return response

    # This is an already-resolved client, like the caller supplies in production.
    # Attaching its typed destination avoids credential/provider discovery entirely.
    destination = _FallbackDestination(
        "fixture-google", "https://completion.invalid/v1", "chat_completions", "fixture-model")
    client = SimpleNamespace(
        base_url=destination.base_url, _hermes_fallback_destination=destination,
        chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    messages = [{"role": "user", "content": "fixture request"}]
    extra_body = {"fixture_option": "preserve"}
    result = _call_fallback_candidate_sync(
        client, destination.model, "fixture-google", task="title_generation",
        messages=messages, temperature=0.3, max_tokens=16, tools=None,
        effective_timeout=7.0, effective_extra_body=extra_body,
        reasoning_config={"enabled": False},
    )

    assert result is response
    assert result.choices[0].message.content == "fixture completion"
    assert len(sent) == 2
    first, second = sent
    assert "reasoning" in first["extra_body"]
    expected_retry = deepcopy(first)
    del expected_retry["extra_body"]["reasoning"]
    assert second == expected_retry
    assert second["extra_body"] == extra_body == {"fixture_option": "preserve"}
    assert second["messages"] == messages
    assert second["model"] == destination.model
    assert second["temperature"] == 0.3
    assert second["timeout"] == 7.0
