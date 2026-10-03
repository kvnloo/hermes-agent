"""In-process group consumer: settled-discussion retry and thread progress.

Real group dispatch, coordinator, authority FIFO and publication; only an ambiguous
transport send and finite model execution are substituted. No sockets or providers.
"""
import asyncio
import json
import threading
import time
from types import SimpleNamespace

import pytest


def _wait(read, description, diagnostic=None):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        value = read()
        if value:
            return value
        threading.Event().wait(.02)
    raise AssertionError((description, diagnostic() if diagnostic else None))


@pytest.mark.parametrize('later_thread', ['thread-b', 'thread-a'])
def test_deferred_retry_preserves_thread_publication(tmp_path, monkeypatch, later_thread):
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    from gateway.session_authority import initialize_session_authority
    from gateway.session_contract import Principal
    from gateway.session_group_controls import dispatch_group_control
    from gateway.session_hosted_service import CanonicalHostedRoomService
    from gateway.session_hosted_rpc import HostedRoomAuthorityRPC
    from gateway import hosted_room_driver as tasks, session_finite
    from hermes_state import SessionDB
    from hermes_state_runtime import list_session_admissions

    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(home))
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    secondary = home / 'profiles' / 'two'
    secondary.mkdir(parents=True)
    (secondary / 'config.yaml').write_text('{}\n')
    (home / 'config.yaml').write_text(json.dumps({
        'model': {'default': 'fixture', 'provider': 'custom'},
        'terminal': {'cwd': str(home)},
        'platform_toolsets': {'cli': [], 'gui': [], 'bot_room': []},
        'hosted_rooms': {'profiles': {'two': str(secondary)}},
    }))
    store = SessionStore(home / 'sessions', GatewayConfig())
    store._db = SessionDB(home / 'state.db')
    runner = SimpleNamespace(session_store=store, _session_db=store._db,
        adapters={}, _draining=False, _cached_agent_for=lambda route: None)
    runner._adapter_for_source = lambda source: runner.adapters[source.platform]
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever)
    thread.start()
    service = None
    try:
        authority = asyncio.run_coroutine_threadsafe(initialize_session_authority(
            runner, profile_id=str(home), instance_id='retry-consumer'), loop).result(10)
        service = CanonicalHostedRoomService(authority, loop)
        authority.hosted_room_service = service
        actor = Principal('owner', str(home), frozenset({
            'session:create', 'session:read', 'session:submit', 'session:control',
            'session:approve'}), 'in-process-consumer')
        connection = SimpleNamespace(authority=authority, actor=actor)

        def call(method, **params):
            return asyncio.run_coroutine_threadsafe(
                dispatch_group_control(connection, method, params), loop).result(10)

        executed = []
        async def execute(authority, ref, row):
            identity, generation = json.loads(row['request_id'][7:])
            executed.append((identity, generation, row['payload'], row['admission_id']))
            return 'PASS recovered' if identity['thread_id'] == 'thread-a' and generation == 2 else 'PASS later'
        monkeypatch.setattr(session_finite, 'execute_finite_admission', execute)
        original_submit = HostedRoomAuthorityRPC.submit
        lost = threading.Event()
        def lose_first(self, **params):
            if not lost.is_set():
                lost.set()
                raise RuntimeError('transport lost before canonical admission')
            return original_submit(self, **params)
        monkeypatch.setattr(HostedRoomAuthorityRPC, 'submit', lose_first)
        offset = [0.0]
        service.runtime.clock = lambda: time.time() + offset[0]
        service.runtime.poll_interval_seconds = .05
        service.runtime.active_poll_interval_seconds = .02
        service.runtime.start()
        call('groups.create', room_id='room', name='Room', members=[
            {'member_id': 'one', 'profile': 'default', 'handle': 'one'},
            {'member_id': 'two', 'profile': 'two', 'handle': 'two'}])
        original = call('groups.send', room_id='room', event_id='original',
             payload={'text': '@one ORIGINAL', 'thread_id': 'thread-a'})
        assert lost.wait(10)
        first = _wait(lambda: next(iter(tasks.list_tasks(service.db_path, room_id='room')), None), 'original task')
        identity = first['identity']
        frozen = first['payload']
        _wait(lambda: service.runtime._ambiguous_rooms.get('room'), 'ambiguous transport recorded')
        offset[0] += 100
        service.runtime.wakeup()
        _wait(lambda: tasks.get_task(service.db_path, identity)['status'] == 'indeterminate', 'real lease recovery')
        offset[0] += 100
        service.runtime.wakeup()
        _wait(lambda: tasks.get_task(service.db_path, identity)['status'] == 'deferred', 'real deferred transition')
        _wait(lambda: any(e['kind'] == 'turn.deferred' and e['payload'].get('task_id') == identity.task_id
                         for e in service._events('room')), 'deferred outcome published')
        # This scenario starts after the old discussion completes. Concurrent new
        # same-thread send versus old room.activity is a separate observed race.
        _wait(lambda: any(e['kind'] == 'room.activity' and
                         e['payload'].get('discussion_event_id') == original['event']['event_id']
                         for e in service._events('room')), 'original discussion completed')
        rpc = next(iter(service.member_rpcs.values()))
        assert list_session_admissions(authority.db, session_id=rpc.ref.session_id, pending_only=False) == []
        assert not executed
        call('groups.send', room_id='room', event_id='later',
             payload={'text': '@one LATER', 'thread_id': later_thread})
        _wait(lambda: any(e['kind'] == 'message.member' and e['payload'].get('text') == 'PASS later'
                         for e in service._events('room')), 'later thread completes while original remains deferred',
              lambda: {'tasks': tasks.list_tasks(service.db_path, room_id='room'),
                       'events': service._events('room'), 'runtime': service.runtime.status(),
                       'executed': executed})
        assert tasks.get_task(service.db_path, identity)['status'] == 'deferred'
        receipt = call('groups.retry', room_id='room', member_id='one',
                       task_id=identity.task_id, execution_generation=1)
        assert receipt['retried'] and receipt['task']['execution_generation'] == 1
        assert receipt['task']['status'] == 'queued'
        _wait(lambda: tasks.get_task(service.db_path, identity)['status'] == 'settled', 'retry executes to settlement')
        _wait(lambda: any(e['kind'] in {'turn.settled', 'turn.cancelled'} and
                         e['payload'].get('task_id') == identity.task_id for e in service._events('room')), 'retry published')
        assert tasks.get_task(service.db_path, identity)['execution_generation'] == 2
        assert tasks.get_task(service.db_path, identity)['payload'] == frozen
        own = [item for item in executed if item[0]['task_id'] == identity.task_id]
        assert len(own) == 1 and own[0][1] == 2
        assert own[0][2]['text'] == frozen['prompt']
        later = [item for item in executed if item[0]['task_id'] != identity.task_id]
        assert len(later) == 1 and later[0][0]['thread_id'] == later_thread
        assert len(executed) == 2
        rows = list_session_admissions(authority.db, session_id=rpc.ref.session_id, pending_only=False)
        assert len(rows) == 2 and all(row['status'] == 'terminal' and row['outcome'] == 'completed' for row in rows)
        for _ in range(2):
            service.prepare_room(service.bindings()[0])
        events = call('groups.log', room_id='room')['events']
        later_replies = [e for e in events if e['kind'] == 'message.member'
                         and e['payload'].get('task_id') == later[0][0]['task_id']]
        assert len(later_replies) == 1
        assert later_replies[0]['payload']['thread_id'] == later_thread
        assert later_replies[0]['payload']['text'] == 'PASS later'
        terminal = [e for e in events if e['kind'] in {'turn.settled', 'turn.cancelled'}
                    and e['payload'].get('task_id') == identity.task_id]
        replies = [e for e in events if e['kind'] == 'message.member'
                   and e['payload'].get('task_id') == identity.task_id]
        assert len(terminal) == 1
        if later_thread == 'thread-b':
            assert terminal[0]['kind'] == 'turn.settled'
            assert len(replies) == 1 and replies[0]['payload']['text'] == 'PASS recovered'
        else:
            assert terminal[0]['kind'] == 'turn.cancelled'
            assert terminal[0]['payload']['reason'] == 'superseded_by_newer_user_event'
            assert replies == []
    finally:
        if service is not None:
            assert service.runtime.stop(timeout=10)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(10)
        assert not thread.is_alive()
        loop.close()
        store.close_all_db_handles()
