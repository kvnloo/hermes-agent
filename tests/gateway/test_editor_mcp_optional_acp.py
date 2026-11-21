"""Regression for NousResearch/hermes-agent#150409: editor MCP needs the optional ACP extra."""
import builtins

import pytest

from gateway.session_local_mcp import private_mutation_payload, validate_servers
from hermes_state_runtime import RuntimeStoreError


def _make_acp_import_fail(monkeypatch, missing):
    original_import = builtins.__import__

    def import_without_acp(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'acp.schema':
            raise ModuleNotFoundError(f"No module named '{missing}'", name=missing)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', import_without_acp)


def test_missing_acp_extra_is_actionable_in_editor_mcp_mutation(monkeypatch):
    _make_acp_import_fail(monkeypatch, 'acp')
    with pytest.raises(RuntimeStoreError) as caught:
        private_mutation_payload('editor_mcp', {'mcp_servers': [
            {'type': 'stdio', 'name': 'editor', 'command': 'python', 'args': []},
        ]})
    refusal = caught.value
    assert refusal.reason == 'acp_extra_missing'
    assert refusal.field == 'editor.mcp_servers'
    assert "'[acp]'" in refusal.detail
    assert str(refusal) == 'acp_extra_missing'


def test_unrelated_import_failure_is_not_misreported_as_missing_acp(monkeypatch):
    _make_acp_import_fail(monkeypatch, 'other_optional_dependency')
    with pytest.raises(ModuleNotFoundError) as caught:
        validate_servers([{'type': 'stdio', 'name': 'editor', 'command': 'python', 'args': []}])
    assert caught.value.name == 'other_optional_dependency'
