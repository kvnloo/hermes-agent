"""Independent replay-admission probes for #137565 and PR #137566.

The real handler, agent worker, stream consumer, delivery classifier, reset
helper and replay gate run together. Model and platform I/O are deterministic
test doubles; unrelated preparation, persistence and final-send seams are
stubbed. These are gateway-boundary tests, not live Telegram or lease-drain E2E.
"""

import asyncio
import sys
import threading
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

import gateway.run as gateway_run
from gateway.config import Platform, StreamingConfig
from gateway.platforms.event import MessageEvent
from gateway.session import SessionSource
from tests.gateway.test_run_progress_topics import (
    MetadataEditProgressCaptureAdapter,
    _make_runner,
)


SESSION_KEY = "agent:main:telegram:dm:replay-safety"
PARTIAL_TEXT = "I have started checking that calendar request."
PREPARED_TEXT = "create the calendar event\n[already-prepared image description]"


class RecordingAdapter(MetadataEditProgressCaptureAdapter):
    SUPPORTS_MESSAGE_EDITING = True

    def __init__(self):
        super().__init__(platform=Platform.TELEGRAM)
        self.visible_output = threading.Event()
        self.agent_inputs = []

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        result = await super().send(chat_id, content, reply_to=reply_to, metadata=metadata)
        if PARTIAL_TEXT in content:
            self.visible_output.set()
        return result


def _event(*, message_id="original", internal=False):
    return MessageEvent(
        text="create the calendar event",
        message_id=message_id,
        internal=internal,
        source=SessionSource(
            platform=Platform.TELEGRAM, chat_id="replay-safety", chat_type="dm", user_id="user",
        ),
    )


def _harness(monkeypatch, tmp_path, *, streamed=False, reset_succeeds=True, deferred=False):
    adapter = RecordingAdapter()
    image_path = tmp_path / "prepared-photo.png"
    Image.new("RGB", (1, 1), color="white").save(image_path)
    adapter.prepared_image_paths = [str(image_path)]

    class ExhaustedAgent:
        def __init__(self, **kwargs):
            self.stream_delta_callback = kwargs.get("stream_delta_callback")
            self.tools = []

        def run_conversation(self, message, conversation_history=None, task_id=None, **kwargs):
            adapter.agent_inputs.append(message)
            if streamed:
                assert self.stream_delta_callback is not None
                self.stream_delta_callback(PARTIAL_TEXT)
                assert adapter.visible_output.wait(timeout=5), "No platform send before the failed result"
            return {
                "failed": True,
                "compression_exhausted": True,
                "compression_deferred": deferred,
                "final_response": "Context compression exhausted",
                "error": "context length exceeded",
                "messages": [{"role": "user", "content": message}],
                "api_calls": 1,
            }

    fake_run_agent = types.ModuleType("run_agent")
    fake_run_agent.AIAgent = ExhaustedAgent
    monkeypatch.setitem(sys.modules, "run_agent", fake_run_agent)
    config = {
        "display": {"tool_progress": "off", "interim_assistant_messages": False},
        "streaming": {"enabled": True, "transport": "edit", "edit_interval": 0.01, "buffer_threshold": 1},
    }
    monkeypatch.setattr(gateway_run, "_load_gateway_config", lambda: config)
    monkeypatch.setattr(gateway_run, "_hermes_home", tmp_path)
    monkeypatch.setattr(gateway_run, "_resolve_runtime_agent_kwargs", lambda: {"api_key": "test-only"})
    monkeypatch.setenv("HERMES_AGENT_TIMEOUT", "0")
    runner = _make_runner(adapter)
    runner.config.streaming = StreamingConfig.from_dict(config["streaming"])
    runner.hooks.emit = AsyncMock()
    runner._session_state(SESSION_KEY).persistent.native_image_paths = list(adapter.prepared_image_paths)
    old = SimpleNamespace(session_id="oversized-session", session_key=SESSION_KEY)
    fresh = SimpleNamespace(session_id="fresh-session", session_key=SESSION_KEY)
    runner._async_session_store = SimpleNamespace(
        _store=runner.session_store,
        reset_session=AsyncMock(return_value=fresh if reset_succeeds else None),
    )
    runner._hmwa_resolve_session = AsyncMock(side_effect=lambda event, source: (source, old, SESSION_KEY))
    prepared = runner._PreparedTurn([], "", PREPARED_TEXT, None, None, None, old.session_id, "test-owner")
    runner._hmwa_prepare_turn = AsyncMock(return_value=(prepared, None))
    runner._pinned_channel_inputs = lambda key, prompt, source, **kwargs: (prompt, source)
    runner._persist_prompt_pins = AsyncMock()
    runner._reply_anchor_for_event = lambda event: event.message_id
    runner._hmwa_stop_typing_for_turn = AsyncMock()
    runner._is_session_run_current = lambda key, generation: True
    runner._hmwa_shape_agent_response = AsyncMock(
        side_effect=lambda result, *args, **kwargs: (result["final_response"], False, result["messages"]),
    )
    runner._hmwa_prepend_reasoning = lambda result, response, *args: response
    runner._hmwa_runtime_footer_line = lambda *args: ""
    runner._hmwa_post_turn_hooks = AsyncMock()
    runner._evict_cached_agent = MagicMock()
    runner._clear_conversation_scope = MagicMock()
    runner._sync_telegram_topic_binding = MagicMock()
    runner._hmwa_persist_turn_transcript = AsyncMock()
    runner._hmwa_deliver_turn_response = AsyncMock(side_effect=lambda *args: args[7])
    runner._clear_session_env = MagicMock()

    async def raise_handler_error(error, *args):
        raise error

    runner._hmwa_agent_error_reply = raise_handler_error
    return runner, adapter, old, fresh


async def _handle(runner, event):
    return await asyncio.wait_for(
        runner._handle_message_with_agent(event, event.source, SESSION_KEY, 1), timeout=15,
    )


@pytest.mark.asyncio
async def test_failed_turn_with_confirmed_visible_stream_is_not_replayed(monkeypatch, tmp_path):
    runner, adapter, _old, _fresh = _harness(monkeypatch, tmp_path, streamed=True)
    event = _event()

    await _handle(runner, event)

    assert adapter.visible_output.is_set()
    assert any(PARTIAL_TEXT in send["content"] for send in adapter.sent)
    result = runner._hmwa_shape_agent_response.call_args.args[0]
    assert result["failed"] is True and result["compression_exhausted"] is True
    assert not any(message.get("role") in {"tool", "function"} for message in result["messages"])
    assert SESSION_KEY not in adapter._pending_messages, (
        "A platform-confirmed partial stream from the failed turn must block automatic replay; "
        f"already_sent={result.get('already_sent')!r}"
    )


@pytest.mark.asyncio
async def test_failed_reset_does_not_stage_original_request(monkeypatch, tmp_path):
    runner, adapter, old, _fresh = _harness(monkeypatch, tmp_path, reset_succeeds=False)
    event = _event()

    response = await _handle(runner, event)

    runner.async_session_store.reset_session.assert_awaited_once_with(SESSION_KEY)
    assert runner._hmwa_persist_turn_transcript.call_args.kwargs["session_entry"] is old
    assert SESSION_KEY not in adapter._pending_messages, "reset_session=None must not admit replay"
    assert response is not None, "A failed reset must not suppress the error response"


@pytest.mark.asyncio
async def test_successful_clean_reset_replays_once_with_prepared_input(monkeypatch, tmp_path):
    runner, adapter, _old, fresh = _harness(monkeypatch, tmp_path)
    event = _event()
    followup = _event(message_id="later-input")

    def input_arrives_after_agent_drain(result, *args, **kwargs):
        adapter._pending_messages[SESSION_KEY] = followup
        return result["final_response"], False, result["messages"]

    runner._hmwa_shape_agent_response.side_effect = input_arrives_after_agent_drain

    response = await _handle(runner, event)

    assert not adapter.visible_output.is_set()
    assert response is None
    assert adapter._pending_messages[SESSION_KEY] is event
    assert runner._hmwa_persist_turn_transcript.call_args.kwargs["session_entry"] is fresh
    assert event._gateway_compression_replay_message_text == PREPARED_TEXT
    assert event._gateway_compression_replay_native_image_paths == adapter.prepared_image_paths
    assert any(part.get("type") == "image_url" for part in adapter.agent_inputs[0])
    assert runner._peek_session_state(SESSION_KEY).conversation.queued_events == [followup]
    assert event._gateway_compression_replay_attempted is True
    adapter._pending_messages.pop(SESSION_KEY)
    runner._peek_session_state(SESSION_KEY).conversation.queued_events.clear()
    runner._hmwa_shape_agent_response.side_effect = (
        lambda result, *args, **kwargs: (result["final_response"], False, result["messages"])
    )

    second_response = await _handle(runner, event)

    assert SESSION_KEY not in adapter._pending_messages
    assert second_response is not None


@pytest.mark.asyncio
async def test_deferred_exhaustion_neither_resets_nor_replays(monkeypatch, tmp_path):
    runner, adapter, _old, _fresh = _harness(monkeypatch, tmp_path, deferred=True)

    response = await _handle(runner, _event())

    runner.async_session_store.reset_session.assert_not_awaited()
    assert SESSION_KEY not in adapter._pending_messages
    assert response is not None
