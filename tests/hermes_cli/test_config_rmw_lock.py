"""Concurrent dashboard config writers must not drop each other's mutations.

Only ``PUT /api/config`` (and the ``config_write_scope`` routers) held ``_CONFIG_MUTATION_LOCK``.
The custom-endpoint handlers, the profile-create model write, ``POST /api/model/set`` and
``PUT /api/model/moa`` ran their load→mutate→save cycles on worker threads without it, so a
writer racing the desktop's debounced whole-record autosave interleaved as::

    T1 load (providers={})     T2 load (providers={})
    T1 mutate providers.box    T2 mutate display.x
    T1 save (providers.box)    T2 save (providers={} + display.x)   <- T1's write erased

Both tests force exactly that interleaving and assert both writes land.
"""

from __future__ import annotations

import threading

import pytest
import hermes_yaml as yaml


@pytest.fixture
def client(monkeypatch, _isolate_hermes_home):
    from starlette.testclient import TestClient

    from hermes_cli.config import load_config, save_config
    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app

    monkeypatch.setattr("hermes_cli.model_cost_guard.expensive_model_warning", lambda *_a, **_k: None)
    cfg = load_config()
    cfg["model"] = {"provider": "openrouter", "default": "openai/gpt-5.5"}
    save_config(cfg)

    client = TestClient(app)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    return client


def _race_second_writer_into_first_writers_save(monkeypatch, first, second, timeout: float = 1.5):
    """Deterministic lost-write interleaving: ``first`` runs until it reaches ``save_config``,
    then ``second`` is started and ``first`` waits (up to ``timeout``) for ``second`` to
    ``load_config`` before saving. Unlocked, ``second`` loads the stale document and its save
    erases ``first``'s mutation. With the RMW lock ``second`` blocks before its load, ``first``'s
    wait times out, and the two writes serialize. Returns ``(first_response, second_response)``."""
    import hermes_cli.config as cfg_mod

    real_save, real_load = cfg_mod.save_config, cfg_mod.load_config
    first_at_save, second_loaded = threading.Event(), threading.Event()
    gate = threading.Lock()

    def gated_save(config, *args, **kwargs):
        # The first save_config call in the test is the first writer's (the second has not
        # started yet). Hold it until the second writer has loaded — or the lock kept it out.
        if not first_at_save.is_set():
            first_at_save.set()
            second_loaded.wait(timeout)
            with gate:
                return real_save(config, *args, **kwargs)
        return real_save(config, *args, **kwargs)

    def spied_load(*args, **kwargs):
        cfg = real_load(*args, **kwargs)
        # Any load while the first writer sits blocked in save_config is the second writer's.
        if first_at_save.is_set() and not gate.locked():
            second_loaded.set()
        return cfg

    monkeypatch.setattr(cfg_mod, "save_config", gated_save)
    monkeypatch.setattr(cfg_mod, "load_config", spied_load)

    results: list = [None, None]
    threads = [threading.Thread(target=lambda: results.__setitem__(0, first())),
               threading.Thread(target=lambda: results.__setitem__(1, second()))]
    threads[0].start()
    assert first_at_save.wait(30), "first writer never reached save_config"
    threads[1].start()
    for t in threads:
        t.join(timeout=60)
    return results


def _on_disk() -> dict:
    from hermes_constants import get_hermes_home
    return yaml.safe_load((get_hermes_home() / "config.yaml").read_text(encoding="utf-8"))


def test_custom_endpoint_upsert_racing_config_autosave_keeps_both_writes(client, monkeypatch):
    """Saving a custom endpoint (sync-def handler on a worker thread) while the settings-page
    autosave (PUT /api/config) is in flight: the new ``providers`` entry AND the autosaved field
    both survive."""
    autosave = lambda: client.put(  # noqa: E731
        "/api/config", json={"config": {"display": {"personality": "canary"}}})
    upsert = lambda: client.post(  # noqa: E731
        "/api/providers/custom-endpoints",
        json={"id": "racebox", "name": "racebox", "base_url": "http://racebox:8000/v1", "model": "race-model",
              "discover_models": False})

    r1, r2 = _race_second_writer_into_first_writers_save(monkeypatch, autosave, upsert)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text

    on_disk = _on_disk()
    assert "racebox" in on_disk["providers"]
    assert on_disk["display"]["personality"] == "canary"


def test_custom_endpoint_activate_racing_moa_save_keeps_both_writes(client, monkeypatch):
    """Two worker-thread writers (custom-endpoint activate vs MoA save) serialize through the
    same lock — the ``model`` switch and the ``moa`` section are both on disk afterwards."""
    from hermes_cli.config import load_config, save_config

    cfg = load_config()
    cfg["providers"] = {"racebox": {"base_url": "http://racebox:8000/v1", "model": "race-model", "api_key": "k"}}
    save_config(cfg)

    activate = lambda: client.post("/api/providers/custom-endpoints/racebox/activate")  # noqa: E731
    moa = lambda: client.put(  # noqa: E731
        "/api/model/moa",
        json={"reference_models": [{"provider": "openrouter", "model": "openai/gpt-5.5"}],
              "aggregator": {"provider": "openrouter", "model": "openai/gpt-5.5"}})

    r1, r2 = _race_second_writer_into_first_writers_save(monkeypatch, activate, moa)
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text

    on_disk = _on_disk()
    assert on_disk["model"]["provider"] == "racebox"
    assert on_disk["moa"]["aggregator"]["model"] == "openai/gpt-5.5"


def _acquire_config_mutation_lock_in_process(config_path, attempting, acquired):
    from hermes_cli.config import config_mutation_lock

    attempting.set()
    with config_mutation_lock(config_path):
        acquired.set()


def test_profile_config_mutation_lock_excludes_another_process(tmp_path):
    import multiprocessing

    from hermes_cli.config import config_mutation_lock

    context = multiprocessing.get_context("spawn")
    attempting, acquired = context.Event(), context.Event()
    config_path = tmp_path / "config.yaml"
    process = context.Process(
        target=_acquire_config_mutation_lock_in_process,
        args=(str(config_path), attempting, acquired),
    )
    process.start()
    try:
        with config_mutation_lock(config_path):
            assert attempting.wait(10), "child process did not reach the profile lock"
            assert not acquired.wait(0.3), "a second process entered the same profile transaction"
        assert acquired.wait(10), "child process did not enter after the transaction committed"
    finally:
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
    assert process.exitcode == 0


def test_dashboard_autosave_serializes_with_raw_yaml_key_update(client, monkeypatch):
    """A whole-config dashboard PUT cannot erase an atomic legacy-key update to its profile."""
    import threading

    import hermes_cli.config as cfg_mod
    import utils
    from hermes_constants import get_hermes_home
    from utils import atomic_roundtrip_yaml_update

    config_path = get_hermes_home() / "config.yaml"
    dashboard_at_save, raw_loaded = threading.Event(), threading.Event()
    real_save, real_roundtrip_load = cfg_mod.save_config, utils._roundtrip_load
    responses, failures = [], []

    def gated_save(config, *args, **kwargs):
        dashboard_at_save.set()
        raw_loaded.wait(1.0)
        return real_save(config, *args, **kwargs)

    def observed_roundtrip_load(path):
        raw_loaded.set()
        return real_roundtrip_load(path)

    monkeypatch.setattr(cfg_mod, "save_config", gated_save)
    monkeypatch.setattr(utils, "_roundtrip_load", observed_roundtrip_load)

    def update_dashboard():
        try:
            responses.append(client.put(
                "/api/config", json={"config": {"display": {"personality": "canary"}}}))
        except Exception as exc:
            failures.append(exc)

    def update_legacy_key():
        try:
            atomic_roundtrip_yaml_update(config_path, "display.in_app_tips", False)
        except Exception as exc:
            failures.append(exc)

    dashboard = threading.Thread(target=update_dashboard, name="dashboard-config-put")
    legacy = threading.Thread(target=update_legacy_key, name="raw-yaml-update")
    dashboard.start()
    assert dashboard_at_save.wait(10), "dashboard PUT never reached its config commit"
    legacy.start()
    dashboard.join(timeout=10)
    legacy.join(timeout=10)

    assert not dashboard.is_alive() and not legacy.is_alive()
    assert not failures
    assert len(responses) == 1 and responses[0].status_code == 200, responses
    on_disk = _on_disk()
    assert on_disk["display"]["personality"] == "canary"
    assert on_disk["display"]["in_app_tips"] is False


def _write_platform_config_in_process(
    profile_home, at_commit, model_lock_waiting, allow_commit, finished, failures
):
    import os

    os.environ["HERMES_HOME"] = str(profile_home)
    import hermes_cli.config as config_module

    real_replace = config_module.atomic_config_replace

    def pause_before_commit(*args, **kwargs):
        at_commit.set()
        if not model_lock_waiting.wait(15):
            raise TimeoutError("native model writer did not reach the profile lock")
        if not allow_commit.wait(15):
            raise TimeoutError("platform config commit was not released")
        return real_replace(*args, **kwargs)

    config_module.atomic_config_replace = pause_before_commit
    try:
        config_module.write_platform_config_field("telegram", "enabled", True)
    except BaseException as exc:
        failures.put(f"platform writer: {exc!r}")
    finally:
        finished.set()


def _persist_model_selection_in_process(
    profile_home, lock_waiting, lock_acquired, finished, failures
):
    import os
    from contextlib import contextmanager
    from pathlib import Path

    os.environ["HERMES_HOME"] = str(profile_home)
    import hermes_cli.auth as auth_module
    from hermes_cli.model_switch import ModelSwitchResult, persist_model_selection

    real_file_lock = auth_module._file_lock
    expected_lock = (Path(profile_home) / "config.yaml.lock").resolve()

    @contextmanager
    def observe_profile_lock(*args, **kwargs):
        is_profile_config_lock = Path(args[0]).resolve() == expected_lock
        if is_profile_config_lock:
            lock_waiting.set()
        with real_file_lock(*args, **kwargs):
            if is_profile_config_lock:
                lock_acquired.set()
            yield

    auth_module._file_lock = observe_profile_lock
    try:
        persist_model_selection(ModelSwitchResult(
            success=True, new_model="model-after-platform", target_provider="custom:racebox",
            base_url="http://racebox:8000/v1",
        ))
    except BaseException as exc:
        failures.put(f"native model writer: {exc!r}")
    finally:
        finished.set()


def test_platform_writer_serializes_with_native_model_writer_across_processes(
    tmp_path, monkeypatch
):
    """A model writer waits for the public platform RMW commit, preserving both raw records."""
    import multiprocessing
    import queue

    context = multiprocessing.get_context("spawn")
    profile_home = tmp_path / "profiles" / "native"
    profile_home.mkdir(parents=True)
    config_path = profile_home / "config.yaml"
    config_path.write_text(
        'model:\n'
        '  provider: custom:racebox\n'
        '  default: model-before-platform\n'
        '  base_url: http://racebox:8000/v1\n'
        '  api_key: "${RACEBOX_API_KEY}" # preserve custom endpoint credential template\n'
        'platforms:\n'
        '  existing:\n'
        '    access_token: "${TEST_PLATFORM_TOKEN}"\n'
        '    enabled: false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("RACEBOX_API_KEY", "test-only-custom-credential")
    monkeypatch.setenv("TEST_PLATFORM_TOKEN", "test-only-platform-credential")

    at_commit = context.Event()
    model_lock_waiting, model_lock_acquired = context.Event(), context.Event()
    allow_commit = context.Event()
    platform_finished, model_finished = context.Event(), context.Event()
    failures = context.Queue()
    platform = context.Process(
        target=_write_platform_config_in_process,
        args=(str(profile_home), at_commit, model_lock_waiting, allow_commit,
              platform_finished, failures),
    )
    model = context.Process(
        target=_persist_model_selection_in_process,
        args=(str(profile_home), model_lock_waiting, model_lock_acquired,
              model_finished, failures),
    )

    platform.start()
    try:
        assert at_commit.wait(15), "platform helper never reached its YAML commit"
        model.start()
        assert model_lock_waiting.wait(15), "model writer never attempted the profile file lock"
        assert not model_lock_acquired.wait(0.3), (
            "native model writer acquired the profile lock before the platform commit"
        )
        assert not model_finished.is_set(), "native model writer completed before platform commit"
        allow_commit.set()
        assert platform_finished.wait(15), "platform writer did not finish after commit release"
        assert model_finished.wait(15), "native model writer did not finish after platform commit"
    finally:
        allow_commit.set()
        for process in (platform, model):
            if process.pid is None:
                continue
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)

    errors = []
    for _ in range(2):
        try:
            errors.append(failures.get(timeout=1))
        except queue.Empty:
            break
    assert not errors
    assert platform.exitcode == 0
    assert model.exitcode == 0

    raw_text = config_path.read_text(encoding="utf-8")
    on_disk = yaml.safe_load(raw_text)
    assert on_disk["platforms"]["telegram"]["enabled"] is True
    assert on_disk["model"]["default"] == "model-after-platform"
    assert on_disk["model"]["provider"] == "custom:racebox"
    assert on_disk["model"]["base_url"] == "http://racebox:8000/v1"
    assert on_disk["model"]["api_key"] == "${RACEBOX_API_KEY}"
    assert "# preserve custom endpoint credential template" in raw_text
    assert on_disk["platforms"]["existing"]["access_token"] == "${TEST_PLATFORM_TOKEN}"


def _write_platform_config_before_public_mutation_in_process(
    profile_home, at_commit, mutation_lock_attempting, allow_commit, finished, failures
):
    import os

    os.environ["HERMES_HOME"] = str(profile_home)
    import hermes_cli.config as config_module

    real_replace = config_module.atomic_config_replace

    def pause_before_commit(*args, **kwargs):
        at_commit.set()
        if not mutation_lock_attempting.wait(15):
            raise TimeoutError("public config mutation did not attempt the profile lock")
        if not allow_commit.wait(15):
            raise TimeoutError("platform config commit was not released")
        return real_replace(*args, **kwargs)

    config_module.atomic_config_replace = pause_before_commit
    try:
        config_module.write_platform_config_field("telegram", "enabled", True)
    except BaseException as exc:
        failures.put(f"platform writer: {exc!r}")
    finally:
        finished.set()


def _run_public_config_mutation_in_process(
    profile_home, operation, lock_attempting, lock_acquired, finished, failures
):
    import os
    from contextlib import contextmanager

    os.environ["HERMES_HOME"] = str(profile_home)
    import hermes_cli.config as config_module

    real_mutation_lock = config_module.config_mutation_lock

    @contextmanager
    def observe_mutation_lock(path=None):
        lock_attempting.set()
        with real_mutation_lock(path):
            lock_acquired.set()
            yield

    config_module.config_mutation_lock = observe_mutation_lock
    try:
        if operation == "set":
            config_module.set_config_value("display.personality", "canary")
        else:
            config_module.unset_config_value("display.in_app_tips")
    except BaseException as exc:
        failures.put(f"public {operation}: {exc!r}")
    finally:
        finished.set()


@pytest.mark.parametrize("operation", ("set", "unset"))
def test_public_config_set_and_unset_serialize_with_platform_writer_across_processes(
    operation, tmp_path, monkeypatch
):
    """Public whole-config mutations wait for a platform write and retain raw templates."""
    import multiprocessing
    import queue

    context = multiprocessing.get_context("spawn")
    profile_home = tmp_path / "profiles" / operation
    profile_home.mkdir(parents=True)
    config_path = profile_home / "config.yaml"
    config_path.write_text(
        '# preserve profile comment\n'
        'model:\n'
        '  provider: openrouter\n'
        '  default: model-before-platform\n'
        '  api_key: "${OPENROUTER_API_KEY}" # preserve model credential template\n'
        '  key_env: OPENROUTER_API_KEY\n'
        'platforms:\n'
        '  telegram:\n'
        '    enabled: false\n'
        '    access_token: "${TEST_PLATFORM_TOKEN}" # preserve platform credential template\n'
        '  existing:\n'
        '    access_token: "${TEST_PLATFORM_TOKEN}"\n'
        '    enabled: false\n'
        'display:\n'
        '  personality: friendly\n'
        '  in_app_tips: false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-model-credential")
    monkeypatch.setenv("TEST_PLATFORM_TOKEN", "test-only-platform-credential")

    at_commit = context.Event()
    lock_attempting, lock_acquired = context.Event(), context.Event()
    allow_commit = context.Event()
    platform_finished, mutation_finished = context.Event(), context.Event()
    failures = context.Queue()
    platform = context.Process(
        target=_write_platform_config_before_public_mutation_in_process,
        args=(str(profile_home), at_commit, lock_attempting, allow_commit, platform_finished, failures),
    )
    mutation = context.Process(
        target=_run_public_config_mutation_in_process,
        args=(
            str(profile_home), operation, lock_attempting, lock_acquired, mutation_finished, failures,
        ),
    )

    platform.start()
    try:
        assert at_commit.wait(15), "platform writer never reached its config commit"
        mutation.start()
        assert lock_attempting.wait(15), "public config mutation never attempted the profile lock"
        assert not lock_acquired.wait(0.3), (
            "public config mutation acquired the profile lock before the platform commit"
        )
        assert not mutation_finished.is_set(), "public config mutation completed before the platform commit"
        allow_commit.set()
        assert platform_finished.wait(15), "platform writer did not finish after commit release"
        assert lock_acquired.wait(15), "public config mutation did not acquire the profile lock"
        assert mutation_finished.wait(15), "public config mutation did not finish after platform commit"
    finally:
        allow_commit.set()
        for process in (platform, mutation):
            if process.pid is None:
                continue
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()
                process.join(timeout=10)

    errors = []
    for _ in range(2):
        try:
            errors.append(failures.get(timeout=1))
        except queue.Empty:
            break
    assert not errors
    assert platform.exitcode == 0
    assert mutation.exitcode == 0

    raw_text = config_path.read_text(encoding="utf-8")
    on_disk = yaml.safe_load(raw_text)
    assert on_disk["platforms"]["telegram"]["enabled"] is True
    assert on_disk["model"]["default"] == "model-before-platform"
    assert on_disk["model"]["api_key"] == "${OPENROUTER_API_KEY}"
    assert on_disk["platforms"]["telegram"]["access_token"] == "${TEST_PLATFORM_TOKEN}"
    assert on_disk["platforms"]["existing"]["access_token"] == "${TEST_PLATFORM_TOKEN}"
    assert "# preserve profile comment" in raw_text
    assert "# preserve model credential template" in raw_text
    assert "# preserve platform credential template" in raw_text
    if operation == "set":
        assert on_disk["display"]["personality"] == "canary"
        assert on_disk["display"]["in_app_tips"] is False
    else:
        assert on_disk["display"]["personality"] == "friendly"
        assert "in_app_tips" not in on_disk["display"]
