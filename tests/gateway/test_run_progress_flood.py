"""Flood-window and dead-bubble regressions through the real progress loop."""

import time

import pytest

from gateway.config import Platform
from gateway.platforms.base import SendResult
from tests.gateway.test_run_progress_topics import (
    ManyProgressLinesAgent,
    SmallLimitProgressAdapter,
    _run_with_agent,
)


class FloodOverflowEditProgressAdapter(SmallLimitProgressAdapter):
    """Refuse the first edit for flood control, as Telegram does inside a penalty window."""

    def __init__(self, platform=Platform.TELEGRAM):
        super().__init__(platform=platform)
        self.flood_refusals = 0

    async def edit_message(self, chat_id, message_id, content) -> SendResult:
        if self.flood_refusals == 0:
            self.flood_refusals += 1
            self.edits.append({"chat_id": chat_id, "message_id": message_id, "content": content})
            return SendResult(success=False, error="flood_control:1.0", retry_after=1.0)
        return await super().edit_message(chat_id, message_id, content)



class PersistentFloodProgressAdapter(SmallLimitProgressAdapter):
    """Every edit is refused for a long flood window; records when each attempt happened."""

    def __init__(self, platform=Platform.TELEGRAM):
        super().__init__(platform=platform)
        self.edit_times = []

    async def edit_message(self, chat_id, message_id, content) -> SendResult:
        self.edit_times.append(time.monotonic())
        if len(content) > self.MAX_MESSAGE_LENGTH:
            self.oversized_edits.append(content)
        self.edits.append({"chat_id": chat_id, "message_id": message_id, "content": content})
        return SendResult(success=False, error="flood_control:30.0", retry_after=30.0)



class DeadBubbleProgressAdapter(SmallLimitProgressAdapter):
    """The first progress bubble becomes uneditable (deleted, or too old to edit)."""

    async def edit_message(self, chat_id, message_id, content) -> SendResult:
        if message_id == "progress-1":
            self.edits.append({"chat_id": chat_id, "message_id": message_id, "content": content})
            return SendResult(success=False, error="Message to edit not found")
        return await super().edit_message(chat_id, message_id, content)



class ManyProgressLinesOutlastFloodAgent(ManyProgressLinesAgent):
    """Keeps the turn alive past a short flood window so the deferred edit can land."""

    def run_conversation(self, message, conversation_history=None, task_id=None, **kwargs):
        result = super().run_conversation(message, conversation_history, task_id, **kwargs)
        time.sleep(4.0)
        return result



async def _run_many_progress_lines(monkeypatch, tmp_path, adapter_cls, session_id, agent_cls=ManyProgressLinesAgent):
    return await _run_with_agent(
        monkeypatch, tmp_path, agent_cls, session_id=session_id,
        config_data={"display": {"tool_progress": "all", "interim_assistant_messages": False}},
        platform=Platform.SLACK, chat_id="C123", chat_type="direct", thread_id="1700000000.000100",
        adapter_cls=adapter_cls,
    )



@pytest.mark.asyncio
async def test_flood_refused_overflow_edit_keeps_progress_in_bubbles(monkeypatch, tmp_path):
    """A flood refusal is "not now": editing must resume, never one message per later tool line."""
    adapter, result = await _run_many_progress_lines(
        monkeypatch, tmp_path, FloodOverflowEditProgressAdapter, "sess-progress-flood-overflow",
        agent_cls=ManyProgressLinesOutlastFloodAgent)

    assert result["final_response"] == "done"
    assert adapter.flood_refusals == 1
    # Resumed edits after the refusal: proof editing was not switched off for the turn.
    assert len(adapter.edits) > adapter.flood_refusals
    # Every overflow-line-N lands in a bubble that holds several lines, never a bubble of its own.
    single_line_sends = [s["content"] for s in adapter.sent if "\n" not in s["content"]]
    assert all(not text.startswith("overflow-line-") for text in single_line_sends), single_line_sends
    assert adapter.oversized_sends == []
    assert adapter.oversized_edits == []



@pytest.mark.asyncio
async def test_uneditable_progress_bubble_continues_in_a_fresh_bubble(monkeypatch, tmp_path):
    """One dead bubble moves progress to a fresh editable bubble instead of disabling edits."""
    adapter, result = await _run_many_progress_lines(
        monkeypatch, tmp_path, DeadBubbleProgressAdapter, "sess-progress-dead-bubble")

    assert result["final_response"] == "done"
    assert any(e["message_id"] == "progress-1" for e in adapter.edits)
    # Later edits target a fresh bubble, so editing survived the dead one.
    assert any(e["message_id"] != "progress-1" for e in adapter.edits)
    assert adapter.oversized_sends == []
    assert adapter.oversized_edits == []



@pytest.mark.asyncio
async def test_persistent_flood_does_not_retry_per_line_or_flush_oversized(monkeypatch, tmp_path):
    """Inside a long flood window the refused bubble is not re-edited for each incoming tool line,
    and turn cleanup never sends the unsplit over-limit buffer as a single edit."""
    adapter, result = await _run_many_progress_lines(
        monkeypatch, tmp_path, PersistentFloodProgressAdapter, "sess-progress-persistent-flood")

    assert result["final_response"] == "done"
    # The 30s refusal arrives mid-turn; no further edit may follow inside that window.
    assert len(adapter.edit_times) == 1, adapter.edits
    assert adapter.oversized_edits == []
    assert adapter.oversized_sends == []
    # Lines that arrived during the refusal were never sent as messages of their own.
    assert all(not s["content"].startswith("overflow-line-") for s in adapter.sent if "\n" not in s["content"])
