"""New input is refused before commit while the disk guard reads critical (disk-full cascade).

Before: the gateway admitted turns into a full volume; each then failed at append_message,
_persist_session, the turn-lease release and admission settlement, and the user saw "No reply".
"""
import pytest

from gateway import disk_status
from gateway.platforms.event import MessageEvent
from gateway.session_contract import Submission
from gateway.session_ingress import DISK_FULL_REPLY, admit_message
from persistence.core.errors import AuthorityRefusal
from tests.gateway.test_session_authority_cancel_settlement import ACTOR, REF, _authority, _submit


def _critical(monkeypatch):
    monkeypatch.setattr(disk_status, "new_work_refusal",
                        lambda *a, **k: "disk critical: 100 MB free on the volume holding /h")


@pytest.mark.asyncio
async def test_submit_is_refused_storage_unavailable_and_nothing_is_committed(tmp_path, monkeypatch):
    db, authority = _authority(tmp_path, monkeypatch)
    monkeypatch.setattr(authority, "_schedule", lambda ref: None)
    with db:
        assert (await _submit(authority, "before")).status == "queued"
        _critical(monkeypatch)
        with pytest.raises(AuthorityRefusal) as refused:
            await _submit(authority, "during")
        assert refused.value.reason == "storage_unavailable"
        assert refused.value.field == "disk"
        assert [r.request_id for r in authority.persistence.admissions.list(session_id="s")] == ["before"]
        # Space freed: the same request admits (storage_unavailable is an owner-state refusal).
        monkeypatch.setattr(disk_status, "new_work_refusal", lambda *a, **k: None)
        assert (await _submit(authority, "during")).status == "queued"


@pytest.mark.asyncio
async def test_messaging_input_gets_one_plain_disk_full_notice(tmp_path, monkeypatch):
    db, authority = _authority(tmp_path, monkeypatch)
    monkeypatch.setattr(authority, "_schedule", lambda ref: None)

    async def admit_native(event):
        return await authority.submit(ACTOR, Submission(event.text, REF, {"text": event.text}, "queue"))
    monkeypatch.setattr(authority, "admit_native", admit_native)
    with db:
        await _submit(authority, "seed")
        _critical(monkeypatch)
        reply = await admit_message(authority, MessageEvent(text="hello", source=authority.sessions["s"].source))
        assert reply == DISK_FULL_REPLY
