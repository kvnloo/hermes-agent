"""Regression for NousResearch/hermes-agent#149807: DeepSeek image marker poisons replay."""

import json
from copy import deepcopy

import httpx
from openai import OpenAI

from agent.transports.chat_completions import ChatCompletionsTransport


def test_convert_messages_scrubs_poison_without_touching_history():
    wide = "<｜deepseek_image｜>"
    ascii_token = "<|deepseek_image|>"
    safe = "[ds-image-token]"
    image_url = f"https://images.example.test/{ascii_token}"
    history = [
        {"role": "user", "content": f"Please explain this 400: {wide}"},
        {
            "role": "assistant",
            "content": f"The server rejected {wide}",
            "reasoning_content": f"replayed {ascii_token}",
            "reasoning": f"diagnosed {wide}",
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "terminal",
                    "arguments": json.dumps({"query": f"{wide} {ascii_token}"}, ensure_ascii=False),
                },
            }],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": f'IMAGE_PLACEHOLDER = "{ascii_token}"'},
        {"role": "user", "content": [
            {"type": "text", "text": f"pasted {ascii_token} and {wide}"},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]},
    ]
    original = deepcopy(history)
    route = {"provider": "custom", "model": "deepseek-v4.1-flash-1017",
             "base_url": "https://deepseek.example.test/v1"}
    transport = ChatCompletionsTransport()

    wire = transport.convert_messages(history, **route)

    assert history == original  # Persisted transcript and earlier cache inputs stay untouched.
    assert wire[0]["content"] == f"Please explain this 400: {safe}"
    assert wire[1]["content"] == f"The server rejected {safe}"
    assert wire[1]["reasoning_content"] == f"replayed {safe}"
    assert wire[1]["reasoning"] == f"diagnosed {safe}"
    assert json.loads(wire[1]["tool_calls"][0]["function"]["arguments"]) == {
        "query": f"{safe} {safe}"
    }
    assert wire[2]["content"] == f'IMAGE_PLACEHOLDER = "{safe}"'
    assert wire[3]["content"][0]["text"] == f"pasted {safe} and {safe}"
    assert wire[3]["content"][1] is history[3]["content"][1]
    assert wire[3]["content"][1]["image_url"]["url"] == image_url
    assert wire[1]["tool_calls"][0] is not history[1]["tool_calls"][0]
    assert transport.convert_messages(wire, **route) is wire

    clean = [{"role": "user", "content": "Hello"}]
    assert transport.convert_messages(clean, **route) is clean


def test_build_kwargs_scrubs_serialized_sdk_request_without_touching_history():
    history = [{"role": "user", "content": "Explain <｜deepseek_image｜> and <|deepseek_image|>"}]
    original = deepcopy(history)
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "deepseek-v4.1-flash-1017",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Accepted"},
                "finish_reason": "stop",
            }],
        })

    transport = ChatCompletionsTransport()
    kwargs = transport.build_kwargs(
        model="deepseek-v4.1-flash-1017",
        messages=history,
        provider_name="custom",
        base_url="https://deepseek.example.test/v1",
    )
    with OpenAI(
        api_key="test-only",
        base_url="https://deepseek.example.test/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(respond)),
    ) as client:
        response = client.chat.completions.create(**kwargs)

    assert response.choices[0].message.content == "Accepted"
    assert len(requests) == 1
    assert requests[0]["messages"] == [
        {"role": "user", "content": "Explain [ds-image-token] and [ds-image-token]"}
    ]
    assert history == original
