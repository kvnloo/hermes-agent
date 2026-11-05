"""The same file is installed beside the intake profile's neighboring plugin tests."""
import copy
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import sys
import threading

import pytest

HERE = Path(__file__).resolve()
SOURCE = HERE.parents[2] / 'plugins'
sys.path.insert(0, str(SOURCE if (SOURCE / 'intake_ledger_match').exists() else HERE.parent))

from intake_ledger_match import Observer, message_text
from intake_ledger_match.matcher import match, update_ledger


@pytest.fixture
def ledger(tmp_path):
    path = tmp_path / 'ledger.json'
    path.write_text(json.dumps([{'id': 'R01', 'ask': 'Repair broken glass background opacity',
                                'check': 'Settings transparency toggles immediately',
                                'status': 'in-progress', 'extra': {'keep': True}}]))
    return path


def rows(path):
    return json.loads(path.read_text())


def test_match_preserves_fields_and_deduplicates(ledger):
    assert update_ledger(ledger, 'm1', 'R01 please fix it')['action'] == 'match'
    assert update_ledger(ledger, 'm1', 'different text')['action'] == 'duplicate'
    row = rows(ledger)[0]
    assert row['mentions'] == ['m1']
    assert row['status'] == 'in-progress'
    assert row['extra'] == {'keep': True}


def test_new_id_uses_max_not_count_and_is_idempotent(ledger):
    value = rows(ledger) + [{'id': 'I042', 'ask': 'Build a bicycle shed'}]
    ledger.write_text(json.dumps(value))
    result = update_ledger(ledger, 'm2', 'Track penguin migration across Antarctica')
    assert result['row_id'] == 'I043'
    assert result['action'] == 'new'
    row = rows(ledger)[-1]
    assert row['source_msg_id'] == 'm2' and row['owner'] == 'ayo' and row['status'] == 'open'
    assert update_ledger(ledger, 'm2', 'Track penguin migration')['action'] == 'duplicate'


def test_new_row_can_be_rendered_by_existing_ayo_renderer(ledger):
    update_ledger(ledger, 'new-renderable', 'Track penguin migration across Antarctica')
    row = rows(ledger)[-1]
    # render_ledger.py indexes these fields on every row, including new intake asks.
    assert (row['check'], row['evidence'], row['note']) == ('', '', '')


def test_lexical_embedding_match_and_abstention(ledger):
    value = rows(ledger)
    assert match('Fix broken glass background opacity settings', value)[0] == 'R01'
    assert match('yeah can you do it please', value)[0] is None
    original = copy.deepcopy(value)
    match('glass', value)
    assert value == original


def test_parallel_writers_no_lost_mentions_or_new_ids(ledger):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda n: update_ledger(ledger, f'm{n}', 'R01'), range(24)))
    assert set(rows(ledger)[0]['mentions']) == {f'm{n}' for n in range(24)}
    assert len(rows(ledger)[0]['mentions']) == 24


def test_independent_process_writers(ledger):
    import subprocess
    source = str(Path(__import__('intake_ledger_match').__file__).parent.parent)
    code = ('import sys; sys.path.insert(0,sys.argv[1]); from pathlib import Path; '
            'from intake_ledger_match.matcher import update_ledger; '
            'update_ledger(Path(sys.argv[2]),sys.argv[3],"R01")')
    children = [subprocess.Popen([sys.executable, '-c', code, source, str(ledger), f'p{n}']) for n in range(6)]
    assert [child.wait(timeout=15) for child in children] == [0] * 6
    assert set(rows(ledger)[0]['mentions']) == {f'p{n}' for n in range(6)}


def test_reads_after_lock_not_before(ledger):
    with ledger.with_suffix('.json.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(update_ledger, ledger, 'late', 'R01')
            current = rows(ledger)
            current[0]['status'] = 'done'
            ledger.write_text(json.dumps(current))
            fcntl.flock(lock, fcntl.LOCK_UN)
            assert future.result(timeout=10)['row_id'] == 'R01'
    assert rows(ledger)[0]['status'] == 'done'


def test_replace_failure_keeps_original_and_cleans_temp(ledger, monkeypatch):
    import intake_ledger_match.matcher as module
    old = ledger.read_bytes()
    def fail(*args):
        raise OSError('replace failed')
    monkeypatch.setattr(module.os, 'replace', fail)
    with pytest.raises(OSError):
        update_ledger(ledger, 'm3', 'R01')
    assert ledger.read_bytes() == old
    assert not list(ledger.parent.glob('.ledger.json.*'))


def test_noncooperating_writer_detected(ledger, monkeypatch):
    import intake_ledger_match.matcher as module
    original = module.match
    def concurrent(text, value):
        changed = rows(ledger)
        changed[0]['status'] = 'external-edit'
        ledger.write_text(json.dumps(changed))
        return original(text, value)
    monkeypatch.setattr(module, 'match', concurrent)
    with pytest.raises(RuntimeError):
        update_ledger(ledger, 'm4', 'R01')
    assert rows(ledger)[0]['status'] == 'external-edit'


def test_invalid_ledger_never_overwritten(ledger):
    ledger.write_text('{broken')
    with pytest.raises(ValueError):
        update_ledger(ledger, 'm5', 'R01')
    assert ledger.read_text() == '{broken'


def test_lock_timeout(ledger):
    with ledger.with_suffix('.json.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with pytest.raises(TimeoutError):
            update_ledger(ledger, 'm6', 'R01', lock_timeout=0)


def test_hook_never_waits_or_mutates_payload(ledger, tmp_path, monkeypatch):
    import intake_ledger_match as module
    entered, release, returned = threading.Event(), threading.Event(), threading.Event()
    def slow(*args):
        entered.set()
        assert release.wait(10)
        return {'action': 'test'}
    monkeypatch.setattr(module, 'update_ledger', slow)
    observer = Observer(ledger, tmp_path / 'logs' / 'ledger-match.log', 'owner')
    payload = {'user_message': 'R01', 'turn_id': 'turn-1', 'conversation_history': [{'role': 'user', 'content': 'R01'}]}
    before = copy.deepcopy(payload)
    def invoke():
        assert observer.pre_llm_call(**payload) is None
        returned.set()
    caller = threading.Thread(target=invoke)
    caller.start()
    try:
        assert entered.wait(5)
        assert returned.wait(2)
        assert payload == before
    finally:
        release.set()
        caller.join(10)
        observer.drain()


def test_worker_fails_open_and_logs_error(ledger, tmp_path):
    ledger.write_text('invalid')
    log = tmp_path / 'ledger-match.log'
    observer = Observer(ledger, log, 'owner')
    assert observer.pre_llm_call(user_message='R01', turn_id='error-turn') is None
    observer.drain()
    assert '"event": "error"' in log.read_text()
    assert 'JSONDecodeError' in log.read_text()


@pytest.mark.parametrize('payload', [
    {'role': 'assistant'}, {'role': 'tool'}, {'parent_session_id': 'parent'},
    {'platform': 'telegram', 'sender_id': 'stranger'}, {'platform': 'telegram'},
])
def test_only_owner_user_turns(ledger, tmp_path, payload):
    observer = Observer(ledger, tmp_path / 'log', 'owner')
    observer.pre_llm_call(user_message='R01', turn_id='skip', **payload)
    observer.drain()
    assert 'mentions' not in rows(ledger)[0]


def test_actual_core_payload_uses_turn_identity(ledger, tmp_path):
    observer = Observer(ledger, tmp_path / 'log', 'owner')
    observer.pre_llm_call(user_message='R01', session_id='session', turn_id='real-core-turn',
                          task_id='task', conversation_history=[], is_first_turn=True,
                          model='test', platform='telegram', sender_id='owner')
    observer.drain()
    assert rows(ledger)[0]['mentions'] == ['real-core-turn']


def test_native_message_id_is_preserved_across_retries(ledger, tmp_path):
    observer = Observer(ledger, tmp_path / 'log', 'owner')
    for turn in ('attempt-1', 'attempt-2'):
        observer.pre_llm_call(user_message='R01', source_msg_id='native-42', turn_id=turn)
    observer.drain()
    assert rows(ledger)[0]['mentions'] == ['native-42']


def test_missing_identity_and_unwritable_log_fail_open(ledger, tmp_path):
    observer = Observer(ledger, tmp_path, 'owner')
    assert observer.pre_llm_call(user_message='R01') is None
    assert 'mentions' not in rows(ledger)[0]


def test_multimodal_text_only():
    assert message_text([{'type': 'image_url', 'image_url': 'private'},
                         {'type': 'text', 'text': 'R01'}]) == 'R01'
