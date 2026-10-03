"""A rejected hot-profile drains its recovery-created receipt task before unreserving."""
import asyncio
from pathlib import Path

import pytest

from gateway.run import MultiplexConfigError
from gateway import run_runtime
from gateway.runtime_ownership import process_ownership
from hermes_state import SessionDB
from hermes_state_runtime import admit_session_input, begin_runtime_epoch
from tools.bot_live_delivery import _locked, _read, _write
from tests.gateway.test_session_authorities_multiplex import _reserve_homes, _runner


@pytest.mark.asyncio
async def test_profile_rejection_joins_recovered_receipt_before_release(tmp_path, monkeypatch):
    root, homes = _reserve_homes(tmp_path, monkeypatch, names=())
    monkeypatch.setattr('hermes_cli.profiles.get_active_profile_name', lambda: 'default')
    process_ownership.reserve([root])
    runner = _runner(root, homes)
    runner._running = True
    runner._primary_profile_name = 'default'
    captured = {}
    releases = []
    added_hooks = []
    secondary = root / 'profiles' / 'secondary'
    key = 'b' * 32

    async def reject_adapter(name, home, claimed):
        authority = runner.session_authorities.for_home(home)
        tasks = tuple(getattr(authority, '_bot_receipt_tasks', ()))
        assert len(tasks) == 1
        captured.update(authority=authority, watcher=tasks[0])
        await asyncio.sleep(0)  # Let the real receipt coroutine begin awaiting its future.
        assert not tasks[0].done()
        assert not authority.waiters[admission['admission_id']].done()
        raise MultiplexConfigError('fixture adapter configuration rejected')

    real_release = run_runtime.release_profile_home

    def release_after_retirement(current, home):
        if Path(home).resolve() == secondary:
            watcher = captured['watcher']
            assert process_ownership.owns(home)
            assert watcher.done() and watcher.cancelled()
            assert not captured['authority']._bot_receipt_tasks
            releases.append(str(home))
        return real_release(current, home)

    async def no_external_discovery(profiles):
        added_hooks.extend(name for name, _home in profiles)

    monkeypatch.setattr(runner, '_start_one_profile_adapters', reject_adapter)
    monkeypatch.setattr(runner, '_after_profiles_added', no_external_discovery)
    monkeypatch.setattr(run_runtime, 'release_profile_home', release_after_retirement)
    try:
        await run_runtime.initialize_gateway_runtime(runner)
        launch = runner.session_authorities.launch
        runner._record_served_profiles('default', homes)
        secondary.mkdir(parents=True)
        (secondary / 'config.yaml').write_text('{}\n')
        db = SessionDB(secondary / 'state.db')
        try:
            db.create_session('receipt-session', source='gui')
            epoch = begin_runtime_epoch(db, instance_id='prior-fixture-owner')
            admission = admit_session_input(db, epoch=epoch, principal_id='owner',
                session_id='receipt-session', request_id='bot:' + key,
                payload={'text': 'queued fixture delivery'})
        finally:
            db.close()
        with _locked(secondary) as mailbox:
            receipt_path = mailbox / f'{key}.json'
            _write(receipt_path, {'status': 'canonical', 'admission_id': admission['admission_id'],
                'delivery_id': key, 'profile_home': str(secondary), 'session_id': 'receipt-session',
                'principal_id': 'owner', 'message': 'queued fixture delivery'})

        result = await runner.reconcile_served_profiles()
        assert captured['watcher'].done(), 'real recovery-created receipt watcher outlived rejection'
        assert releases == [str(secondary)]
        assert added_hooks == []
        assert result['parked'] == ['secondary']
        assert result['added'] == []
        assert result['served_profiles'] == ['default']
        assert runner.session_authorities.for_home(secondary) is None
        assert not process_ownership.owns(secondary)
        assert runner.session_authorities.launch is launch
        assert process_ownership.owns(root)
        # Cancellation does not manufacture delivery success or rewrite queued work terminal.
        with _locked(secondary):
            record = _read(receipt_path)
        assert record['status'] == 'queued'
        assert record['admission_id'] == admission['admission_id']
    finally:
        watcher = captured.get('watcher')
        if watcher is not None and not watcher.done():
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
        if 'authority' in captured:
            for future in captured['authority'].waiters.values():
                if not future.done():
                    future.cancel()
        registry = getattr(runner, 'session_authorities', None)
        if registry is not None:
            if registry.for_home(secondary) is not None:
                await run_runtime.unserve_profile_runtime(runner, secondary)
            from gateway.session_cron import unbind_owner
            unbind_owner(registry.launch)
        runner.session_store.close_all_db_handles()
        runner.close_all_session_db_handles()
        for home in list(process_ownership.homes):
            process_ownership.release(home)
