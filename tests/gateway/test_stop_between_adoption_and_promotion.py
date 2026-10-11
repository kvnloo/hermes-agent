"""A Stop between agent adoption and route promotion reaches the turn's fresh agent.

JoaoMarcos44 (PR #106742 review 5480193598, R4), confirming andrexibiza (r4238307333) and the
earlier report by dokterdok: ``adopt_agent`` records the generation while the route's running
slot can still name the previous cached agent. ``interrupt`` then stops that stale agent and,
because ``adopted == generation``, latches nothing, so the fresh agent runs the turn unstopped.
"""
import asyncio

import pytest

from tests.gateway.test_session_authority_cancel_settlement import ACTOR, REF, _authority, _submit, _wire_turn_agent
from tests.gateway.test_session_authority_preadopt_stop import Agent


@pytest.mark.asyncio
@pytest.mark.parametrize('stop', ['after_adoption', 'after_promotion'])
async def test_stop_after_adoption_reaches_the_fresh_agent(tmp_path, monkeypatch, stop):
    from gateway import session_finite

    db, authority = _authority(tmp_path, monkeypatch)
    stale, fresh = Agent(), Agent()
    cache = {'route': stale}  # the previous turn's reusable agent
    authority.runner._cached_agent_for = cache.get
    ready, stopped = asyncio.Event(), asyncio.Event()
    ran = {}

    async def execute(authority, ref, row):
        _wire_turn_agent(authority, row['generation'], fresh)  # the real adoption
        if stop == 'after_promotion':
            cache['route'] = fresh
        ready.set()
        await asyncio.wait_for(stopped.wait(), 5)
        cache['route'] = fresh  # route promotion
        ran[row['request_id']] = fresh.interrupted
        return 'done'
    monkeypatch.setattr(session_finite, 'execute_finite_admission', execute)

    with db:
        await _submit(authority, 'turn')
        await asyncio.wait_for(ready.wait(), 5)
        handle = await authority.interrupt(ACTOR, REF, authority._handle(REF).execution_generation)
        assert handle.execution_state == 'running'
        stopped.set()
        await asyncio.wait_for(authority.sessions['s'].task, 5)
        assert ran['turn'] is True, 'the agent this generation adopted must receive the Stop'
        assert not authority.pending_stops
