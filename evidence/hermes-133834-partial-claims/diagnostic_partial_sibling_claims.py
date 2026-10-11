"""New downstream partial-claim probe, 2026-10-11; AI authored by OpenAI Codex.

Credits: Brian Le (0xble) owns PR #133834. No production fix is included.
The refund assertion proposes arbitrary-error hardening; cancellation's contract
alone does not establish that contract. Uses real SessionDB and ledger writes.
"""
import asyncio
import json
import sqlite3
from unittest.mock import AsyncMock

import pytest

from hermes_state import SessionDB
from tools import async_delegation as ad
from gateway.run_notifications import GatewayNotificationsMixin


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(ad, "get_hermes_home", lambda: home)
    clock = [10000.0]
    monkeypatch.setattr(ad.time, "time", lambda: clock[0])
    db = SessionDB(home / "state.db")
    events = [{"type": "async_delegation", "delegation_id": name,
               "parent_session_id": "parent", "result": name}
              for name in ("primary", "first", "second")]
    with sqlite3.connect(home / "state.db") as conn:
        for evt in events:
            conn.execute("""INSERT INTO async_delegations
                (delegation_id, origin_session, state, dispatched_at,
                 completed_at, updated_at, event_json, result_json)
                VALUES (?, 'parent', 'completed', ?, ?, ?, ?, ?)""",
                (evt["delegation_id"], clock[0], clock[0], clock[0],
                 json.dumps(evt), json.dumps({"result": evt["result"]})))
    def rows():
        # A separate connection proves commits, not merely writer-local updates.
        with sqlite3.connect(home / "state.db") as conn:
            return {r[0]: r[1:] for r in conn.execute(
                "SELECT delegation_id, delivery_claim, delivery_claimed_at, "
                "delivery_attempts, delivery_state, result_json FROM async_delegations")}
    yield events, clock, rows
    db.close()


def caller(monkeypatch):
    from gateway import run
    monkeypatch.setattr(run, "_format_gateway_process_notification", lambda evt: evt["result"])
    runner = GatewayNotificationsMixin()
    runner._completion_delivery_identity = lambda evt: None
    runner._completion_delivery_ready = AsyncMock(return_value=True)
    runner._deliver_completion_notification = AsyncMock(return_value=True)
    return runner


def fail_second(monkeypatch, rows):
    real = ad.claim_event_delivery
    calls = []
    def claim(evt, consumer):
        calls.append(evt["delegation_id"])
        if evt["delegation_id"] == "second":
            assert rows()["first"][0] is not None
            assert rows()["first"][2] == 1
            raise RuntimeError("new probe: second sibling claim failed")
        return real(evt, consumer)
    monkeypatch.setattr(ad, "claim_event_delivery", claim)
    return calls


def test_partial_claim_characterization_and_strict_ttl(ledger, monkeypatch):
    events, clock, rows = ledger
    runner = caller(monkeypatch)
    calls = fail_second(monkeypatch, rows)
    with pytest.raises(RuntimeError, match="second sibling"):
        asyncio.run(runner._deliver_async_delegation_group_scoped(events))
    assert calls == ["first", "second"]
    runner._deliver_completion_notification.assert_not_awaited()
    state = rows()
    assert state["primary"][:4] == (None, None, 0, "pending")
    assert state["second"][:4] == (None, None, 0, "pending")
    assert state["first"][1:4] == (10000.0, 1, "pending")
    assert json.loads(state["first"][4]) == {"result": "first"}
    assert not ad.claim_completion_delivery("first", "immediate")
    clock[0] = 10300.0
    assert not ad.claim_completion_delivery("first", "exact-boundary")
    assert rows()["first"][:4] == state["first"][:4]
    clock[0] = 10300.001
    assert ad.claim_completion_delivery("first", "after-boundary")
    assert rows()["first"][:4] == ("after-boundary", 10300.001, 2, "pending")


def test_proposed_partial_claim_error_refunds_unadmitted_sibling(ledger, monkeypatch):
    events, _clock, rows = ledger
    runner = caller(monkeypatch)
    fail_second(monkeypatch, rows)
    with pytest.raises(RuntimeError, match="second sibling"):
        asyncio.run(runner._deliver_async_delegation_group_scoped(events))
    assert rows()["first"][:4] == (None, None, 0, "pending")


def test_successful_claim_handoff_and_explicit_defer_control(ledger, monkeypatch):
    events, _clock, rows = ledger
    runner = caller(monkeypatch)
    assert asyncio.run(runner._deliver_async_delegation_group_scoped(events)) is True
    runner._deliver_completion_notification.assert_awaited_once()
    handed = runner._deliver_completion_notification.call_args.kwargs["sibling_claims"]
    assert [evt["delegation_id"] for evt, _token in handed] == ["first", "second"]
    for evt, token in handed:
        name = evt["delegation_id"]
        assert rows()[name][:4] == (token, 10000.0, 1, "pending")
        assert ad.defer_completion_delivery(name, token)
        assert rows()[name][:4] == (None, None, 0, "pending")
        assert ad.claim_completion_delivery(name, "fresh")
        assert rows()[name][:4] == ("fresh", 10000.0, 1, "pending")
