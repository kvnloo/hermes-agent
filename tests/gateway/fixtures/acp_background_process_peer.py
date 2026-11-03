"""Real gateway, real process, real ACP projection; no inference.

A ``GatewayACPAgent`` whose gateway RPCs go over the owner's actual WebSocket views a session that
owns a real background process (``exit 3`` after ~2 s). The editor connection is a recorder. The
``tool.complete`` frame is the exact one ``terminal(background=true)`` publishes (no model call can
issue it here); every later read is the live ``process.list``.
"""
import asyncio
import json
import os
from pathlib import Path
import shlex
import sys
import time
import traceback


class Recorder:
    def __init__(self):
        self.reports, self.t0 = [], time.monotonic()

    async def session_update(self, **_):
        return None

    async def ext_notification(self, method, params):
        self.reports.append({'method': method, 'at_s': round(time.monotonic() - self.t0, 2), **params})


class WsGateway:
    def __init__(self, ws, rpc):
        self.ws, self._rpc = ws, rpc

    async def rpc(self, method, **params):
        reply = await self._rpc(self.ws, method, **params)
        if 'error' in reply:
            raise RuntimeError(reply['error'])
        return reply['result']


async def probe():
    from acp_adapter import gateway_background
    from acp_adapter.gateway_server import GatewayACPAgent
    from gateway.run import GatewayRunner
    from gateway.session_authority import initialize_session_authority
    from gateway.run_api import start_gateway_api, stop_gateway_api
    from hermes_cli import web_server
    from hermes_cli.dashboard_auth.ws_tickets import mint_ticket
    from tests.gateway.fixtures.local_recovery_probe import rpc
    from tools.process_registry import process_registry
    from websockets.asyncio.client import connect

    gateway_background.POLL_SECONDS = 0.5
    home = Path(os.environ['HERMES_HOME'])
    (home / 'config.yaml').write_text('gateway:\n  multiplex_profiles: false\nmodel:\n  provider: custom\n  default: no-inference\n  base_url: http://127.0.0.1:1/v1\nauxiliary:\n  title_generation:\n    enabled: false\n')
    runner = GatewayRunner()
    authority = await initialize_session_authority(runner, profile_id=str(home), instance_id='acp-bg')
    api = await start_gateway_api(runner)
    web_server.app.state.auth_required = True
    receipt, proc = {}, None
    command = shlex.quote(sys.executable) + ' -c ' + shlex.quote('import time,sys; time.sleep(2); sys.exit(3)')
    try:
        ticket = mint_ticket(user_id='owner', provider='fixture')
        async with connect(api.api_origin.replace('http:', 'ws:') + '/api/ws?ticket=' + ticket) as ws:
            sid = (await rpc(ws, 'session.create', request_id='acp', source='acp', toolsets=[]))['result']['session_id']
            proc = process_registry.spawn_local(command, cwd=str(home), task_id=sid, owner_task_id=sid,
                                                session_key=authority.sessions[sid].route)
            editor = GatewayACPAgent()
            editor._snapshots[sid] = {}
            editor._gateway, editor._conn = WsGateway(ws, rpc), Recorder()
            result = json.dumps({'output': 'Background process started', 'session_id': proc.id, 'pid': proc.pid,
                                 'exit_code': 0, 'error': None})
            for kind, payload in (('tool.start', {'tool_call_id': 'call_1', 'tool_name': 'terminal',
                                                  'args': {'command': 'sleep 2; exit 3', 'background': True}}),
                                  ('tool.complete', {'tool_call_id': 'call_1', 'tool_name': 'terminal',
                                                     'result': result, 'is_error': False})):
                await editor._project({'session_id': sid, 'type': kind, 'admission_id': 'a', 'payload': payload})
            receipt['listed_while_running'] = [r.get('status') for r in
                                               (await rpc(ws, 'process.list', session_id=sid))['result']['processes']]
            await asyncio.wait_for(asyncio.gather(*editor._bg_watchers.values()), 15)
            receipt['process_exit_code'] = proc.exit_code
            receipt['reports'] = editor._conn.reports
    finally:
        if proc is not None and not proc.exited:
            process_registry.kill_process(proc.id)
        await stop_gateway_api(api)
    (home / 'receipt.json').write_text(json.dumps(receipt))


if __name__ == '__main__':
    status = 0
    try:
        asyncio.run(probe())
    except BaseException:
        traceback.print_exc()
        status = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(status)
