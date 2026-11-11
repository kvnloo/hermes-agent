"""A bot DM supersedes the same sender's DMs still queued for the same Bot Chat.

Bot DMs wait hours behind a busy owner; delivering each stale status in turn made the owner relay
superseded reports. Only the newest queued DM from one sender runs, carrying
"(N older updates superseded)"; started DMs and other senders are never touched.
"""
from types import SimpleNamespace

import pytest

from gateway.session_contract import SessionActor
from hermes_state_runtime import get_session_admission, list_session_admissions
from tests.gateway.test_automation_notification_category import _authority

REL = {'id': 'bot:reliability', 'name': 'reliability', 'is_bot': True}
OSS = {'id': 'bot:ossfactory', 'name': 'ossfactory', 'is_bot': True}


async def _bot_chat(tmp_path, monkeypatch):
    from gateway.session_local import create_local_session
    from gateway.session_local_title import title_new_session
    _runner, authority = await _authority(tmp_path, monkeypatch)
    actor = SessionActor('test-owner', 'default', frozenset({'session:create', 'session:submit', 'session:read'}), 'fixture')
    ref = create_local_session(authority, actor, dict(request_id='bot', source='gui', model='fixture', toolsets=[]))
    title_new_session(authority, ref, 'Bot Chat')
    return authority, ref, SimpleNamespace(authority=authority, actor=actor)


def _text(authority, admission_id):
    row = get_session_admission(authority.db, admission_id=admission_id)
    descriptor = row['payload'].get('local_automation_v1') or {}
    return row['payload'].get('text') or descriptor.get('text') or str(row['payload'])


def _queued(authority, ref):
    return [r for r in list_session_admissions(authority.db, session_id=ref.session_id) if r['status'] == 'queued']


@pytest.mark.asyncio
async def test_newest_queued_dm_supersedes_older_ones_from_same_sender(tmp_path, monkeypatch):
    from gateway.session_bot import deliver
    authority, ref, conn = await _bot_chat(tmp_path, monkeypatch)
    try:
        first = await deliver(conn, dict(id='a' * 32, profile='default', message='status v1', author=REL))
        other = await deliver(conn, dict(id='b' * 32, profile='default', message='oss status', author=OSS))
        second = await deliver(conn, dict(id='c' * 32, profile='default', message='status v2', author=REL))
        third = await deliver(conn, dict(id='d' * 32, profile='default', message='status v3', author=REL))

        queued = {r['admission_id'] for r in _queued(authority, ref)}
        assert queued == {other['admission_id'], third['admission_id']}
        assert 'status v3' in _text(authority, third['admission_id'])
        assert '(2 older updates superseded)' in _text(authority, third['admission_id'])
        assert 'superseded' not in _text(authority, other['admission_id'])
        for older in (first, second):
            row = get_session_admission(authority.db, admission_id=older['admission_id'])
            assert (row['status'], row['outcome']) == ('terminal', 'cancelled')

        from tools import bot_live_delivery as live
        old = live.read_delivery_result(tmp_path, 'a' * 32)
        assert old['status'] == 'cancelled' and old['superseded_by'] == 'c' * 32
        # The receipt keeps the sender's own message, so an exact resend still matches its identity.
        again = await deliver(conn, dict(id='d' * 32, profile='default', message='status v3', author=REL))
        assert again['admission_id'] == third['admission_id']
    finally:
        authority.db.close()


@pytest.mark.asyncio
async def test_single_queued_dm_is_unchanged(tmp_path, monkeypatch):
    from gateway.session_bot import deliver
    authority, ref, conn = await _bot_chat(tmp_path, monkeypatch)
    try:
        only = await deliver(conn, dict(id='e' * 32, profile='default', message='only update', author=REL))
        assert 'superseded' not in _text(authority, only['admission_id'])
        assert [r['admission_id'] for r in _queued(authority, ref)] == [only['admission_id']]
    finally:
        authority.db.close()
