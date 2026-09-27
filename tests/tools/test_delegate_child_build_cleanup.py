"""``_build_children`` closes already-built children when a later child's build fails.

A fully built child owns a dedicated SessionDB handle (released only by ``close()``);
abandoning it on a mid-batch build failure pins the handle until process exit.
Contract tests with a stubbed child builder, not snapshots.
"""

import pytest

from tools import delegate_tool


class _StubChild:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _creds():
    return {"provider": "p", "base_url": "u", "api_key": "k", "api_mode": "m", "model": "model"}


def _run_build(monkeypatch, tasks, builder):
    monkeypatch.setattr(delegate_tool, "_build_child_preserving_parent_tools", builder)
    return delegate_tool._build_children(
        tasks, [None] * len(tasks), _creds(), top_role="leaf", max_iterations=1,
        parent_agent=None, routing_cfg={}, live_deleg_id=None, live_writers=[])


def _builder(fail_on=None, exc=RuntimeError("boom")):
    built = []

    def build(**kwargs):
        if kwargs.get("task_index") == fail_on:
            raise exc
        child = _StubChild()
        built.append(child)
        return child

    return build, built


def test_later_build_failure_closes_earlier_children(monkeypatch):
    build, built = _builder(fail_on=1)
    with pytest.raises(RuntimeError):
        _run_build(monkeypatch, [{"goal": "a"}, {"goal": "b"}], build)
    assert len(built) == 1 and built[0].closed


def test_preflight_valueerror_closes_earlier_children(monkeypatch):
    build, built = _builder(fail_on=1, exc=ValueError("bad pin"))
    children, err = _run_build(monkeypatch, [{"goal": "a"}, {"goal": "b"}], build)
    assert children == [] and err == "bad pin"
    assert len(built) == 1 and built[0].closed


def test_successful_build_closes_nothing(monkeypatch):
    build, built = _builder()
    children, err = _run_build(monkeypatch, [{"goal": "a"}, {"goal": "b"}], build)
    assert err is None and len(children) == 2
    assert len(built) == 2 and not any(c.closed for c in built)
