"""An in-flight capture owns its bytes until its admission commits or is refused.

JoaoMarcos44 (PR #106742 review 5480193598, R2; first reported by Greptile, r4238371654):
``_submit`` captures (or reuses) the immutable content-addressed path, then yields to the
off-loop admission write. A previous terminal turn's real ``release_admission_media`` can run
in that window and collect the same path, because no committed admission holds it yet. The
new admission then commits ``queued`` against bytes that no longer exist.
"""
import os
from types import SimpleNamespace

import pytest

_ONE_PX_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
)


async def _authority(tmp_path, monkeypatch):
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionSource, SessionStore
    from gateway.session_authority import LiveSession, initialize_session_authority

    async def answer(event):
        return 'ok'
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    store = SessionStore(tmp_path / 'sessions', GatewayConfig())
    runner = SimpleNamespace(_session_db=store._db, session_store=store, _draining=False,
                             _handle_message=answer, _adapter_for_source=lambda source: None)
    authority = await initialize_session_authority(runner, profile_id='p', instance_id='owner')
    store._db.create_session('s', source='telegram')
    authority.sessions['s'] = LiveSession(SessionSource(platform=Platform.TELEGRAM, chat_id='c'), 's')
    return authority


@pytest.mark.asyncio
@pytest.mark.parametrize('cleanup', ['before_capture', 'before_commit', 'after_commit'])
async def test_previous_turn_cleanup_never_collects_a_capture_awaiting_commit(tmp_path, monkeypatch, cleanup):
    import gateway.session_authority as sa
    import gateway.session_settlement_recovery as settlement
    from gateway.platforms.base import cache_image_from_bytes
    from gateway.session_contract import Principal, SessionRef, Submission
    from gateway.session_ingress_media import release_admission_media, restore_attachments
    from hermes_state_runtime import get_session_admission

    authority = await _authority(tmp_path, monkeypatch)
    actor = Principal('human', 'p', frozenset({'session:submit'}), 't')
    # The same staged file twice, so both admissions resolve the same content-addressed path.
    staged = cache_image_from_bytes(_ONE_PX_PNG, '.png')
    def submission(request_id):
        return Submission(request_id, SessionRef('p', 's'),
                          {'text': 'look', 'attachments': [{'path': staged, 'mime': 'image/png'}]}, 'queue')

    # The first turn settles for real; only its terminal cleanup is held back so it can land
    # at a chosen point of the second submission.
    deferred = []
    monkeypatch.setattr(settlement, '_release_media', lambda authority, row: deferred.append(row['admission_id']))
    first = await authority.submit(actor, submission('first'))
    await authority.sessions['s'].task
    assert get_session_admission(authority.db, admission_id=first.admission_id)['status'] == 'terminal'
    (first_id,) = deferred
    if cleanup == 'before_capture':
        release_admission_media(authority.db, first_id)

    monkeypatch.setattr(sa.SessionAuthority, '_schedule', lambda self, ref: None)
    real_admit = sa.admit_session_input
    def admit(*args, **kwargs):
        if cleanup == 'before_commit':
            # The second admission's writer is waiting; the first turn's real cleanup runs now.
            release_admission_media(authority.db, first_id)
        return real_admit(*args, **kwargs)
    monkeypatch.setattr(sa, 'admit_session_input', admit)

    second = await authority.submit(actor, submission('second'))
    if cleanup == 'after_commit':
        release_admission_media(authority.db, first_id)

    assert second.status == 'queued'
    row = get_session_admission(authority.db, admission_id=second.admission_id)
    assert row['status'] == 'queued'
    (reference,) = row['payload']['attachments_v1']['media']
    assert os.path.exists(reference['path'])
    with open(reference['path'], 'rb') as saved:
        assert saved.read() == _ONE_PX_PNG
    restore_attachments(row['payload'])
