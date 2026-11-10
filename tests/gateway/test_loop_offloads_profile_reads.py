"""The gateway event loop must not do profile file work on the loop.

Every stall dump in ``logs/gateway-shutdown-watchdog.log`` (six of them, 2026-11-07/08) caught the
loop thread inside a synchronous profile read: ``_profile_runtime_scope`` entering
``owner_scope`` from the 1 Hz hosted-room watcher (four dumps), ``profile_serve_signature`` hashing
``config.yaml``/``.env`` in the profile reconcile (one), and slack_bolt deriving its app name with
``inspect.stack()`` during connect (one). Three missed 30s liveness probes and the watchdog
hard-exits the process with code 75, killing in-flight turns.

These pin the two cheapest authors of that stall.
"""
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest


def _counting_scope(monkeypatch, module):
    entered = []

    @asynccontextmanager
    async def scope(authority):
        entered.append(authority)
        yield

    monkeypatch.setattr(module, 'async_owner_scope', scope)
    return entered


@pytest.mark.asyncio
async def test_a_prepared_hosted_service_is_not_re_scoped_on_every_tick(tmp_path, monkeypatch):
    """The 1 Hz watcher must not re-enter ``owner_scope`` for a service that already exists."""
    from gateway import session_hosted_service as mod

    entered = _counting_scope(monkeypatch, mod)
    service = SimpleNamespace(_transport_installed=True)
    authority = SimpleNamespace(
        db=SimpleNamespace(db_path=str(tmp_path / 'state.db')),
        profile_id=str(tmp_path), epoch=None, hosted_room_service=service)
    runner = SimpleNamespace(session_control_server=None)

    await mod._ensure_hosted_service(runner, authority)
    assert entered == [], 'steady state must not read the profile .env/config on the loop'


@pytest.mark.asyncio
async def test_an_unprepared_authority_still_builds_inside_its_scope(tmp_path, monkeypatch):
    """The fast path must not bypass the preparation work: an unprepared service still installs."""
    from gateway import session_hosted_service as mod

    entered = _counting_scope(monkeypatch, mod)
    installed = []
    monkeypatch.setattr('gateway.session_hosted_transport.install_hosted_transport',
                        lambda *args, **kwargs: installed.append((args, kwargs)))
    service = SimpleNamespace(_transport_installed=False, attest=lambda: True)
    authority = SimpleNamespace(
        db=SimpleNamespace(db_path=str(tmp_path / 'state.db')),
        profile_id=str(tmp_path), epoch=None, hosted_room_service=service)
    runner = SimpleNamespace(session_control_server=object())

    await mod._ensure_hosted_service(runner, authority)

    assert entered == [authority], 'an unprepared service must be prepared inside its scope'
    assert installed, 'the transport must still be installed'
    assert service._transport_installed is True


@pytest.mark.asyncio
async def test_watcher_signature_hashing_runs_off_the_event_loop(tmp_path, monkeypatch):
    """Served-profile signatures are hashed in a worker thread, never on the loop thread."""
    import threading
    from unittest.mock import patch

    from gateway import run_profile_reconcile as reconcile_mod
    from tests.gateway.test_multiplex_hot_serve import _mkprofile, _runner

    runner, home = _runner(tmp_path, monkeypatch)
    _mkprofile(home, 'alpha', 'DISCORD_BOT_TOKEN=alpha-token\n')
    with patch('hermes_cli.profiles.get_active_profile_name', return_value='default'):
        await runner._start_secondary_profile_adapters()

        loop_thread = threading.get_ident()
        seen = []
        real = reconcile_mod.profile_serve_signature

        def spy(profile_home):
            seen.append(threading.get_ident())
            return real(profile_home)

        monkeypatch.setattr(reconcile_mod, 'profile_serve_signature', spy)
        await runner.reconcile_served_profiles(reason='watcher')

    assert seen, 'the watcher must compare served-profile signatures'
    assert all(ident != loop_thread for ident in seen), \
        'signature hashing must not run on the event loop thread'


@pytest.mark.asyncio
async def test_cold_hosted_service_scope_file_work_runs_off_loop(tmp_path, monkeypatch):
    """A newly served multiplex profile must not read its terminal policy on the gateway loop."""
    import threading

    from gateway import session_hosted_service as mod
    from tools import terminal_scope

    home = tmp_path / 'profiles' / 'secondary'
    home.mkdir(parents=True)
    (home / '.env').write_text('HOSTED_ROOM_TEST_KEY=secondary\n', encoding='utf-8')
    (home / 'config.yaml').write_text(
        'terminal:\n  backend: local\n  cwd: /srv/work\n', encoding='utf-8')

    runner = SimpleNamespace(config=SimpleNamespace(multiplex_profiles=True),
                             session_control_server=object())
    service = SimpleNamespace(_transport_installed=False, attest=lambda *args: True)
    authority = SimpleNamespace(
        runner=runner, profile_id=str(home), epoch=None,
        db=SimpleNamespace(db_path=str(home / 'state.db')), hosted_room_service=service)

    installed = []
    monkeypatch.setattr('gateway.session_hosted_transport.install_hosted_transport',
                        lambda *args, **kwargs: installed.append((args, kwargs)))
    loop_thread = threading.get_ident()
    build_threads = []
    original_build = terminal_scope.build_profile_terminal_scope

    def record_build(*args, **kwargs):
        build_threads.append(threading.get_ident())
        return original_build(*args, **kwargs)

    monkeypatch.setattr(terminal_scope, 'build_profile_terminal_scope', record_build)
    await mod._ensure_hosted_service(runner, authority)

    assert build_threads, 'the cold profile must load its terminal policy'
    assert all(thread_id != loop_thread for thread_id in build_threads), (
        'cold profile reads must not block the gateway event loop')
    assert installed and service._transport_installed is True
