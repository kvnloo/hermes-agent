"""Regression for NousResearch/hermes-agent#149807: DeepSeek image marker poisons replay."""

import json
from copy import deepcopy

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
             "base_url": "http://127.0.0.1:8000/v1"}
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
