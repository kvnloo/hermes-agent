"""Contract tests for the session-serving backend slice (RFC #23717).

These assert the *contract*, not the implementation: every test drives the
``SessionServingBackend`` ABC and would pass against any backend that honors
it. The fixture wires the SQLite adapter around the real ``SessionDB`` on a
temp database, which both proves the current implementation satisfies the
slice unmodified and exercises the real storage path (no mocks).
"""

import time

import pytest

from hermes_state import SessionDB
from hermes_state_serving_backend import SessionServingBackend
from hermes_state_serving_backend_sqlite import SqliteSessionServingBackend


@pytest.fixture()
def backend(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    yield SqliteSessionServingBackend(db)
    db.close()


def test_backend_is_a_session_serving_backend(backend):
    assert isinstance(backend, SessionServingBackend)


def test_session_lifecycle_contract(backend):
    assert backend.create_session("s-life", "cli") == "s-life"
    # create is an upsert: repeating it does not reset or duplicate
    assert backend.create_session("s-life", "cli") == "s-life"
    assert backend.session_count() >= 1

    row = backend.get_session("s-life")
    assert row is not None and row["id"] == "s-life"
    assert row.get("end_reason") in (None, "")

    backend.end_session("s-life", "user_done")
    assert backend.get_session("s-life")["end_reason"] == "user_done"

    backend.reopen_session("s-life")
    assert backend.get_session("s-life").get("end_reason") in (None, "")

    assert backend.get_session("s-missing") is None
    assert backend.delete_session("s-life") is True
    assert backend.get_session("s-life") is None
    assert backend.delete_session("s-life") is False  # idempotent


def test_message_serving_contract(backend):
    backend.ensure_session("s-msg", "cli")

    backend.append_message("s-msg", "user", content="hello")
    backend.append_message("s-msg", "assistant", content="hi there",
                           finish_reason="stop")
    backend.append_messages_batch("s-msg", [
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
    ])
    assert backend.message_count("s-msg") == 4

    msgs = backend.get_messages("s-msg")
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    # insertion order: ids strictly increase
    ids = [m["id"] for m in msgs]
    assert ids == sorted(ids)

    conv = backend.get_messages_as_conversation("s-msg")
    assert [m["role"] for m in conv] == ["user", "assistant", "user", "assistant"]
    assert conv[0]["content"] == "hello"

    backend.replace_messages("s-msg", [{"role": "user", "content": "fresh"}])
    assert backend.message_count("s-msg") == 1
    assert backend.get_messages("s-msg")[0]["content"] == "fresh"

    backend.clear_messages("s-msg")
    assert backend.message_count("s-msg") == 0
    # session survives its messages
    assert backend.get_session("s-msg") is not None


def test_meta_title_count_contract(backend):
    backend.ensure_session("s-meta", "cli")

    assert backend.get_meta("contract-probe") is None
    backend.set_meta("contract-probe", "v1")
    assert backend.get_meta("contract-probe") == "v1"

    assert backend.get_session_title("s-meta") is None
    assert backend.set_session_title("s-meta", "Contract probe") is True
    assert backend.get_session_title("s-meta") == "Contract probe"

    n = backend.session_count()
    backend.ensure_session("s-meta-2", "cli")
    assert backend.session_count() == n + 1


def test_lease_is_compare_and_set(backend):
    scope, name = "compression", "s-lease"
    backend.ensure_session(name, "cli")

    assert backend.lease_acquire(scope, name, "holder-A") is True
    # a second holder cannot steal a live lease
    assert backend.lease_acquire(scope, name, "holder-B") is False
    # only the owner can refresh
    assert backend.lease_refresh(scope, name, "holder-B") is False
    assert backend.lease_refresh(scope, name, "holder-A") is True
    # release by a non-owner is a no-op: the owner still holds it
    backend.lease_release(scope, name, "holder-B")
    assert backend.lease_acquire(scope, name, "holder-B") is False
    backend.lease_release(scope, name, "holder-A")
    assert backend.lease_acquire(scope, name, "holder-B") is True
    backend.lease_release(scope, name, "holder-B")
    # release of an unheld lease is idempotent
    backend.lease_release(scope, name, "holder-B")


def test_lease_expired_is_reclaimed(backend):
    scope, name = "compression", "s-lease-exp"
    backend.ensure_session(name, "cli")

    assert backend.lease_acquire(scope, name, "holder-A", ttl_seconds=0.05) is True
    time.sleep(0.15)  # past the TTL; reclaim must succeed regardless of load
    assert backend.lease_acquire(scope, name, "holder-B") is True
    backend.lease_release(scope, name, "holder-B")


def test_lease_unknown_scope_rejected(backend):
    with pytest.raises(ValueError):
        backend.lease_acquire("search", "s-x", "holder")
