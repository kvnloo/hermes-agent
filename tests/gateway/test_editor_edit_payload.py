"""Large ACP edits must not disconnect approval or its reconnect snapshot."""
import asyncio
import json
from dataclasses import asdict

import pytest
from websockets.asyncio.server import serve

from acp_adapter.edit_approval import EditProposal, build_acp_edit_tool_call
from gateway.session_local_editor import request_editor_edit
from hermes_cli.gateway_client import connect_gateway
from tools import approval
from tools import approval_context, approval_gateway_wait


def proposal(tmp_path):
    # The proposal repeats the replacement in arguments, as a real write_file does.
    old = 'a' * (3 * 1024 * 1024)
    new = 'b' * (3 * 1024 * 1024)
    target = tmp_path / 'repos.json'
    target.write_text(old)
    return EditProposal('write_file', str(target), old, new,
                        {'path': str(target), 'content': new})


def test_direct_acp_large_edit_is_explicitly_a_preview(tmp_path):
    edit = proposal(tmp_path)
    call = build_acp_edit_tool_call(edit)
    encoded = call.model_dump_json(by_alias=True)
    assert len(encoded.encode()) < 1024 * 1024
    assert 'truncated' in encoded.lower()
    assert edit.new_text == edit.arguments['content']
    assert len(edit.new_text) == 3 * 1024 * 1024


@pytest.mark.parametrize('choice', ['once', 'deny'])
def test_large_edit_approval_and_reconnect_fit_existing_socket_limit(tmp_path, monkeypatch, choice):
    edit = proposal(tmp_path)
    original = asdict(edit)
    route = 'editor-payload-test'
    monkeypatch.setattr(approval_context, 'get_current_session_key', lambda: route)
    monkeypatch.setitem(approval._gateway_notify_cbs, route, lambda data: None)

    async def roundtrip(data):
        async def handler(ws):
            async for raw in ws:
                request = json.loads(raw)
                # Both the live approval event and reconnect include the same pending card.
                await ws.send(json.dumps({'jsonrpc': '2.0', 'method': 'event',
                                          'params': {'type': 'approval', 'payload': data}}))
                await ws.send(json.dumps({'jsonrpc': '2.0', 'id': request['id'],
                                          'result': {'prompts': [data]}}))
        async with serve(handler, '127.0.0.1', 0) as server:
            port = next(iter(server.sockets)).getsockname()[1]
            monkeypatch.setenv('HERMES_TUI_GATEWAY_URL', f'ws://127.0.0.1:{port}')
            async with connect_gateway() as client:
                snapshot = await client.rpc('session.resume', session_id='editor')
                event = await client.events.get()
                assert snapshot['prompts'][0]['edit'] == event['params']['payload']['edit']
                return snapshot['prompts'][0]

    def decide(_route, _notify, data, **kwargs):
        # Consent has not been received: even a large edit must still be pending.
        assert (tmp_path / 'repos.json').read_text() == edit.old_text
        received = asyncio.run(roundtrip(data))
        assert received['allow_session'] is False
        assert received['allow_permanent'] is False
        assert 'truncated' in received['edit']['new_text'].lower()
        # The gateway card must still reconstruct as an ACP edit permission, not a generic command.
        call = build_acp_edit_tool_call(EditProposal(**received['edit']))
        assert call.kind == 'edit'
        return {'resolved': True, 'choice': choice}

    monkeypatch.setattr(approval_gateway_wait, '_await_gateway_decision', decide)
    assert request_editor_edit(edit) is (choice == 'once')
    assert asdict(edit) == original
    assert (tmp_path / 'repos.json').read_text() == edit.old_text


@pytest.mark.parametrize('choice', ['once', 'deny'])
def test_large_write_executes_full_content_only_after_consent(tmp_path, monkeypatch, choice):
    from acp_adapter.edit_approval import reset_edit_approval_requester, set_edit_approval_requester
    from model_tools import handle_function_call

    target = tmp_path / 'approved.txt'
    content = 'payload\n' * (400 * 1024)
    route = 'editor-full-write-test'
    monkeypatch.setattr(approval_context, 'get_current_session_key', lambda: route)
    monkeypatch.setitem(approval._gateway_notify_cbs, route, lambda data: None)
    cards = []

    def decide(_route, _notify, data, **kwargs):
        assert not target.exists()
        cards.append(data)
        return {'resolved': True, 'choice': choice}

    monkeypatch.setattr(approval_gateway_wait, '_await_gateway_decision', decide)
    token = set_edit_approval_requester(lambda edit: bool(request_editor_edit(edit)))
    try:
        result = json.loads(handle_function_call('write_file', {'path': str(target), 'content': content},
                                                 task_id='editor-full-write-test'))
    finally:
        reset_edit_approval_requester(token)
    assert len(cards) == 1
    assert len(json.dumps(cards).encode()) < 1024 * 1024
    if choice == 'once':
        assert 'error' not in result
        assert target.read_text() == content
    else:
        assert 'Edit approval denied' in result['error']
        assert not target.exists()

