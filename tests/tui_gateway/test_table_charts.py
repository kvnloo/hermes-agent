"""Opt-in automatic table planning admission and budgets (#590), without live models."""
import queue
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

TABLE = '| Category | Revenue |\n| --- | --- |\n| Alpha | 10 |\n| Beta | 25 |'


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from tui_gateway import server
    from hermes_cli.config import save_config
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    save_config({'display': {'table_charts': 'off'}})
    transport = SimpleNamespace(write=lambda frame: True)
    owner = {'session_key': 'key', 'transport': transport, 'profile_home': str(tmp_path),
             'history_lock': threading.RLock(), 'history': [{'role': 'assistant', 'content': TABLE}]}
    monkeypatch.setattr(server, '_sessions', {'s': owner})
    plan = Mock(return_value='line')
    monkeypatch.setattr(server, '_plan_table_chart', plan)
    def call(method='table_chart.plan', via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({'id': 1, 'method': method, 'params': {'session_id': 's', **params}})
        finally:
            server.reset_transport(token)
    def mode(value):
        save_config({'display': {'table_charts': value}})
    return server, owner, call, mode, plan, transport


def test_real_profile_loader_defaults_off_and_never_calls_model_when_off_or_local(runtime):
    _, owner, call, mode, plan, _ = runtime
    assert call('table_chart.policy')['result'] == {'mode': 'off'}
    assert call(source=TABLE)['result'] == {'kind': 'bar'}
    mode('always')
    assert call('table_chart.policy')['result'] == {'mode': 'always'}
    assert call(source=TABLE)['result'] == {'kind': 'bar'}
    plan.assert_not_called()
    assert owner['history'] == [{'role': 'assistant', 'content': TABLE}]


def test_smart_deduplicates_and_caps_each_owned_session(runtime):
    _, _, call, mode, plan, _ = runtime
    mode('smart')
    for i in range(12):
        source = TABLE.replace('Revenue', f'Revenue {i}')
        assert call(source=source)['result']['kind'] in ('line', 'bar')
        call(source=source)
    assert plan.call_count == 8


def test_planner_failure_falls_back_and_does_not_retry(runtime):
    _, _, call, mode, plan, _ = runtime
    mode('smart')
    plan.side_effect = RuntimeError('provider unavailable')
    assert call(source=TABLE)['result'] == {'kind': 'bar'}
    assert call(source=TABLE)['result'] == {'kind': 'bar'}
    plan.assert_called_once()


@pytest.mark.parametrize('source', ['', 'x' * 8193, 12, TABLE.replace('25', 'unknown')])
def test_invalid_or_nonnumeric_sources_never_call_model(runtime, source):
    _, _, call, mode, plan, _ = runtime
    mode('smart')
    result = call(source=source)
    assert 'error' in result or result['result'] == {'kind': 'bar'}
    plan.assert_not_called()


def test_transport_and_session_replacement_cancel_stale_result(runtime):
    server, owner, call, mode, plan, _ = runtime
    mode('smart')
    foreign = SimpleNamespace(write=lambda frame: True)
    assert 'error' in call(source=TABLE, via=foreign)
    assert 'error' in call('table_chart.policy', via=foreign)
    def replaced(source, cancelled):
        assert not cancelled()
        server._sessions['s'] = {**owner}
        assert cancelled()
        return 'line'
    plan.side_effect = replaced
    assert call(source=TABLE)['result'] == {'kind': 'bar'}


def test_worker_dispatch_does_not_block_reader_and_uses_owned_profile(runtime):
    server, owner, _, mode, plan, _ = runtime
    mode('smart')
    answers = queue.Queue()
    transport = SimpleNamespace(write=lambda frame: answers.put(frame))
    owner['transport'] = transport
    assert server.dispatch({'id': 'p', 'method': 'table_chart.plan',
                            'params': {'session_id': 's', 'source': TABLE}}, transport=transport) is None
    assert answers.get(timeout=10)['result'] == {'kind': 'line'}
    plan.assert_called_once()


def test_native_setting_is_explicit_validated_and_emits_live_policy(runtime, monkeypatch):
    server, _, call, _, plan, _ = runtime
    emitted = Mock()
    monkeypatch.setattr(server, '_emit', emitted)
    assert 'error' in call('settings.set', key='display.table_charts', value='invented', confirmed=True)
    changed = call('settings.set', key='display.table_charts', value='smart', confirmed=True)
    assert changed['result']['value'] == 'smart'
    assert call('table_chart.policy')['result']['mode'] == 'smart'
    assert call('settings.get')['result']['fields']['display.table_charts']['value'] == 'smart'
    emitted.assert_any_call('table_chart.policy', 's', {'mode': 'smart'})
    plan.assert_not_called()


def test_real_planner_limits_provider_request_and_rejects_arbitrary_output(monkeypatch):
    from tui_gateway import server
    from agent import auxiliary_client
    completion = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='<svg>unsafe</svg>'))]))
    monkeypatch.setattr(auxiliary_client, 'get_text_auxiliary_client', lambda task: (object(), 'fixture'))
    monkeypatch.setattr(auxiliary_client, '_relay_sync_completion', completion)
    assert server._plan_table_chart(TABLE, lambda: False) == 'bar'
    kwargs = completion.call_args.args[1]
    assert kwargs['timeout'] == 5
    assert 64 in (kwargs.get('max_tokens'), kwargs.get('max_completion_tokens'))
    assert 'tools' not in kwargs


def test_auxiliary_baseexception_cancellation_settles_to_local_fallback(runtime):
    from agent.auxiliary_client import AuxiliaryExplicitCancellation
    _, owner, call, mode, plan, _ = runtime
    mode('smart')
    plan.side_effect = AuxiliaryExplicitCancellation()
    assert call(source=TABLE)['result'] == {'kind': 'bar'}
    assert not owner['_table_charts']['active']


def test_single_flight_blocks_parallel_model_work(runtime):
    _, owner, call, mode, plan, _ = runtime
    mode('smart')
    def nested(source, cancelled):
        assert owner['_table_charts']['active']
        assert call(source=TABLE.replace('Revenue', 'Second'))['result'] == {'kind': 'bar'}
        return 'line'
    plan.side_effect = nested
    assert call(source=TABLE)['result'] == {'kind': 'line'}
    plan.assert_called_once()
