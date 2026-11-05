"""A default currency probe is answered from its read set until any input changes."""
from __future__ import annotations

import pytest

from tests.pm._fixtures import (
    client as client,  # noqa: PLC0414 -- the self-alias is load-bearing: it suppresses F811 for the pytest fixture parameter shadowing this import
    isolated_python as isolated_python,  # noqa: PLC0414 -- the self-alias is load-bearing: it suppresses F811 for the pytest fixture parameter shadowing this import
)
from tests.pm.test_worker import _current_environment

pytestmark = pytest.mark.real_machine_home


@pytest.fixture
def probes(client, tmp_path, monkeypatch, isolated_python):
    """Real worker probes against a current fixture install; counts worker round-trips."""
    from pm.environments import selected_venv

    monkeypatch.setattr(client, "is_runtime", lambda: False)
    monkeypatch.setattr("pm.runtime.runtime_python", lambda **kwargs: isolated_python)
    repo = _current_environment(tmp_path, monkeypatch, [])
    workers = []
    request = client._request

    def counted(operation, *args, **kwargs):
        workers.append(operation)
        return request(operation, *args, **kwargs)

    monkeypatch.setattr(client, "_request", counted)
    return repo, selected_venv(repo), workers


def test_repeat_probe_skips_the_worker_while_inputs_are_unchanged(client, probes):
    repo, _environment, workers = probes
    assert client.venv_is_current()
    assert client.venv_is_current()
    assert client.venv_is_current(project_root=repo)
    assert workers == ["venv_is_current"], "an unchanged install paid a PM worker round-trip again"


def test_a_stale_lock_is_still_detected(client, probes):
    repo, _environment, workers = probes
    assert client.venv_is_current()
    (repo / "uv.lock").write_text("version = 2\n")
    assert not client.venv_is_current()
    assert not client.venv_is_current(), "a stale answer must never be remembered"
    assert workers == ["venv_is_current"] * 3


def test_a_vanished_environment_is_still_detected(client, probes):
    _repo, environment, workers = probes
    assert client.venv_is_current()
    (environment / "pyvenv.cfg").unlink()
    assert not client.venv_is_current()
    assert len(workers) == 2


def test_a_new_profile_selection_reaches_the_full_probe(client, probes, tmp_path):
    _repo, _environment, workers = probes
    assert client.venv_is_current()
    (tmp_path / "home").mkdir(exist_ok=True)
    (tmp_path / "home" / "config.yaml").write_text("plugins:\n  enabled: [absent]\n")
    client.venv_is_current()
    assert len(workers) == 2, "a plugin selection the probe had read as missing did not invalidate it"


def test_explicit_inputs_and_a_changed_environment_are_never_answered_from_the_record(
        client, probes, monkeypatch):
    from pm.plugin_inputs import Members

    _repo, _environment, workers = probes
    assert client.venv_is_current()
    assert client.venv_is_current(plugins=Members([]))
    assert not client.venv_is_current(extras=["new-extra"])
    monkeypatch.setenv("HERMES_DISABLE_LAZY_INSTALLS", "1")
    assert client.venv_is_current()
    assert len(workers) == 4
