"""#342 steps 3-5 on a real gateway: a sandboxed profile's managed worker cannot read another
profile, its secrets or the host environment; the hidden-paths notice reaches the model; the
policy is re-read at each launch; a killed worker fails the turn instead of hanging it; and a
gateway death leaves no worker behind.

The fixture lives under /var/tmp: the boundary replaces /tmp with a tmpfs, which would make every
"hidden" check pass vacuously.
"""
import asyncio
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import sys
import tempfile
import threading
import time

import pytest

from tests.waiting import async_wait_until

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = 'host-env-sentinel-342'
SYSTEMS = []  # system prompt of every model request, in order


def _probe(home, b, bws, ops):
    checks = ' '.join(f'{p}' for p in (b / 'state.db', b / 'skills' / 's1' / 'SKILL.md', b / '.env', bws / 'token'))
    return (f'for p in {checks}; do test -e "$p" && echo "SEEN $p" || echo GONE; done; '
            f'echo "OWN $(head -c 6 {home}/config.yaml)"; '
            f'echo "ENVRO $([ -w {home}/.env ] && echo W || echo RO)"; '
            f'echo "HOSTENV $(cat /proc/[0-9]*/environ 2>/dev/null | tr \'\\0\' \'\\n\' | grep -c {SENTINEL})"; '
            f'echo "OPS $(touch {ops}/w && echo ok)"')


class Model(BaseHTTPRequestHandler):
    probe = ''

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        messages = body.get('messages') or [{'role': 'system'}]
        SYSTEMS.append(next((m.get('content') or '' for m in messages if m['role'] == 'system'), ''))
        last = messages[-1]
        if last['role'] == 'user' and last.get('content') == 'SLOW':
            time.sleep(60)
        call = last['role'] == 'user' and last.get('content') == 'PROBE'
        message = ({'role': 'assistant', 'content': None, 'tool_calls': [{'id': f'c{len(messages)}', 'index': 0,
                    'type': 'function', 'function': {'name': 'terminal', 'arguments': json.dumps({'command': self.probe})}}]}
                   if call else {'role': 'assistant', 'content': 'OK'})
        choice = {'index': 0, 'delta': message, 'finish_reason': 'tool_calls' if call else 'stop'}
        frame = {'id': 'sbx', 'model': 'm', 'choices': [choice], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}
        if body.get('stream'):
            payload, kind = ('data: ' + json.dumps(frame) + '\n\ndata: [DONE]\n\n').encode(), 'text/event-stream'
        else:
            choice['message'] = choice.pop('delta')
            payload, kind = json.dumps(frame).encode(), 'application/json'
        try:
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except OSError:
            pass


def _workers(home):
    """Host pids of sandboxed managed workers for *home* (bwrap argv names the home)."""
    out = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            argv = (proc / 'cmdline').read_bytes().split(b'\0')
        except OSError:
            continue
        if b'agent.managed_worker' in argv and any(Path(a.decode(errors='replace')).name == 'bwrap' for a in argv[:1]) \
                and str(home).encode() in argv:
            out.append(int(proc.name))
    return out


@pytest.mark.platforms('linux')
@pytest.mark.live_system_guard_bypass  # SIGKILLs the sandboxed worker this test's own gateway spawned
@pytest.mark.skipif(not shutil.which('bwrap'), reason='bwrap only')
def test_sandboxed_managed_worker_on_a_real_gateway():
    from tests.gateway.fixtures.local_recovery_probe import daemon, rpc, websocket
    base = Path(tempfile.mkdtemp(prefix='sbx342-e2e-', dir='/var/tmp'))
    home, user, bws, ops = base / 'state', base / 'user', base / 'bws', base / 'ops'
    home.mkdir(mode=0o700)
    for d in (user, bws, ops):
        d.mkdir()
    (user / '.hushlogin').touch()
    b = home / 'profiles' / 'b'
    (b / 'skills' / 's1').mkdir(parents=True)
    (b / 'skills' / 's1' / 'SKILL.md').write_text('x')
    (b / 'state.db').write_bytes(b'SQLite format 3\0')
    (b / '.env').write_text('B_SECRET=b-sentinel\n')
    (bws / 'token').write_text('TOKEN=fixture\n')
    (home / '.env').write_text('FIXTURE=1\n')
    peer = ThreadingHTTPServer(('127.0.0.1', 0), Model)
    threading.Thread(target=peer.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{peer.server_port}/v1'
    Model.probe = _probe(home, b, bws, ops)
    (home / 'config.yaml').write_text(json.dumps({
        'gateway': {'multiplex_profiles': False, 'managed_workers': True},
        'model': {'provider': 'custom', 'default': 'm', 'base_url': url},
        'auxiliary': {'title_generation': {'enabled': False}}, 'approvals': {'mode': 'off'},
        'platform_toolsets': {'cli': ['terminal']}}))
    policy = f'hidden: [{bws}]\nrw: [{ops}]\n'
    (home / 'sandbox.yaml').write_text('enabled: true\n' + policy)
    env = {k: os.environ[k] for k in ('LANG', 'TZ', 'PATH') if k in os.environ}
    env.update(HOME=str(user), HERMES_HOME=str(home), PYTHONPATH=str(ROOT), OPENAI_API_KEY='loopback-only',
               OPENAI_BASE_URL=url, ANTHROPIC_API_KEY=SENTINEL, XDG_RUNTIME_DIR=str(base))

    def status(request_id):
        with closing(sqlite3.connect(f'file:{home / "state.db"}?mode=ro', uri=True)) as db:
            rows = db.execute('SELECT status FROM session_admissions WHERE request_id=?', (request_id,)).fetchall()
            return rows[0][0] if rows else None

    async def turn(ws, name, text, *, settle=True):
        created = await rpc(ws, 'session.create', request_id=name, source='cli', cwd=str(home), model='m',
                            provider='custom', base_url=url, api_key='loopback-only', toolsets=['terminal'],
                            ignore_rules=True)
        assert 'result' in created, created
        sid = created['result']['session_id']
        assert 'result' in await rpc(ws, 'prompt.submit', session_id=sid, input_id=f'in-{name}', text=text)
        if settle:
            await async_wait_until(lambda: status(f'in-{name}') == 'terminal', timeout=120, interval=.1,
                                   what=f'{name} to settle')
        return sid

    async def tool_output(ws, sid):
        messages = (await rpc(ws, 'session.resume', session_id=sid))['result']['messages']
        return json.loads([m['content'] for m in messages if m['role'] == 'tool'][-1])['output']

    async def exercise(desc, gateway_pid):
        found = {}
        async with websocket(home, desc) as ws:
            n = len(SYSTEMS)
            sid = await turn(ws, 'sandboxed', 'PROBE')
            found['sandboxed'] = await tool_output(ws, sid)
            found['notice'] = [s for s in SYSTEMS[n:] if 'SANDBOX BOUNDARY' in s]
            found['sid'] = sid
            # Invariant 1: re-read per launch. The same gateway, policy switched off: B is visible again.
            (home / 'sandbox.yaml').write_text('enabled: false\n' + policy)
            n = len(SYSTEMS)
            found['open'] = await tool_output(ws, await turn(ws, 'open', 'PROBE'))
            found['open_notice'] = [s for s in SYSTEMS[n:] if 'SANDBOX BOUNDARY' in s]
            (home / 'sandbox.yaml').write_text('enabled: true\n' + policy)
            # Step 5: a killed worker fails its turn; it never hangs.
            await turn(ws, 'killed', 'SLOW', settle=False)
            await async_wait_until(lambda: _workers(home), timeout=60, interval=.1, what='sandboxed worker')
            for pid in _workers(home):
                os.kill(pid, signal.SIGKILL)
            # The owner settles a lost worker as ``unknown`` ("Worker execution is unknown."): a
            # reported outcome that parks followers, never a turn left running.
            await async_wait_until(lambda: status('in-killed') in ('terminal', 'unknown'), timeout=60, interval=.2,
                                   what='killed turn to settle')
            found['killed'] = status('in-killed')
            # Then one more slow worker (a fresh session: the killed one parks its followers), left
            # running for the gateway-death check below.
            await turn(ws, 'orphan', 'SLOW', settle=False)
            await async_wait_until(lambda: _workers(home), timeout=60, interval=.1, what='second worker')
            found['live_workers'] = _workers(home)
        return found

    try:
        with daemon(ROOT, home, env, barrier=False) as (owner, desc):
            found = asyncio.run(exercise(desc, owner.pid))
        deadline = time.monotonic() + 15  # the daemon fixture SIGKILLs the gateway on exit
        while _workers(home) and time.monotonic() < deadline:
            time.sleep(.2)
        orphans = _workers(home)
    finally:
        peer.shutdown()
        peer.server_close()
    try:
        lines = found['sandboxed'].strip().splitlines()
        assert lines[:4] == ['GONE'] * 4, found['sandboxed']  # B's state.db, skills, .env; the hidden secret dir
        assert 'OWN {"gat' in found['sandboxed'] and 'ENVRO RO' in found['sandboxed'], found['sandboxed']
        assert 'HOSTENV 0' in found['sandboxed'] and 'OPS ok' in found['sandboxed'], found['sandboxed']
        assert found['notice'], 'the hidden-paths notice never reached the model'
        assert found['open'].count('SEEN ') == 4 and not found['open_notice'], found['open']
        logs = ' '.join(p.read_text(errors='replace') for p in (home / 'logs').glob('*.log'))
        assert found['sid'] in logs  # the turn is in the sandboxed profile's own logs
        assert found['live_workers'] and orphans == [], (found['live_workers'], orphans)
    finally:
        shutil.rmtree(base, ignore_errors=True)
