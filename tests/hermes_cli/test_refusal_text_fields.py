"""A canonical-contract refusal (``gateway/session_controls.py``) names its keys in ``data.fields``
(a list), not ``field``. The client must show them: a sandboxed one-shot whose inherited
``HERMES_SESSION_SOURCE=kanban`` was refused printed a bare ``invalid_params`` (A19 canary, 2026-11-07)."""
from hermes_cli.cli_chat_error_copy import agent_init_failure_message, refusal_text
from hermes_cli.gateway_client import GatewayRPCError, rpc_error


def test_canonical_refusal_names_its_fields():
    refused = rpc_error({'code': 4001, 'message': 'invalid_params',
                         'data': {'reason': 'invalid_params', 'fields': ['source']}})
    assert refusal_text(refused) == 'invalid_params (source)'
    assert 'invalid_params (source)' in agent_init_failure_message(refused)


def test_several_fields_and_singular_field_unchanged():
    assert refusal_text(GatewayRPCError('invalid_params', data={'fields': ['source', 'cwd']})) == \
        'invalid_params (source, cwd)'
    assert refusal_text(GatewayRPCError('invalid_params', data={'field': 'toolsets', 'detail': 'bad'})) == \
        'invalid_params (toolsets: bad)'
    assert refusal_text(GatewayRPCError('invalid_params')) == 'invalid_params'
