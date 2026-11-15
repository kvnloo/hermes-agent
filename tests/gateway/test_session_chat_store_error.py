"""A chat-platform session cannot be continued through the API's native chat door.

Regression for NousResearch/hermes-agent#150153, reported by enckequity.
A refused turn is an HTTP conflict, not an unhandled server error; it must
not change the platform's session or create an API admission.
"""

import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from hermes_state_runtime import list_session_admissions


@pytest.mark.asyncio
async def test_session_chat_refuses_chat_platform_without_admission(api, owner):
    session_id = "telegram-owned"
    owner.db.create_session(session_id, source="telegram")
    app = web.Application()
    app.router.add_post("/api/sessions/{session_id}/chat", api._handle_session_chat)

    async with TestClient(TestServer(app)) as client:
        response = await client.post(
            f"/api/sessions/{session_id}/chat", json={"message": "continue here"})
        status, body_text = response.status, await response.text()

    assert status == 409, (status, body_text)
    assert json.loads(body_text)["error"]["code"] == "permission_denied"
    assert owner.db.get_session(session_id)["source"] == "telegram"
    assert list_session_admissions(
        owner.db, session_id=session_id, pending_only=False) == []
