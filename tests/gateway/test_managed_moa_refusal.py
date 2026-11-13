"""Managed LOCAL prompt.submit must refuse /moa before it reaches a single-model worker.

Regression for #147510: slash.exec already refuses managed /moa, but a raw /moa
submission (including a persisted queued turn) bypasses that command handler.
"""
from types import SimpleNamespace

import pytest

from agent.i18n import t
from gateway import session_managed_worker


@pytest.mark.asyncio
@pytest.mark.parametrize('finite', [False, True])
async def test_raw_moa_in_managed_session_refuses_without_spawning_worker(tmp_path, monkeypatch, finite):
    started = []

    async def run_worker(*_args):
        started.append(True)
        return 'answered on the wrong model'

    monkeypatch.setattr(session_managed_worker, 'execute_managed', run_worker)
    authority = SimpleNamespace(pending_results={})
    policy = SimpleNamespace(cwd=str(tmp_path))
    row = {'admission_id': 'managed-moa', 'payload': {
        'text': '/moa compare both options', 'finite': finite,
    }}

    answer = await session_managed_worker.admit_managed(authority, None, row, policy)

    notice = t('gateway.moa.managed_session')
    assert answer == notice
    assert not started
    result = authority.pending_results[row['admission_id']]
    assert result['usage'] == {}
    if finite:
        assert result['result']['error'] == notice
        assert result['result']['failed'] is True
        assert result['result']['final_response'] == ''
    else:
        assert result['result']['final_response'] == notice
