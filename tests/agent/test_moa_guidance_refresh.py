"""MoA must use refreshed advice from an uncached, interrupted fan-out.

When one reference was interrupted, MoA deliberately does not cache that fan-out.
A later tool step may retry it under the same default user_turn key and get new
advice. Preserved Anthropic thinking forbids rewriting the earlier guidance.
"""
from types import SimpleNamespace

from agent.moa_aggregator_wire import AggregatorWire


def test_retried_fanout_with_same_key_appends_changed_guidance_behind_signed_reply():
    wire = AggregatorWire()
    key = ("review", "unchanged-user-turn")
    task = {"role": "user", "content": "Read the note."}
    partial = "[Mixture of Agents reference context]\\nReference interrupted."
    fresh = "[Mixture of Agents reference context]\\nReference succeeded."

    first, guidance = wire.request([task], partial, key)
    assert first == [task]
    assert guidance == partial

    signed = {"type": "thinking", "thinking": "Read the note first.", "signature": "sig-1"}
    wire.sent(SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        reasoning_details=[signed], anthropic_content_blocks=[signed],
    ))]))

    assistant = {
        "role": "assistant", "content": "Reading.",
        "reasoning_details": [signed],
        "anthropic_content_blocks": [signed, {"type": "text", "text": "Reading."}],
        "tool_calls": [{"id": "call-1", "type": "function",
                        "function": {"name": "read_file", "arguments": '{"path":"note.txt"}'}}],
    }
    tool = {"role": "tool", "tool_call_id": "call-1", "content": "hello"}
    history = [task, assistant, tool]

    next_messages, next_guidance = wire.request(history, fresh, key)
    assert next_messages == [task, {"role": "user", "content": partial}, assistant, tool]
    assert next_guidance == fresh  # new advice must follow, not replace, the signed prefix
    assert signed in next_messages[2]["reasoning_details"]

    wire.sent(SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        reasoning_details=[], anthropic_content_blocks=[],
    ))]))
    later_messages, later_guidance = wire.request(history, fresh, key)
    assert later_guidance is None  # unchanged fresh guidance is sent only once
    assert later_messages == [
        task, {"role": "user", "content": partial}, assistant, tool,
        {"role": "user", "content": fresh},
    ]
