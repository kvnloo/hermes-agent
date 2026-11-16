"""Typed ``/discard`` on a local (Ink / Desktop) session reaches the lost turn (#139532, GW-10).

The pause notice and ``/handoff``'s refusal tell the user to send ``/discard``; Ink and Desktop send a
typed command through ``slash.exec``. Real authority + SQLite: an owner restart fences the head
``unknown`` with a follower queued behind it."""
from types import SimpleNamespace

import pytest

from gateway.config import GatewayConfig, Platform
from gateway.session import SessionSource, SessionStore
from gateway.session_authority import LiveSession, initialize_session_authority
from gateway.session_contract import SessionRef, Submission
from gateway.session_controls import AuthorityConnection
from hermes_state_runtime import claim_session_input, list_session_admissions
from agent.i18n import t
from tests.gateway.test_authority_unknown_resolution import Peer
from tests.waiting import async_wait_until


async def _local_session_with_unknown_head(tmp_path, monkeypatch, executed):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    # The local adapter's own source check, as test_pre_command_in_gateway.py stubs it.
    monkeypatch.setattr('gateway.session_local.authorize_local_source', lambda _r, _s: True)
    store = SessionStore(tmp_path / 'sessions', GatewayConfig())
    db = store._db

    async def answer(event):
        from gateway.session_results import execution_result
        executed.append(event.text)
        execution_result.get()['result'] = {'final_response': 'ACK_' + event.text, 'completed': True, 'messages': []}
        return 'ACK_' + event.text

    runner = SimpleNamespace(_session_db=db, session_store=store, _draining=False,
                             _handle_message=answer, _adapter_for_source=lambda source: None)
    db.create_session('s', source='tui')
    first = await initialize_session_authority(runner, profile_id=str(tmp_path), instance_id='owner-1')
    actor = AuthorityConnection(first, Peer(), {'user_id': 'human'}).actor
    source = SessionSource(platform=Platform.LOCAL, chat_id='local-s', user_id=actor.subject)
    first.sessions['s'] = LiveSession(source, 's')
    ref = SessionRef(str(tmp_path), 's')
    first._schedule = lambda ref: None
    head = await first.submit(actor, Submission('head', ref, {'text': 'HEAD'}, 'queue'))
    follower = await first.submit(actor, Submission('follower', ref, {'text': 'FOLLOWER'}, 'queue'))
    assert claim_session_input(db, epoch=first.epoch, session_id='s')['admission_id'] == head.admission_id
    authority = await initialize_session_authority(runner, profile_id=str(tmp_path), instance_id='owner-2')
    authority.sessions['s'] = LiveSession(source, 's')
    rows = {r['admission_id']: r['status'] for r in list_session_admissions(db, session_id='s')}
    assert rows == {head.admission_id: 'unknown', follower.admission_id: 'queued'}
    return store, authority, head, follower


def _statuses(authority):
    return {r['admission_id']: (r['status'], r['outcome'])
            for r in list_session_admissions(authority.db, session_id='s', pending_only=False)}


@pytest.mark.asyncio
async def test_typed_discard_releases_the_follower_on_a_local_session(tmp_path, monkeypatch):
    executed = []
    store, authority, head, follower = await _local_session_with_unknown_head(tmp_path, monkeypatch, executed)
    viewer = AuthorityConnection(authority, Peer(), {'user_id': 'human'})
    try:
        await viewer.dispatch({'id': 1, 'method': 'session.resume', 'params': {'session_id': 's'}})
        reply = await viewer.dispatch({'id': 2, 'method': 'slash.exec',
                                       'params': {'session_id': 's', 'command': '/discard'}})
        assert 'error' not in reply, reply
        assert reply['result']['type'] == 'exec' and reply['result']['output'], reply
        assert reply['result']['output'] != t('gateway.discard.nothing')
        assert _statuses(authority)[head.admission_id] == ('terminal', 'interrupted')
        # The fence is gone. (That the drain then runs the follower is test_authority_unknown_resolution.py's,
        # same owner path; this fixture's drain has no stored local policy to run it with.)
        live = authority.sessions['s']
        await async_wait_until(lambda: live.task is not None and live.task.done(), what='drain ran')
        assert all(status != 'unknown' for status, _ in _statuses(authority).values())
        assert 'HEAD' not in executed  # never replayed
        # The follower is now the FIFO's claimable head (a lost head blocks every claim).
        assert claim_session_input(authority.db, epoch=authority.epoch, session_id='s')['admission_id'] == follower.admission_id
        # Nothing left to discard: a second /discard says so.
        again = await viewer.dispatch({'id': 3, 'method': 'slash.exec',
                                       'params': {'session_id': 's', 'command': '/discard'}})
        assert again.get('result', {}).get('output') == t('gateway.discard.nothing'), again
    finally:
        await viewer.close()
        store.close_all_db_handles()


@pytest.mark.asyncio
async def test_typed_discard_with_an_id_acts_on_that_lost_turn_only(tmp_path, monkeypatch):
    """ACP's refusal prints `/discard <id>`: a wrong id discards nothing, the exact id releases."""
    executed, fired = [], []

    async def observed(_authority, _ref, canonical, _alias, arg):
        fired.append((canonical, arg))
    monkeypatch.setattr('gateway.session_commands._pre_command_before', observed)
    store, authority, head, _follower = await _local_session_with_unknown_head(tmp_path, monkeypatch, executed)
    viewer = AuthorityConnection(authority, Peer(), {'user_id': 'human'})
    try:
        await viewer.dispatch({'id': 1, 'method': 'session.resume', 'params': {'session_id': 's'}})
        wrong = await viewer.dispatch({'id': 2, 'method': 'slash.exec',
                                       'params': {'session_id': 's', 'command': '/discard not-a-lost-turn'}})
        assert wrong['result']['output'] == t('gateway.discard.nothing'), wrong
        assert _statuses(authority)[head.admission_id] == ('unknown', None)
        exact = await viewer.dispatch({'id': 3, 'method': 'slash.exec',
                                       'params': {'session_id': 's', 'command': f'/discard {head.admission_id}'}})
        assert exact['result']['output'] != t('gateway.discard.nothing'), exact
        assert _statuses(authority)[head.admission_id] == ('terminal', 'interrupted')
        # Plugins' pre_command observers see it although the fenced session is not idle.
        assert fired == [('discard', 'not-a-lost-turn'), ('discard', head.admission_id)]
    finally:
        await viewer.close()
        store.close_all_db_handles()


@pytest.mark.asyncio
async def test_typed_discard_needs_session_control(tmp_path, monkeypatch):
    executed = []
    store, authority, head, _follower = await _local_session_with_unknown_head(tmp_path, monkeypatch, executed)
    reader = AuthorityConnection(authority, Peer(), {'user_id': 'human',
                                                     'capabilities': ['session:read', 'session:submit']})
    try:
        await reader.dispatch({'id': 1, 'method': 'session.resume', 'params': {'session_id': 's'}})
        denied = await reader.dispatch({'id': 2, 'method': 'slash.exec',
                                        'params': {'session_id': 's', 'command': '/discard'}})
        assert denied['error']['message'] == 'permission_denied', denied
        live = authority.sessions['s']
        await async_wait_until(lambda: live.task is None or live.task.done(), what='no live drain')
        assert _statuses(authority)[head.admission_id] == ('unknown', None)
        assert executed == []
    finally:
        await reader.close()
        store.close_all_db_handles()
