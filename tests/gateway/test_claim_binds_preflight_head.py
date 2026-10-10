"""The FIFO claim is bound to the admission its preflight validated.

JoaoMarcos44 (PR #106742 review 5480193598, R3; earlier Xipong and sprmn24): ``_claim_next``
validates ``first`` and then awaits a claim write that selects whichever queued row is the head
by then. A cancellation of ``first`` committed while that writer waits lets the claim start the
successor, which ``_drain`` then executes without its own preflight.
"""
from types import SimpleNamespace

import pytest


async def _authority(tmp_path, monkeypatch):
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionSource, SessionStore
    from gateway.session_authority import LiveSession, SessionAuthority, initialize_session_authority

    async def answer(event):
        return 'ok'
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    store = SessionStore(tmp_path / 'sessions', GatewayConfig())
    runner = SimpleNamespace(_session_db=store._db, session_store=store, _draining=False,
                             _handle_message=answer, _adapter_for_source=lambda source: None)
    authority = await initialize_session_authority(runner, profile_id='p', instance_id='owner')
    store._db.create_session('s', source='telegram')
    authority.sessions['s'] = LiveSession(SessionSource(platform=Platform.TELEGRAM, chat_id='c'), 's')
    monkeypatch.setattr(SessionAuthority, '_schedule', lambda self, ref: None)
    return authority


@pytest.mark.asyncio
@pytest.mark.parametrize('race', ['cancel_head_while_claim_waits', 'unchanged_head'])
async def test_claim_starts_only_the_admission_its_preflight_checked(tmp_path, monkeypatch, race):
    import gateway.session_authority as sa
    from gateway.session_contract import Principal, SessionRef, Submission
    from hermes_state_runtime import cancel_session_input, get_session_admission

    authority = await _authority(tmp_path, monkeypatch)
    actor = Principal('human', 'p', frozenset({'session:submit'}), 't')
    ref = SessionRef('p', 's')
    a = await authority.submit(actor, Submission('a', ref, {'text': 'A'}, 'queue'))
    b = await authority.submit(actor, Submission('b', ref, {'text': 'B'}, 'queue'))

    real_claim = sa.claim_session_input
    def claim(db, **kwargs):
        if race == 'cancel_head_while_claim_waits':
            # A's cancellation commits while the claim's writer waits (it does not share the
            # mutation lock); the real claim transaction runs after it.
            cancel_session_input(db, epoch=authority.epoch, admission_id=a.admission_id)
        return real_claim(db, **kwargs)
    monkeypatch.setattr(sa, 'claim_session_input', claim)

    live = authority.sessions['s']
    row, first = await authority._claim_next(ref, live)
    assert first['admission_id'] == a.admission_id
    if race == 'unchanged_head':
        assert row['admission_id'] == a.admission_id
        return
    # The checked head is gone: nothing may start on A's verdict, and B waits for its own preflight.
    assert row is False
    assert get_session_admission(authority.db, admission_id=b.admission_id)['status'] == 'queued'
    monkeypatch.setattr(sa, 'claim_session_input', real_claim)
    row, first = await authority._claim_next(ref, live)
    assert first['admission_id'] == b.admission_id and row['admission_id'] == b.admission_id
