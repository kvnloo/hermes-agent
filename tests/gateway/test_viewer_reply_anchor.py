"""A Desktop submit on a messaging session has no native reply ID."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway import session_ingress as ingress
from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import _reply_anchor_for_event
from gateway.session import SessionSource
from plugins.platforms.qqbot.adapter import QQAdapter


@pytest.mark.asyncio
async def test_viewer_submit_does_not_send_admission_id_to_qq(monkeypatch):
    adapter = QQAdapter(PlatformConfig(enabled=True, extra={"app_id": "a", "client_secret": "b"}))
    monkeypatch.setattr(adapter, "_ensure_connected", AsyncMock(return_value=True))
    api = AsyncMock(return_value={"id": "sent"})
    monkeypatch.setattr(adapter, "_api_request", api)
    source = SessionSource(platform=Platform.QQBOT, chat_id="chat", user_id="human", chat_type="dm")
    authority = SimpleNamespace(
        sessions={"session": SimpleNamespace(source=source, route="agent:main:qqbot:dm:chat")},
    )
    row = {"admission_id": "local-submit-uuid", "payload": {"text": "question"},
           "request_id": "desktop-request", "principal_id": "human", "generation": 0}
    event = ingress.restore_admitted_event(authority, SimpleNamespace(session_id="session"), row)
    await adapter.send(event.source.chat_id, "answer", reply_to=_reply_anchor_for_event(event))

    assert event.message_id == "local-submit-uuid"  # retained for the transcript/ledger
    assert "msg_id" not in api.await_args.args[2]


@pytest.mark.parametrize("reply_override", [None, "", "redirected-native-id"])
def test_native_admission_preserves_platform_reply_anchor(reply_override):
    source = SessionSource(platform=Platform.QQBOT, chat_id="chat", user_id="human", chat_type="dm")
    payload = {"text": "question", "native_text_v1": {
        "source": {**source.to_dict(), "is_bot": False},
        "timestamp": "2026-11-08T00:00:00+00:00",
        "event": {"message_id": "native-qq-id", "reply_anchor_override": reply_override},
    }}
    event = ingress.restore_admitted_event(SimpleNamespace(runner=None), None, {"payload": payload})

    expected = "native-qq-id" if reply_override is None else reply_override
    assert _reply_anchor_for_event(event) == expected


@pytest.mark.asyncio
async def test_execute_admission_sends_viewer_reply_without_qq_msg_id(monkeypatch):
    """The existing admission boundary must not turn local UUIDs into QQ reply anchors."""
    from gateway import session_completion_notes, session_managed_worker, session_operator, session_policy

    @asynccontextmanager
    async def isolated_turn(*_args):
        yield

    monkeypatch.setattr(session_completion_notes, "note_if_unviewed", AsyncMock(return_value=None))
    monkeypatch.setattr(session_policy, "policy_for_source", lambda *_args: None)
    monkeypatch.setattr(session_managed_worker, "managed_policy", lambda *_args: None)
    monkeypatch.setattr(session_operator, "is_viewer_input", lambda _row: True)
    monkeypatch.setattr(ingress, "row_turn_author", lambda *_args: None)
    monkeypatch.setattr(ingress, "_admission_scope", isolated_turn)

    adapter = QQAdapter(PlatformConfig(enabled=True, extra={"app_id": "a", "client_secret": "b"}))
    monkeypatch.setattr(adapter, "_ensure_connected", AsyncMock(return_value=True))
    api = AsyncMock(return_value={"id": "sent"})
    monkeypatch.setattr(adapter, "_api_request", api)
    source = SessionSource(platform=Platform.QQBOT, chat_id="chat", user_id="human", chat_type="dm")
    route = "agent:main:qqbot:dm:chat"
    runner = SimpleNamespace(
        _handle_message=AsyncMock(return_value="answer"),
        _adapter_for_source=lambda _source: adapter,
    )
    authority = SimpleNamespace(
        runner=runner,
        sessions={"session": SimpleNamespace(source=source, route=route)},
        native_waiters=set(),
        pending_results={},
        pending_deliveries={},
    )
    row = {
        "admission_id": "local-submit-uuid",
        "payload": {"text": "question"},
        "request_id": "desktop-request",
        "principal_id": "human",
        "generation": 0,
    }
    response = await ingress.execute_admission(authority, SimpleNamespace(session_id="session"), row)

    assert response == "answer"
    delivery_adapter, event, delivery_route, body, _home = authority.pending_deliveries[row["admission_id"]]
    assert delivery_adapter is adapter
    assert delivery_route == route
    assert event.message_id == row["admission_id"]  # transcript identity is preserved
    await delivery_adapter.send(event.source.chat_id, body, reply_to=_reply_anchor_for_event(event))
    assert "msg_id" not in api.await_args.args[2]
