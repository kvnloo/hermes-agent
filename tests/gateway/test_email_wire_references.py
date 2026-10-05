"""Provider session identity stays separate from reply headers (PR #132967)."""

from email import policy
from email.parser import BytesParser

import pytest

from gateway.config import PlatformConfig
from plugins.platforms.email.adapter import EmailAdapter


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_thread_id", ["1876543210123456789", ""])
async def test_provider_thread_routes_replies_with_real_message_ids(monkeypatch, provider_thread_id):
    monkeypatch.setenv("EMAIL_ADDRESS", "hermes@example.test")
    monkeypatch.setenv("EMAIL_ALLOWED_USERS", "sender@example.test")
    adapter = EmailAdapter(PlatformConfig(enabled=True))
    events = []

    async def capture(event):
        events.append(event)

    adapter.handle_message = capture
    inbound = {
        "sender_addr": "sender@example.test", "sender_name": "Sender",
        "subject": "Ordinary conversation", "message_id": "<first@example.test>",
        "in_reply_to": "", "references": "", "body": "Hello", "attachments": [],
        "date": "", "sender_authenticated": True, "provider_thread_id": provider_thread_id,
    }
    await adapter._dispatch_message(inbound)
    first, first_id, _ = adapter._new_reply(
        "sender@example.test", "Hello back", reply_to_msg_id=inbound["message_id"])
    first_wire = BytesParser(policy=policy.default).parsebytes(first.as_bytes())
    assert str(first_wire["References"]) == "<first@example.test>"
    assert str(first_wire["In-Reply-To"]) == "<first@example.test>"

    # A subsequent message can cite only our reply; preserve the known wire root.
    await adapter._dispatch_message({
        **inbound, "message_id": "<second@example.test>",
        "references": first_id, "in_reply_to": first_id,
    })
    second, _, _ = adapter._new_reply(
        "sender@example.test", "Second answer", reply_to_msg_id="<second@example.test>")
    second_wire = BytesParser(policy=policy.default).parsebytes(second.as_bytes())
    assert events[0].source.thread_id == events[1].source.thread_id
    assert str(second_wire["References"]) == "<first@example.test> <second@example.test>"
    assert str(second_wire["In-Reply-To"]) == "<second@example.test>"
