"""Regression tests for #106153 — media-only turns reported FAILURE.

``_process_message_background`` fed its ``on_processing_complete`` outcome from
``delivery_attempted``/``delivery_succeeded``, which only text/TTS sends
populated. A turn replying with just ``MEDIA:<path>`` delivered the attachment
fine but computed ``processing_ok = False`` (no text attempted, non-empty
response), so Signal swapped the 👀 reaction for ❌ instead of ✅.

The attachment path now feeds the same tracker, so a delivered media-only
turn reports SUCCESS and a failed one still reports FAILURE.
"""

import asyncio
import json

import pytest

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    SendResult,
    _media_failure_text,
)
from gateway.platforms.event import MessageEvent, MessageType, ProcessingOutcome
from gateway.session import SessionSource, build_session_key


class _MediaOutcomeAdapter(BasePlatformAdapter):
    """Base-loop adapter (no ``send_multiple_images`` override) that records
    the turn outcome via the production ``on_processing_complete`` hook."""

    def __init__(self, *, image_ok: bool = True):
        super().__init__(PlatformConfig(enabled=True, token="fake-token"), Platform.SIGNAL)
        self._image_ok = image_ok
        self.outcomes: list = []
        self.images_sent: list = []

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        return True

    async def disconnect(self) -> None:
        return None

    async def send(self, chat_id, content, reply_to=None, metadata=None) -> SendResult:
        return SendResult(success=True, message_id="msg-1")

    async def send_typing(self, chat_id: str, metadata=None) -> None:
        return None

    async def get_chat_info(self, chat_id: str):
        return {"id": chat_id}

    async def send_image_file(self, chat_id, image_path, caption=None,
                              reply_to=None, metadata=None, **kwargs) -> SendResult:
        self.images_sent.append(str(image_path))
        if self._image_ok:
            return SendResult(success=True, message_id="img-1")
        return SendResult(success=False, error="boom")

    async def on_processing_complete(self, event: MessageEvent, outcome: ProcessingOutcome) -> None:
        self.outcomes.append(outcome)


async def _hold_typing(_chat_id, interval=2.0, metadata=None, stop_event=None):
    if stop_event is not None:
        await stop_event.wait()
    else:
        await asyncio.Event().wait()


def _allowed_image(tmp_path, monkeypatch, name: str = "photo.png"):
    root = tmp_path / "media-cache"
    f = root / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 64)
    monkeypatch.setattr("gateway.platforms.base.MEDIA_DELIVERY_SAFE_ROOTS", (root,))
    return f.resolve()


def _make_event() -> MessageEvent:
    return MessageEvent(
        text="send the photo",
        message_type=MessageType.TEXT,
        source=SessionSource(platform=Platform.SIGNAL, chat_id="111", chat_type="dm"),
        message_id="m1",
    )


@pytest.mark.asyncio
async def test_media_only_success_reports_success(tmp_path, monkeypatch):
    """Delivered media-only turn must report SUCCESS (was FAILURE → ❌)."""
    png = _allowed_image(tmp_path, monkeypatch)
    adapter = _MediaOutcomeAdapter(image_ok=True)
    adapter._keep_typing = _hold_typing

    async def handler(_event):
        return f"MEDIA:{png}"

    adapter.set_message_handler(handler)
    event = _make_event()
    await adapter._process_message_background(event, build_session_key(event.source))

    assert adapter.images_sent == [str(png)]
    assert adapter.outcomes == [ProcessingOutcome.SUCCESS]


@pytest.mark.asyncio
async def test_media_only_failure_still_reports_failure(tmp_path, monkeypatch):
    """A media-only turn whose attachment failed must still report FAILURE."""
    png = _allowed_image(tmp_path, monkeypatch)
    adapter = _MediaOutcomeAdapter(image_ok=False)
    adapter._keep_typing = _hold_typing

    async def handler(_event):
        return f"MEDIA:{png}"

    adapter.set_message_handler(handler)
    event = _make_event()
    await adapter._process_message_background(event, build_session_key(event.source))

    assert adapter.images_sent == [str(png)]
    assert adapter.outcomes == [ProcessingOutcome.FAILURE]


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_indices", [(), (1,), (0, 1)])
@pytest.mark.parametrize("warning_mode", ["shown", "suppressed", "rejected", "raises"])
async def test_image_batch_failure_notice_preserves_processing_outcome(
    tmp_path, monkeypatch, caplog, record_property, failed_indices, warning_mode,
):
    """One notice for failed images; delivery outcome and image sends stay unchanged."""
    images = [_allowed_image(tmp_path, monkeypatch, name) for name in ("first.png", "second.png")]
    adapter = _MediaOutcomeAdapter()
    adapter._keep_typing = _hold_typing
    text_sends = []
    warning_calls = []
    batch_results = []

    async def send_image_file(chat_id, image_path, **kwargs):
        index = len(adapter.images_sent)
        adapter.images_sent.append(str(image_path))
        if index in failed_indices:
            return SendResult(success=False, error="fixture-upload-failed")
        return SendResult(success=True, message_id=f"image-{index}")

    async def send(chat_id, content, **kwargs):
        text_sends.append(content)
        if warning_mode == "raises":
            raise RuntimeError("fixture-warning-transport-failed")
        if warning_mode == "rejected":
            return SendResult(success=False, error="fixture-warning-rejected")
        return SendResult(success=True, message_id="text")

    original_batch = adapter.send_multiple_images
    original_warning = adapter.emit_warning

    async def observe_warning(*args, **kwargs):
        warning_calls.append((args, kwargs))
        return await original_warning(*args, **kwargs)

    async def observe_batch(*args, **kwargs):
        result = await original_batch(*args, **kwargs)
        batch_results.append(result)
        return result

    monkeypatch.setattr(adapter, "send_image_file", send_image_file)
    monkeypatch.setattr(adapter, "send", send)
    monkeypatch.setattr(adapter, "send_multiple_images", observe_batch)
    monkeypatch.setattr(adapter, "emit_warning", observe_warning)
    monkeypatch.setattr(adapter, "warning_notifications_enabled", lambda *a, **kw: warning_mode != "suppressed")

    async def handler(_event):
        return "\n".join(f"MEDIA:{path}" for path in images)

    adapter.set_message_handler(handler)
    event = _make_event()
    await adapter._process_message_background(event, build_session_key(event.source))

    assert adapter.images_sent == [str(path) for path in images]  # no replay
    assert len(batch_results) == 1
    result = batch_results[0]
    assert result.success is (len(failed_indices) < len(images))
    if len(failed_indices) == 1:
        assert result.error == "1 image(s) failed to send: fixture-upload-failed"
    elif failed_indices:
        assert result.error == "all images failed to send"
    else:
        assert result.error is None
    expected = ProcessingOutcome.SUCCESS if result.success else ProcessingOutcome.FAILURE
    assert adapter.outcomes == [expected]  # existing at-least-one success meaning
    assert len(warning_calls) == bool(failed_indices)  # once per batch, never per image
    expected_notices = [_media_failure_text("image")] if failed_indices and warning_mode != "suppressed" else []
    assert text_sends == expected_notices
    if failed_indices:
        assert "fixture-upload-failed" in caplog.text  # diagnostic log still surfaces it
    record_property("image_batch_witness", json.dumps({
        "failed_indices": failed_indices, "image_calls": len(adapter.images_sent),
        "batch_calls": len(batch_results), "aggregate_success": result.success,
        "aggregate_error": result.error, "processing_outcome": expected.value,
        "warning_mode": warning_mode, "warning_send_attempts": text_sends,
        "warning_calls": len(warning_calls),
    }, sort_keys=True))
