"""Regression for #152905: Desktop history is not an API-owned turn target.

A refused native session-chat stream must respond as HTTP 409 before opening
SSE rather than returning HTTP 200 and a later error event.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import GatewayConfig, PlatformConfig
from gateway.platforms.api_server import APIServerAdapter
from gateway.session import SessionStore


@pytest.mark.asyncio
async def test_desktop_session_stream_returns_http_409(tmp_path, monkeypatch):
    from gateway import run
    from gateway.session_authority import initialize_session_authority
    from hermes_state import SessionDB

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(run, "_load_gateway_config", lambda: {"platform_toolsets": {"cli": []}})
    store = SessionStore(tmp_path / "sessions", GatewayConfig())
    store._db = SessionDB(db_path=tmp_path / "state.db")
    runner = SimpleNamespace(
        session_store=store, _session_db=store._db, adapters={}, _draining=False,
        _evict_cached_agent=lambda route: None,
    )
    authority = await initialize_session_authority(runner, profile_id="default", instance_id="fixture")
    authority.db.create_session("desktop-chat", "desktop")
    adapter = APIServerAdapter(PlatformConfig(enabled=True))
    adapter.gateway_runner = runner
    adapter._session_db = authority.db
    app = web.Application()
    app.router.add_post("/api/sessions/{session_id}/chat/stream", adapter._handle_session_chat_stream)
    try:
        async with TestClient(TestServer(app)) as client:
            with patch.object(adapter, "_run_agent", new_callable=AsyncMock) as run_turn:
                response = await client.post(
                    "/api/sessions/desktop-chat/chat/stream", json={"message": "Continue from phone"}
                )
                assert response.status == 409, await response.text()
                assert response.content_type == "application/json"
                body = await response.json()
                assert body["error"]["code"] == "permission_denied"
                assert "desktop" in body["error"]["message"]
                run_turn.assert_not_called()
    finally:
        adapter._response_store.close()
        adapter._run_idempotency_store.close()
        store._db.close()
