"""Platform-inbound media ages out; owner-pasted images remain session-owned.

Platform documents stay during settlement while the transcript names them
(dokterdok N28), then expire after 24 hours. Local attachments do not."""
import os
import time

import pytest

from gateway.session_ingress_media import _media_root, capture_native_media, release_admission_media
from hermes_state import SessionDB
from hermes_state_runtime import admit_session_input, begin_runtime_epoch, claim_session_input, settle_session_input


def _settled_native_document(tmp_path, monkeypatch, note):
    from gateway.platforms.base import get_document_cache_dir
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    staged = get_document_cache_dir() / 'doc_1_report.pdf'
    staged.write_bytes(b'%PDF-1.4 retained')
    media = capture_native_media([staged])
    retained = media[0]['path']
    db = SessionDB(db_path=tmp_path / 'state.db')
    db.create_session('s', source='telegram')
    db.append_message('s', 'user', note(retained))
    epoch = begin_runtime_epoch(db, instance_id='owner')
    row = admit_session_input(db, epoch=epoch, principal_id='p', session_id='s', request_id='m1',
                              payload={'text': 'page 3?', 'native_text_v1': {'media': media}})
    claim = claim_session_input(db, epoch=epoch, session_id='s')
    settle_session_input(db, epoch=epoch, admission_id=row['admission_id'], generation=claim['generation'],
                         outcome='completed')
    return db, row, retained


@pytest.mark.parametrize('note', [
    lambda path: f"[The user sent a document: 'report.pdf'. It is saved at: {path}.]",
    # A docker/modal backend's agent-visible spelling of the same retained file.
    lambda path: "It is saved at: /root/.hermes/cache/documents/" + path.split('/documents/', 1)[1],
], ids=['host-path', 'agent-visible-path'])
def test_settled_native_document_named_by_the_transcript_survives_settlement(tmp_path, monkeypatch, note):
    import gateway.session_ingress_media as media_module
    monkeypatch.setattr(media_module, '_last_sweep', {}, raising=False)
    db, row, retained = _settled_native_document(tmp_path, monkeypatch, note)
    try:
        release_admission_media(db, row['admission_id'])
        assert os.path.exists(retained), 'the follow-up turn is told to open a path settlement deleted'
        # Settled and older than main's media age: collected whatever the transcript says.
        old = time.time() - 25 * 3600
        os.utime(retained, (old, old))
        monkeypatch.setattr(media_module, '_last_sweep', {}, raising=False)
        release_admission_media(db, row['admission_id'])
        assert not os.path.exists(retained) and list(_media_root().iterdir()) == []
    finally:
        db.close()


def test_owner_pasted_image_survives_platform_media_age_sweep(tmp_path, monkeypatch):
    """A terminal desktop paste is still the owner's file after 25 hours (#150887)."""
    from gateway.platforms.base import get_image_cache_dir
    import gateway.session_ingress_media as media_module

    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    staged = get_image_cache_dir() / 'pasted.png'
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 8)
    owner_media = capture_native_media([staged])
    retained = owner_media[0]['path']
    db = SessionDB(db_path=tmp_path / 'state.db')
    try:
        db.create_session('owner-chat', source='desktop')
        db.append_message('owner-chat', 'user', f"Look\n\n[Image attached at: {retained}]")
        epoch = begin_runtime_epoch(db, instance_id='owner')
        row = admit_session_input(
            db, epoch=epoch, principal_id='uid:1000', session_id='owner-chat',
            request_id='desktop-paste', payload={
                'text': 'Look',
                'attachments_v1': {'media': owner_media, 'media_types': ['image/png']},
            })
        claim = claim_session_input(db, epoch=epoch, session_id='owner-chat')
        settle_session_input(
            db, epoch=epoch, admission_id=row['admission_id'],
            generation=claim['generation'], outcome='completed')
        release_admission_media(db, row['admission_id'])
        assert os.path.isfile(retained)

        old = time.time() - 25 * 3600
        os.utime(retained, (old, old))
        monkeypatch.setattr(media_module, '_last_sweep', {}, raising=False)
        release_admission_media(db, row['admission_id'])
        assert os.path.isfile(retained), 'an owner paste is not platform-inbound cache'
    finally:
        db.close()
