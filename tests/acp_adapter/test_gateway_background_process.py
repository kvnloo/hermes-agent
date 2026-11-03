"""Background processes on the gateway path reach ACP clients as ``_hermes/process`` (#130898's wire
shape): ``running`` when a ``terminal`` call starts one, ``exited`` once ``process.list`` (Desktop's
status-stack source) shows it finished."""
import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from acp_adapter import gateway_background
from acp_adapter.gateway_server import GatewayACPAgent
from tests.waiting import async_wait_until

STARTED = json.dumps({"output": "Background process started", "session_id": "proc_1", "pid": 42,
                      "exit_code": 0, "error": None})


def agent(rows):
    agent = GatewayACPAgent()
    agent._snapshots['s'] = {}
    agent._gateway = AsyncMock()
    agent._gateway.rpc.side_effect = lambda method, **params: {"processes": list(rows)}
    agent._conn = AsyncMock()
    return agent


async def project(agent, kind, payload):
    await agent._project({'session_id': 's', 'type': kind, 'admission_id': 'a', 'payload': payload})


async def start(editor, call='c1', result=STARTED, name='terminal'):
    await project(editor, 'tool.start', {'tool_call_id': call, 'tool_name': name,
                                         'args': {'command': 'sleep 60', 'background': True}})
    await project(editor, 'tool.complete', {'tool_call_id': call, 'tool_name': name, 'result': result})


def reports(editor):
    return [(c.args[0], c.args[1]) for c in editor._conn.ext_notification.await_args_list]


@pytest.mark.asyncio
async def test_background_terminal_reports_running_then_exited(monkeypatch):
    monkeypatch.setattr(gateway_background, 'POLL_SECONDS', 0.01)
    rows = [{'session_id': 'proc_1', 'status': 'running'}]
    editor = agent(rows)
    await start(editor)
    assert reports(editor) == [('hermes/process', {'sessionId': editor._editor_id('s'), 'toolCallId': 'c1',
                                                   'processId': 'proc_1', 'command': 'sleep 60',
                                                   'status': 'running'})]
    await async_wait_until(lambda: editor._gateway.rpc.call_count >= 2, timeout=2)
    assert len(reports(editor)) == 1, 'still running: no second report'
    rows[0] = {'session_id': 'proc_1', 'status': 'exited', 'exit_code': 3, 'completion_reason': 'exited'}
    await asyncio.wait_for(asyncio.gather(*editor._bg_watchers.values()), 2)
    method, exited = reports(editor)[-1]
    assert (method, exited['status'], exited['exitCode'], exited['reason'], exited['toolCallId']) == \
        ('hermes/process', 'exited', 3, 'exited', 'c1')
    assert not editor._bg_live and not editor._background


@pytest.mark.asyncio
async def test_a_process_pruned_from_the_list_reports_lost(monkeypatch):
    monkeypatch.setattr(gateway_background, 'POLL_SECONDS', 0.01)
    rows = []
    editor = agent(rows)
    await start(editor)
    await asyncio.wait_for(asyncio.gather(*editor._bg_watchers.values()), 2)
    assert reports(editor)[-1][1]['reason'] == 'lost'


@pytest.mark.asyncio
async def test_terminal_output_rereads_without_waiting_for_the_tick(monkeypatch):
    monkeypatch.setattr(gateway_background, 'POLL_SECONDS', 60)
    rows = [{'session_id': 'proc_1', 'status': 'running'}]
    editor = agent(rows)
    await start(editor)
    rows[0] = {'session_id': 'proc_1', 'status': 'exited', 'exit_code': 0, 'completion_reason': 'exited'}
    await project(editor, 'agent.terminal.output', {'process_id': 'proc_1', 'chunk': 'done\n'})
    await asyncio.wait_for(asyncio.gather(*editor._bg_watchers.values()), 2)
    assert reports(editor)[-1][1]['status'] == 'exited'


@pytest.mark.asyncio
@pytest.mark.parametrize('name,result,is_error', [
    ('terminal', json.dumps({'output': 'hi', 'exit_code': 0, 'error': None}), False),  # foreground
    ('read_file', STARTED, False),
    ('terminal', STARTED, True),
])
async def test_only_a_started_background_process_is_reported(name, result, is_error):
    editor = agent([])
    await project(editor, 'tool.start', {'tool_call_id': 'c', 'tool_name': name, 'args': {}})
    await project(editor, 'tool.complete', {'tool_call_id': 'c', 'tool_name': name, 'result': result,
                                            'is_error': is_error})
    assert reports(editor) == []
