"""#150558: a phase-less pre-tool commentary message must persist and replay once."""

from agent.codex_responses_adapter import _replay_message_items
from agent.codex_runtime import _consume_codex_event_stream


_TEXT = "Checking the logs before continuing."


def _commentary_item():
    return {
        "type": "message",
        "role": "assistant",
        "id": "msg_1",
        "phase": "commentary",
        "status": "completed",
        "content": [{"type": "output_text", "text": _TEXT}],
    }


def test_phase_finalized_as_commentary_does_not_synthesize_second_message():
    commentary = _commentary_item()
    callbacks = []
    events = [
        {"type": "response.output_item.added", "output_index": 0,
         "item": {"type": "message", "role": "assistant", "id": "msg_1"}},
        {"type": "response.output_text.delta", "output_index": 0,
         "item_id": "msg_1", "delta": _TEXT},
        {"type": "response.output_item.done", "output_index": 0, "item": commentary},
        {"type": "response.output_item.added", "output_index": 1,
         "item": {"type": "function_call", "id": "fc_1", "call_id": "call_1",
                  "name": "terminal", "arguments": "{}"}},
        {"type": "response.output_item.done", "output_index": 1,
         "item": {"type": "function_call", "id": "fc_1", "call_id": "call_1",
                  "name": "terminal", "arguments": "{}", "status": "completed"}},
        {"type": "response.completed", "response": {"status": "completed"}},
    ]

    response = _consume_codex_event_stream(
        events, model="relay-model", on_commentary_message=callbacks.append,
    )
    messages = [item for item in response.output
                if (item.get("type") if isinstance(item, dict) else item.type) == "message"]
    assert messages == [commentary]
    assert callbacks == [_TEXT]
    assert len(response.output) == 2  # commentary + real function call


def test_historical_synthesized_commentary_copy_is_not_replayed():
    commentary = _commentary_item()
    synthesized = {
        "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "output_text", "text": _TEXT}],
    }
    stored = {"codex_message_items": [commentary, synthesized]}
    replayed = _replay_message_items(stored, drop_replay_item_ids=False)
    assert len(replayed) == 1
    assert replayed[0]["id"] == "msg_1"
    assert replayed[0]["phase"] == "commentary"
    assert replayed[0]["content"] == commentary["content"]

    # Two genuine message items can use identical text without being duplicates.
    real_final = {**synthesized, "id": "msg_2", "phase": "final_answer"}
    distinct = _replay_message_items(
        {"codex_message_items": [commentary, real_final]},
        drop_replay_item_ids=False,
    )
    assert len(distinct) == 2
    assert distinct[1]["phase"] == "final_answer"
