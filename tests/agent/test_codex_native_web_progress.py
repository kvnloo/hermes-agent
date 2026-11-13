"""Native Responses web calls must be visible while the server is running them.

Repro from cjjdaq: NousResearch/hermes-agent#154625.
"""

from types import SimpleNamespace

import pytest

from agent.codex_runtime import _consume_codex_event_stream
from agent.codex_responses_adapter import _normalize_codex_response


@pytest.mark.parametrize(("item_type", "action", "name", "args"), [
    ("web_search_call", {"type": "search", "query": "Hermes docs"}, "web_search", {"query": "Hermes docs"}),
    ("web_fetch_call", {"type": "open_page", "url": "https://example.test/docs"}, "web_extract",
     {"url": "https://example.test/docs"}),
])
@pytest.mark.parametrize("wire", ["dict", "object"])
def test_server_web_call_has_live_start_and_finish_before_answer(item_type, action, name, args, wire):
    def shape(value):
        return SimpleNamespace(**value) if wire == "object" else value

    item = shape({"type": item_type, "id": "ws_1", "status": "in_progress",
                  "action": shape(action)})
    # The SSE envelope and native tool may be raw JSON, but assistant normalization
    # receives parsed SDK message objects from the Responses client.
    message = SimpleNamespace(type="message", status="completed", role="assistant",
                              content=[SimpleNamespace(type="output_text", text="Found it.")])
    events = [
        shape({"type": "response.output_item.added", "output_index": 0, "item": item}),
        shape({"type": "response.output_item.done", "output_index": 0, "item": item}),
        shape({"type": "response.output_item.done", "output_index": 1, "item": message}),
        shape({"type": "response.completed", "response": shape({"status": "completed", "output": None})}),
    ]
    seen = []

    def wire_events():
        for index, event in enumerate(events):
            if index == 1:
                assert seen[0][:3] == ("progress", "tool.started", name)
                assert seen[1][:2] == ("start", name)
                assert seen[0][3] == args[next(iter(args))]
            yield event

    response = _consume_codex_event_stream(
        wire_events(), model="gpt-test",
        on_tool_progress=lambda kind, tool, preview, payload, **kw: seen.append(
            ("progress", kind, tool, preview, payload, kw)),
        on_tool_start=lambda call_id, tool, payload: seen.append(("start", tool, call_id, payload)),
        on_tool_complete=lambda call_id, tool, payload, result: seen.append(
            ("complete", tool, call_id, payload, result)),
    )
    assert [entry[:2] for entry in seen] == [
        ("progress", "tool.started"), ("start", name),
        ("progress", "tool.completed"), ("complete", name),
    ]
    assert seen[1][2] == seen[3][2]
    assert seen[0][4] == seen[1][3] == seen[3][3] == args
    assert seen[2][5]["is_error"] is False

    assistant, finish = _normalize_codex_response(response)
    assert finish == "stop"
    assert assistant.content == "Found it."
    assert assistant.tool_calls == []
