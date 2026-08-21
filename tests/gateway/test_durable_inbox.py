import concurrent.futures
import sqlite3

from gateway.inbox import GatewayInbox, InjectionOutcome


KEY = "opaque-high-entropy-key-00000001"


def accept(store, **overrides):
    values = dict(idempotency_key=KEY, source_id="plugin", session_key="telegram:1",
                  generation="session-1", role="user", payload="hello")
    values.update(overrides)
    return store.accept(**values)


def test_exact_replay_and_global_key_conflicts(tmp_path):
    store = GatewayInbox(tmp_path / "state.db")
    first = accept(store)
    assert first.outcome is InjectionOutcome.ACCEPTED
    assert accept(store) == type(first)(InjectionOutcome.ALREADY_ACCEPTED, first.inbox_id)
    for changed in ({"payload": "different"}, {"source_id": "other"},
                    {"session_key": "discord:1"}, {"generation": "session-2"}):
        assert accept(store, **changed).outcome is InjectionOutcome.CONFLICT
    with sqlite3.connect(tmp_path / "state.db") as conn:
        assert conn.execute("select count(*) from gateway_inbox").fetchone()[0] == 1


def test_concurrent_accept_creates_one_record(tmp_path):
    path = tmp_path / "state.db"
    GatewayInbox(path)
    def race(_):
        return accept(GatewayInbox(path)).outcome
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(race, range(24)))
    assert outcomes.count(InjectionOutcome.ACCEPTED) == 1
    assert set(outcomes) <= {InjectionOutcome.ACCEPTED, InjectionOutcome.ALREADY_ACCEPTED}


def test_lease_reclaim_turn_identity_and_retention(tmp_path):
    now = [1000.0]
    store = GatewayInbox(tmp_path / "state.db", clock=lambda: now[0])
    receipt = accept(store, retain_seconds=86400)
    row = store.lease_next("worker-a", lease_seconds=10)
    assert row and row.inbox_id == receipt.inbox_id
    assert store.lease_next("worker-b") is None
    now[0] += 11
    reclaimed = store.lease_next("worker-b")
    assert reclaimed and reclaimed.attempts == 2
    turn = store.claim_turn(reclaimed.inbox_id, "worker-b")
    assert turn and store.claim_turn(reclaimed.inbox_id, "worker-b") == turn
    assert store.finish(reclaimed.inbox_id, turn, "routed")
    assert store.compact()[1] == 0
    now[0] += 86400
    _, deleted = store.compact()
    assert deleted == 1


def test_validation_is_bounded_and_fail_closed(tmp_path):
    store = GatewayInbox(tmp_path / "state.db")
    assert accept(store, idempotency_key="short").outcome is InjectionOutcome.REJECTED
    assert accept(store, idempotency_key="x" * 257).outcome is InjectionOutcome.REJECTED
    assert accept(store, source_id="bad\nsource").outcome is InjectionOutcome.REJECTED
    assert accept(store, role="assistant").outcome is InjectionOutcome.REJECTED
    assert accept(store, payload="x" * 1_048_577).outcome is InjectionOutcome.REJECTED
