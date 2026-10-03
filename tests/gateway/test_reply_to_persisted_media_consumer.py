"""Reply context survives the inbound adapter and canonical transcript round trip (#37717)."""

from types import SimpleNamespace

import pytest

from gateway.config import GatewayConfig
from gateway.platforms.event import MessageType
from gateway.session import SessionStore
from tests.gateway.test_reply_to_injection import _make_runner
from tests.gateway.test_telegram_reply_quote import _make_adapter, _make_message


@pytest.mark.asyncio
async def test_id_only_voice_reply_recovers_the_selected_persisted_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    adapter = _make_adapter()
    original = _make_message(text="")
    original.message_id = 42
    voice = adapter._build_message_event(original, MessageType.VOICE)
    store = SessionStore(tmp_path / "sessions", GatewayConfig())
    try:
        entry = store.get_or_create_session(voice.source)
        sid = entry.session_id
        # Same canonical gateway append shape: inbound platform ID accompanies the
        # user text produced by transcription, not a manually inserted SQLite column.
        store.append_to_transcript(sid, {
            "role": "user", "content": "Reserve the earlier 7pm table.",
            "message_id": voice.message_id,
        })
        store.append_to_transcript(sid, {"role": "assistant", "content": "The earlier option is available."})
        store.append_to_transcript(sid, {
            "role": "user", "content": "The later 9pm table is another option.", "message_id": "43",
        })
        store.append_to_transcript(sid, {"role": "assistant", "content": "Both options are noted."})
    finally:
        store.close_all_db_handles()

    # Reopen so the fallback cannot pass on an in-memory hand-built history list.
    reloaded = SessionStore(tmp_path / "sessions", GatewayConfig())
    try:
        message = _make_message(text="Choose this earlier one.")
        message.reply_to_message = SimpleNamespace(message_id=42, text=None, caption=None)
        reply = adapter._build_message_event(message, MessageType.TEXT)
        assert reply.reply_to_message_id == voice.message_id
        assert not reply.reply_to_text
        history = reloaded.load_transcript(sid)
        assert [row.get("message_id") for row in history if row["role"] == "user"] == ["42", "43"]
        prepared = await _make_runner()._prepare_inbound_message_text(
            event=reply, source=reply.source, history=history,
        )
        assert prepared == '[Replying to: "Reserve the earlier 7pm table."]\n\nChoose this earlier one.'
    finally:
        reloaded.close_all_db_handles()
