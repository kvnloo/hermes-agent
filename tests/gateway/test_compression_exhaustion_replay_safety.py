"""Owner-head RED controls for #137566: do not replay a potentially effectful turn.

These test the gateway turn caller, not just the enqueue helper. A successful
stream send and a reset that did not create a new session must fail closed.

Origin implementation: @KoNit-K (NousResearch/hermes-agent#137566).
Original loss report: @jess-vancap (NousResearch/hermes-agent#137565).
Companion regression tests: downstream OSS factory, lane 1.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import Platform
from gateway.platforms.event import MessageEvent
from gateway.run_turn import GatewayTurnMixin
from gateway.session import SessionSource
from gateway.stream_consumer import GatewayStreamConsumer, StreamConsumerConfig


class _ReplayHarness(GatewayTurnMixin):
    """Keep real gateway caller/reset/staging logic; stub unrelated I/O."""

    def __init__(self, reset_id, *, streamed=False):
        self.source = SessionSource(
            platform=Platform.TELEGRAM, chat_id="chat", user_id="user",
        )
        self.event = MessageEvent(
            text="create a calendar event", message_id="in-137565", source=self.source,
        )
        self.old_entry = SimpleNamespace(session_id="oversized")
        new_entry = None if reset_id is None else SimpleNamespace(session_id=reset_id)
        self.state = SimpleNamespace(
            persistent=SimpleNamespace(native_image_paths=["photo.jpg"]),
            conversation=SimpleNamespace(queued_events=[]),
        )
        self.adapter = SimpleNamespace(_pending_messages={})
        self.hooks = SimpleNamespace(emit=AsyncMock())
        self.async_session_store = SimpleNamespace(
            reset_session=AsyncMock(return_value=new_entry),
        )
        prepared = self._PreparedTurn(
            history=[], context_prompt="prompt", message_text="prepared request",
            persist_user_message=None, persist_user_timestamp=None,
            persist_user_display_kind=None,
        )
        self._hmwa_resolve_session = AsyncMock(
            return_value=(self.source, self.old_entry, "key"),
        )
        self._hmwa_prepare_turn = AsyncMock(return_value=(prepared, object()))
        self._pinned_channel_inputs = lambda *_a, **_k: ("", self.source)
        self._persist_prompt_pins = AsyncMock()
        self._peek_session_state = lambda *_a: self.state
        self._reply_anchor_for_event = lambda *_a: None
        self._hmwa_stop_typing_for_turn = AsyncMock()
        self._is_session_run_current = lambda *_a: True
        self._hmwa_shape_agent_response = AsyncMock(
            return_value=("overflow notice", False, []),
        )
        self._hmwa_prepend_reasoning = lambda _r, response, *_a: response
        self._hmwa_runtime_footer_line = lambda *_a: ""
        self._hmwa_post_turn_hooks = AsyncMock()
        self._hmwa_classify_turn_failure = lambda *_a: (True, False, True)
        self._hmwa_persist_turn_transcript = AsyncMock()
        self._hmwa_deliver_turn_response = AsyncMock(return_value=None)
        self._hmwa_agent_error_reply = AsyncMock(
            side_effect=AssertionError("Unexpected gateway exception"),
        )
        self._clear_session_env = lambda *_a: None
        self._evict_cached_agent = lambda *_a: None
        self._clear_conversation_scope = lambda *_a, **_k: None
        self._sync_telegram_topic_binding = lambda *_a, **_k: None
        self._delivery_adapter_for = lambda *_a: self.adapter

        self.agent_result = {
            "failed": True,
            "compression_exhausted": True,
            "messages": [],
            "history_offset": 0,
        }
        self.stream_adapter = None

        async def run_agent(**_kw):
            if streamed:
                # Real consumer, not a fabricated already_sent=True result.
                stream_adapter = MagicMock()
                stream_adapter.send = AsyncMock(
                    return_value=SimpleNamespace(success=True, message_id="visible-1"),
                )
                stream_adapter.edit_message = AsyncMock(
                    return_value=SimpleNamespace(success=True),
                )
                stream_adapter.MAX_MESSAGE_LENGTH = 4096
                self.stream_adapter = stream_adapter
                consumer = GatewayStreamConsumer(
                    stream_adapter, self.source.chat_id,
                    StreamConsumerConfig(edit_interval=0.01, buffer_threshold=5, cursor=""),
                )
                consumer.on_delta("Visible partial response before later overflow")
                task = asyncio.create_task(consumer.run())
                await asyncio.sleep(0.08)
                assert consumer.already_sent is True
                consumer.finish()
                await asyncio.wait_for(task, timeout=5)
                turn_ctx = SimpleNamespace(
                    stream_consumer_holder=[consumer], source=self.source,
                    session_key="key", event=self.event,
                )
                # Production marker currently short-circuits for failed results.
                await self._run_agent_mark_streamed_delivery(self.agent_result, turn_ctx)
                assert stream_adapter.send.await_count >= 1
                assert not self.agent_result.get("already_sent")
            else:
                # Exercise production's explicit no-output observation, even when
                # the run failed. A caller lacking that observation must fail closed.
                await self._run_agent_mark_streamed_delivery(
                    self.agent_result,
                    SimpleNamespace(
                        stream_consumer_holder=[None], source=self.source,
                        session_key="key", _cleanup_msg_ids=[],
                    ),
                )
            return self.agent_result

        self._run_agent = run_agent


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reset_id", "streamed", "should_replay"),
    [
        (None, False, False),           # reset_session failed
        ("oversized", False, False),   # reset did not advance session ID
        ("fresh", True, False),        # user saw a partial stream before failure
        ("fresh", False, True),        # clean pre-response failure can recover
    ],
)
async def test_only_unseen_turn_with_confirmed_fresh_session_replays(
    monkeypatch, reset_id, streamed, should_replay,
):
    monkeypatch.setattr(
        "gateway.run_heartbeat_acceptance.heartbeat_owner_is_current",
        lambda *_a: True,
    )
    harness = _ReplayHarness(reset_id, streamed=streamed)
    await harness._handle_message_with_agent(harness.event, harness.source, "key", 1)
    harness._hmwa_agent_error_reply.assert_not_awaited()
    harness.async_session_store.reset_session.assert_awaited_once()
    assert (harness.adapter._pending_messages.get("key") is harness.event) is should_replay
    assert bool(getattr(harness.event, "_gateway_compression_replay_attempted", False)) is should_replay


@pytest.mark.asyncio
async def test_failed_reset_does_not_displace_a_followup(monkeypatch):
    monkeypatch.setattr(
        "gateway.run_heartbeat_acceptance.heartbeat_owner_is_current",
        lambda *_a: True,
    )
    harness = _ReplayHarness(None)
    followup = MessageEvent(
        text="second request", message_id="followup",
        source=harness.source,
    )
    harness.adapter._pending_messages["key"] = followup
    await harness._handle_message_with_agent(harness.event, harness.source, "key", 1)
    harness._hmwa_agent_error_reply.assert_not_awaited()
    assert harness.adapter._pending_messages["key"] is followup
    assert harness.state.conversation.queued_events == []


@pytest.mark.asyncio
async def test_one_attempt_only_after_clean_recovery(monkeypatch):
    monkeypatch.setattr(
        "gateway.run_heartbeat_acceptance.heartbeat_owner_is_current",
        lambda *_a: True,
    )
    harness = _ReplayHarness("fresh")
    await harness._handle_message_with_agent(harness.event, harness.source, "key", 1)
    assert harness.adapter._pending_messages["key"] is harness.event
    again = harness._hmwa_stage_compression_exhaustion_replay(
        harness.event, "key", harness.agent_result, "prepared request", ["photo.jpg"],
    )
    assert again is False
    assert harness.state.conversation.queued_events == []

@pytest.mark.asyncio
async def test_missing_stream_observation_does_not_auto_replay(monkeypatch):
    monkeypatch.setattr(
        "gateway.run_heartbeat_acceptance.heartbeat_owner_is_current",
        lambda *_a: True,
    )
    harness = _ReplayHarness("fresh")
    # A proxy/early-return worker which never recorded delivery safety should
    # not be allowed to replay merely because already_sent is absent.
    harness._run_agent = AsyncMock(return_value=harness.agent_result)
    await harness._handle_message_with_agent(harness.event, harness.source, "key", 1)
    harness._hmwa_agent_error_reply.assert_not_awaited()
    assert harness.adapter._pending_messages == {}
    assert not getattr(harness.event, "_gateway_compression_replay_attempted", False)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "consumer_extra,progress_ids",
    [
        ({"_delivery_ambiguous": True}, []),
        ({}, ["acknowledged-progress-1"]),
    ],
)
async def test_ambiguous_or_confirmed_progress_blocks_auto_replay(
    consumer_extra, progress_ids,
):
    harness = _ReplayHarness("fresh")
    # A transport timeout might have delivered text; successful progress may
    # have already reached the user. Either is not a clean pre-response retry.
    consumer = SimpleNamespace(already_sent=False, **consumer_extra)
    result = dict(harness.agent_result)
    await harness._run_agent_mark_streamed_delivery(
        result,
        SimpleNamespace(
            stream_consumer_holder=[consumer], source=harness.source,
            session_key="key", _cleanup_msg_ids=progress_ids,
        ),
    )
    assert result.get("_gateway_replay_visibility_checked") is True
    assert result.get("_gateway_replay_visible_output") is True
    assert not harness._hmwa_stage_compression_exhaustion_replay(
        harness.event, "key", result, "prepared request", [],
    )
