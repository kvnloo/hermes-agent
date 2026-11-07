"""#342: the owner launches a sandboxed profile's managed worker inside its boundary.

- the spawn wraps exactly the ``agent.managed_worker`` exec (no new protocol, same pipes);
- a profile that asks for a boundary the host cannot build is refused by name, never run bare;
- the owner proves the identity of a worker that lives in its own pid namespace (its hello
  reports the namespace pid; the owner maps it to the host pid through ``NSpid``);
- the hidden-paths notice reaches the worker's system context.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gateway import session_managed_worker as smw
from gateway import worker_sandbox as ws

needs_bwrap = pytest.mark.skipif(sys.platform != 'linux' or not shutil.which('bwrap'), reason='bwrap (Linux) only')


def _authority(home):
    return SimpleNamespace(profile_id=str(home), pending_results={}, pending_stop_causes={})


def _row():
    return {'admission_id': 'adm1', 'generation': 1, 'payload': {'finite': True}}


def _spawn(monkeypatch, home):
    calls = []

    async def fake_acquire(popen, argv, **kwargs):
        calls.append((argv, kwargs))
        raise asyncio.CancelledError  # stop right after the exec decision; no child is started

    monkeypatch.setattr('gateway.session_worker_spawn.acquire_process', fake_acquire)
    monkeypatch.setattr(smw, '_worker_env', lambda authority, scoped=False: {'HERMES_HOME': str(home), 'SCOPED': str(scoped)})
    monkeypatch.setattr('gateway.session_managed_worker_log.worker_log_path', lambda profile: None)
    authority = _authority(home)
    out = asyncio.run(smw._spawn_registered_worker(authority, SimpleNamespace(session_id='s1'), _row()))
    return out, calls, authority


def test_unsandboxed_profile_spawns_exactly_as_before(tmp_path, monkeypatch):
    out, calls, _ = _spawn(monkeypatch, tmp_path)
    assert out is None and calls[0][0] == [sys.executable, '-m', 'agent.managed_worker']


def test_sandboxed_profile_spawn_is_wrapped_in_bwrap(tmp_path, monkeypatch):
    (tmp_path / 'sandbox.yaml').write_text('enabled: true\n')
    monkeypatch.setattr(ws.shutil, 'which', lambda name: '/usr/bin/bwrap')
    _, calls, _ = _spawn(monkeypatch, tmp_path)
    argv, kwargs = calls[0]
    assert argv[0] == '/usr/bin/bwrap' and argv[-3:] == [sys.executable, '-m', 'agent.managed_worker']
    assert argv[argv.index('--bind') + 1] == str(tmp_path)  # the live home, in place
    assert ws.NOTICE_ENV in kwargs['env'] and kwargs['stdin'] == subprocess.PIPE
    assert kwargs['env']['SCOPED'] == 'True'  # own profile scope, never the launch environ


def test_sandbox_unavailable_refuses_the_turn_by_name(tmp_path, monkeypatch):
    (tmp_path / 'sandbox.yaml').write_text('enabled: true\n')
    monkeypatch.setattr(ws.shutil, 'which', lambda name: None)
    out, calls, authority = _spawn(monkeypatch, tmp_path)
    assert out is None and calls == []  # nothing ran, sandboxed or not
    result = authority.pending_results['adm1']['result']
    assert result['failed'] is True and result['failure_reason'] == 'sandbox_unavailable'
    assert 'bwrap is not installed' in result['error']


def test_notice_reaches_the_worker_system_context(monkeypatch):
    monkeypatch.delenv(ws.NOTICE_ENV, raising=False)
    assert ws.with_notice('skills') == 'skills' and ws.with_notice(None) is None
    monkeypatch.setenv(ws.NOTICE_ENV, '## SANDBOX BOUNDARY\n- /x')
    assert ws.with_notice('skills') == 'skills\n\n## SANDBOX BOUNDARY\n- /x'
    assert ws.with_notice(None) == '## SANDBOX BOUNDARY\n- /x'


@needs_bwrap
def test_owner_verifies_a_worker_in_its_own_pid_namespace():
    from gateway.session_worker_reservation import verify_worker_identity
    child = ('import json, sys, psutil, time\n'
             'from hermes_cli.process_identity import worker_birth\n'
             'me = psutil.Process()\n'
             'print(json.dumps({"type": "hello", "pid": me.pid, "birth": worker_birth(me), "ancestors": []}), flush=True)\n'
             'time.sleep(30)\n')
    root = str(Path(smw.__file__).resolve().parents[1])
    argv = [shutil.which('bwrap'), '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc', '--unshare-pid',
            '--die-with-parent', '--new-session', '--chdir', root, '--', sys.executable, '-c', child]
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, start_new_session=True)
    try:
        hello = json.loads(process.stdout.readline())
        assert hello['pid'] < 10  # the namespace pid, meaningless on the host
        pid, birth = verify_worker_identity(process, hello)
        assert pid != hello['pid'] and birth == hello['birth']
        status = Path(f'/proc/{pid}/status').read_text()
        assert next(line for line in status.splitlines() if line.startswith('NSpid:')).split()[-1] == str(hello['pid'])
        forged = {**hello, 'pid': hello['pid'] + 50}
        with pytest.raises(Exception, match='permission_denied|worker_not_live'):
            verify_worker_identity(process, forged)
    finally:
        os.killpg(process.pid, 9)
        process.wait(10)


def test_worker_adopts_the_owner_pid_only_in_its_own_pid_namespace(monkeypatch):
    monkeypatch.setattr(ws, '_host_pid', None)
    monkeypatch.delenv(ws.PID_NS_ENV, raising=False)
    assert ws.accept_owner_pid(os.getpid()) and not ws.accept_owner_pid(os.getpid() + 1)
    assert ws.owner_visible_pid() == os.getpid()
    monkeypatch.setenv(ws.PID_NS_ENV, '1')
    assert not ws.accept_owner_pid('7') and ws.accept_owner_pid(424242)
    assert ws.owner_visible_pid() == 424242
