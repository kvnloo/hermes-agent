"""Regression tests for #134239 Gap 2 stale compression snapshots."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.compression_facade import _compression_snapshot_is_current
from agent.context_compressor import _DB_PERSISTED_MARKER


def _messages():
    return [
        {
            "role": "user",
            "content": "old prompt",
            "_row_id": 40,
            _DB_PERSISTED_MARKER: True,
        },
        {
            "role": "assistant",
            "content": "old answer",
            "_row_id": 41,
            _DB_PERSISTED_MARKER: True,
        },
    ]


def _agent(*, role="assistant", watermark=100, rotated=False):
    db = SimpleNamespace(
        get_active_message_watermark=Mock(return_value=watermark),
        get_message_role=Mock(return_value=role),
        get_session=Mock(
            return_value={
                "model_config": {
                    "compression_lineage": {
                        "rotated_to": "child" if rotated else None,
                    }
                }
            }
        ),
    )
    compressor = SimpleNamespace(_session_db=db)
    return SimpleNamespace(
        _session_db=db,
        context_compressor=compressor,
        session_id="session",
    ), db


@pytest.mark.parametrize(
    ("role", "expected"),
    [(None, False), ("assistant", True)],
)
def test_post_lease_guard_rejects_only_archived_held_tip(monkeypatch, role, expected):
    agent, db = _agent(role=role)
    monkeypatch.setattr(
        "agent.conversation_compression._session_was_rotated_by_compression",
        lambda *_args: False,
    )
    host_check = Mock(return_value=True)

    assert _compression_snapshot_is_current(agent, _messages(), host_check) is expected

    host_check.assert_called_once_with()
    db.get_active_message_watermark.assert_called_once_with("session")
    db.get_message_role.assert_called_once_with("session", 41)


def test_rotated_parent_is_left_for_child_adoption(monkeypatch):
    agent, db = _agent(role=None, rotated=True)
    monkeypatch.setattr(
        "agent.conversation_compression._session_was_rotated_by_compression",
        lambda *_args: True,
    )

    assert _compression_snapshot_is_current(agent, _messages()) is True

    db.get_active_message_watermark.assert_not_called()
    db.get_message_role.assert_not_called()


def test_host_snapshot_check_short_circuits_durable_probe(monkeypatch):
    agent, db = _agent()
    rotated = Mock(return_value=False)
    monkeypatch.setattr(
        "agent.conversation_compression._session_was_rotated_by_compression",
        rotated,
    )
    host_check = Mock(return_value=False)

    assert _compression_snapshot_is_current(agent, _messages(), host_check) is False

    rotated.assert_not_called()
    db.get_active_message_watermark.assert_not_called()
    db.get_message_role.assert_not_called()


def test_missing_watermark_preserves_legacy_fail_open(monkeypatch):
    agent, db = _agent(watermark=None)
    monkeypatch.setattr(
        "agent.conversation_compression._session_was_rotated_by_compression",
        lambda *_args: False,
    )

    assert _compression_snapshot_is_current(agent, _messages()) is True

    db.get_active_message_watermark.assert_called_once_with("session")
    db.get_message_role.assert_not_called()


def test_validation_error_fails_closed_before_summary(monkeypatch):
    agent, db = _agent()
    db.get_active_message_watermark.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(
        "agent.conversation_compression._session_was_rotated_by_compression",
        lambda *_args: False,
    )

    assert _compression_snapshot_is_current(agent, _messages()) is False

    db.get_message_role.assert_not_called()
