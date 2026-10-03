"""Runtime-backed retirement when a secondary adapter's configuration is rejected."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from gateway.config import Platform
from gateway.run import MultiplexConfigError
from gateway.run_runtime import initialize_gateway_runtime, unserve_profile_runtime
from gateway.runtime_ownership import process_ownership
from gateway.status import flush_runtime_status
from tests.gateway.test_session_authorities_multiplex import _reserve_homes, _runner


class FiniteAdapter:
    platform = Platform.DISCORD
    token = None

    def __init__(self):
        self.disconnected = False
        self.cancelled = False

    async def disconnect(self):
        self.disconnected = True

    async def cancel_background_tasks(self):
        self.cancelled = True


@pytest.mark.asyncio
@pytest.mark.parametrize('already_served', [False, True], ids=['hot-added', 'changed'])
async def test_config_error_retires_profile_runtime_and_explicit_rescan_recovers(
    tmp_path, monkeypatch, already_served,
):
    root, homes = _reserve_homes(tmp_path, monkeypatch, names=('healthy',))
    monkeypatch.setattr('hermes_cli.profiles.get_active_profile_name', lambda: 'default')
    process_ownership.reserve([home for _, home in homes])
    runner = _runner(root, homes)
    runner._running = True
    runner._primary_profile_name = 'default'
    attempts, added_hooks, failed_authorities = [], [], []
    fail = False
    built_adapters = []
    healthy_adapter = FiniteAdapter()
    held_task = None

    async def start(name, home, claimed):
        attempts.append(name)
        authority = runner.session_authorities.for_home(home)
        assert authority is not None  # The real hot-serve runtime exists before adapter startup.
        if fail:
            failed_authorities.append(authority)
            raise MultiplexConfigError('fixture adapter configuration rejected')
        built_adapters.append(FiniteAdapter())
        runner._profile_adapters.setdefault(name, {})[Platform.DISCORD] = built_adapters[-1]
        return 1

    async def after_added(profiles):
        # External MCP discovery is outside this finite lifecycle scenario.
        added_hooks.extend(name for name, _home in profiles)

    monkeypatch.setattr(runner, '_start_one_profile_adapters', start)
    monkeypatch.setattr(runner, '_after_profiles_added', after_added)
    try:
        await initialize_gateway_runtime(runner)
        runner._record_served_profiles('default', homes)
        healthy = runner.session_authorities.for_home(homes[1][1])
        runner._profile_adapters = {'healthy': {Platform.DISCORD: healthy_adapter}}
        secondary = root / 'profiles' / 'secondary'
        secondary.mkdir()
        (secondary / 'config.yaml').write_text('model: {default: fixture}\n')
        if already_served:
            assert (await runner.reconcile_served_profiles())['added'] == ['secondary']
            prior = runner.session_authorities.for_home(secondary)
            held_task = asyncio.create_task(asyncio.Event().wait())
            await asyncio.sleep(0)
            prior.sessions['fixture-lifecycle'] = SimpleNamespace(task=held_task)
            (secondary / 'config.yaml').write_text('model: {default: fixture-edited}\n')
        attempts.clear()
        added_hooks.clear()
        fail = True
        result = await runner.reconcile_served_profiles()
        assert result['parked'] == ['secondary']
        assert result['added'] == result['rescanned'] == []
        assert result['served_profiles'] == ['default', 'healthy']
        assert runner.session_authorities.for_home(secondary) is None
        assert str(secondary.resolve()) not in runner.session_ticket_store.profile_ids
        assert {row['home'] for row in runner.session_runtime_descriptor['served_profiles']} == {
            str(home.resolve()) for _, home in homes}
        assert 'secondary' in runner.session_runtime_descriptor['parked_profiles']
        assert not process_ownership.owns(secondary)
        assert [name for name, _home in runner.config._runtime_profile_homes] == ['default', 'healthy']
        assert 'secondary' not in runner._profile_adapters
        assert 'secondary' not in runner._served_profile_signatures
        assert added_hooks == []
        if already_served:
            assert built_adapters[0].disconnected and built_adapters[0].cancelled
            assert held_task.cancelled()
        assert runner.session_authorities.for_home(homes[1][1]) is healthy
        assert process_ownership.owns(homes[1][1])
        assert not healthy_adapter.disconnected
        flush_runtime_status()
        import json
        recorded = json.loads((root / 'gateway_state.json').read_text())
        assert recorded['served_profiles'] == ['default', 'healthy']
        assert 'secondary' in recorded['parked_profiles']

        # Watcher does not continuously retry an unchanged rejected profile.
        await runner.reconcile_served_profiles(reason='watcher')
        assert attempts == ['secondary']
        # Explicit rescan uses the existing recovery contract and a fresh authority.
        fail = False
        recovered = await runner.reconcile_served_profiles(reason='control-socket')
        assert recovered['added'] == ['secondary']
        replacement = runner.session_authorities.for_home(secondary)
        assert replacement is not None and replacement is not failed_authorities[0]
        assert 'secondary' not in runner.session_runtime_descriptor['parked_profiles']
        assert process_ownership.owns(secondary)
        assert str(secondary.resolve()) in runner.session_ticket_store.profile_ids
        assert added_hooks == ['secondary']
        assert not built_adapters[-1].disconnected
        if already_served:
            assert built_adapters[-1] is not built_adapters[0]
    finally:
        if held_task is not None and not held_task.done():
            held_task.cancel()
            await asyncio.gather(held_task, return_exceptions=True)
        if getattr(runner, 'session_authorities', None) is not None:
            for authority in list(runner.session_authorities):
                if Path(authority.profile_id) != root:
                    await unserve_profile_runtime(runner, authority.profile_id)
            from gateway.session_cron import unbind_owner
            unbind_owner(runner.session_authorities.launch)
        runner.session_store.close_all_db_handles()
        runner.close_all_session_db_handles()
        for home in list(process_ownership.homes):
            process_ownership.release(home)
