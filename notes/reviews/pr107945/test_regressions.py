"""Focused #107945 witnesses. Copy to tests/tools/ in a full Hermes checkout.

No provider/model calls: resolver and child constructor are controlled doubles.
Original routing: KoNit-K. Earlier preflight/cleanup approach: apoapostolov (#77953),
identified by KoNit-K's comparison. These regression witnesses: kvnloo.
"""
import json
import threading
from types import SimpleNamespace

import pytest


@pytest.fixture
def review(monkeypatch):
    import tools.delegate_tool as dt
    import tools.delegate_tool_child_run as child_run
    import tools.delegation_live_log as live

    parent = SimpleNamespace(_delegate_depth=0, _active_children=[], _active_children_lock=threading.Lock())
    h = SimpleNamespace(dt=dt, parent=parent, cfg={}, made=[], failure=None)

    def resolve(cfg, parent_agent):
        if cfg.get('provider') == 'unavailable' or cfg.get('model') == 'retired-model':
            raise ValueError('synthetic unavailable route')
        return {'provider': cfg.get('provider'), 'model': cfg.get('model'),
                'base_url': 'https://worker.invalid/v1' if cfg.get('provider') else None,
                'api_key': 'synthetic-key' if cfg.get('provider') else None,
                'api_mode': 'chat_completions' if cfg.get('provider') else None}

    def build(**kwargs):
        if h.failure is not None and kwargs['task_index'] == 1:
            raise h.failure
        child = SimpleNamespace(kwargs=kwargs, close_calls=0, tool_progress_callback=None)
        def close():
            child.close_calls += 1
        child.close = close
        child_run._attach_child(parent, child)
        h.made.append(child)
        return child

    monkeypatch.setattr(dt, '_load_config', lambda: h.cfg)
    monkeypatch.setattr(dt, '_resolve_delegation_credentials', resolve)
    monkeypatch.setattr(dt, '_build_child_preserving_parent_tools', build)
    monkeypatch.setattr(dt, '_get_max_concurrent_children', lambda: 10)
    monkeypatch.setattr(dt, '_get_max_spawn_depth', lambda: 2)
    monkeypatch.setattr(dt, 'is_spawn_paused', lambda: False)
    monkeypatch.setattr(dt, '_announce_batch', lambda *args: None)
    monkeypatch.setattr(dt, '_capture_origin', lambda: ('', '', None, None, False))
    monkeypatch.setattr(dt, '_run_batch', lambda *args: json.dumps({'status': 'fixture accepted'}))
    monkeypatch.setattr(live, 'create_live_transcripts', lambda *args, **kwargs: (None, [], []))
    return h


def task(**overrides):
    return {'goal': 'Review the synthetic task', **overrides}


@pytest.mark.parametrize('config,pin', [
    ({'provider': 'unavailable'}, {'provider': 'available-worker'}),
    ({'provider': 'available-worker', 'model': 'retired-model'}, {'model': 'supported-model'}),
])
def test_unused_default_cannot_block_valid_task_pin(review, config, pin):
    h = review
    h.cfg.update(config)
    result = json.loads(h.dt.delegate_task(tasks=[task(**pin)], parent_agent=h.parent))
    assert 'error' not in result, result
    assert len(h.made) == 1


def test_invalid_later_pin_allocates_no_children(review):
    h = review
    result = json.loads(h.dt.delegate_task(
        tasks=[task(provider='available-worker'), task(provider='unavailable')], parent_agent=h.parent))
    assert 'error' in result
    assert h.made == []
    assert h.parent._active_children == []


@pytest.mark.parametrize('failure', [ValueError('rejected'), RuntimeError('constructor failed')])
def test_later_construction_failure_releases_returned_child(review, failure):
    h = review
    h.failure = failure
    if isinstance(failure, ValueError):
        result = json.loads(h.dt.delegate_task(tasks=[task(), task()], parent_agent=h.parent))
        assert result['error'] == str(failure)
    else:
        with pytest.raises(RuntimeError) as raised:
            h.dt.delegate_task(tasks=[task(), task()], parent_agent=h.parent)
        assert raised.value is failure
    assert len(h.made) == 1
    assert h.made[0].close_calls == 1
    assert h.parent._active_children == []


def test_success_does_not_close_children_before_runner_owns_them(review):
    h = review
    result = json.loads(h.dt.delegate_task(tasks=[task(), task()], parent_agent=h.parent))
    assert 'error' not in result
    assert len(h.made) == 2
    assert all(child.close_calls == 0 for child in h.made)
    assert h.parent._active_children == h.made
