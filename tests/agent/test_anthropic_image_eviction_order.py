"""Regression for NousResearch/hermes-agent#143918: newest upload wins byte eviction."""

from agent.anthropic_message_convert import convert_messages_to_anthropic
from agent.image_eviction_policy import OUTBOUND_IMAGE_BUDGET_BYTES


def test_new_upload_after_tool_result_survives_merged_wire_byte_eviction():
    """A merged Anthropic user turn must not retire its newer upload before an older tool image."""
    # Each image fits the budget alone, but both exceed it. The conversion merges
    # the tool result and next user upload into one wire user turn.
    data_url = "data:image/png;base64," + "A" * (OUTBOUND_IMAGE_BUDGET_BYTES // 2 + 4)
    history = [
        {"role": "user", "content": "compare these"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_image",
                    "type": "function",
                    "function": {"name": "vision_analyze", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_image",
            "content": [
                {"type": "text", "text": "older screenshot"},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "this photo is newer"},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]

    _, wire = convert_messages_to_anthropic(history)

    latest = wire[-1]
    assert latest["role"] == "user"
    tool_result = latest["content"][0]
    assert tool_result["type"] == "tool_result"
    assert not any(block["type"] == "image" for block in tool_result["content"])
    assert latest["content"][-1]["type"] == "image"
