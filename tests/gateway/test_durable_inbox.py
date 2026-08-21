import concurrent.futures
import sqlite3

from gateway.inbox import GatewayInbox, InjectionOutcome
from hermes_state import SessionDB


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
    with sqlite3.connect(tmp_path / "state.db") as conn:
        conn.execute("""CREATE TABLE sessions(
            id TEXT PRIMARY KEY, session_key TEXT, message_count INTEGER DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE messages(
            id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT,
            timestamp REAL, gateway_turn_id TEXT, gateway_turn_digest TEXT,
            gateway_turn_scope TEXT
        )""")
        conn.execute("CREATE UNIQUE INDEX turn_id ON messages(gateway_turn_id)")
        conn.execute("INSERT INTO sessions(id,session_key) VALUES('session-1','telegram:1')")
    durable = store.lease_turn("worker-b")
    assert durable and durable.turn_id == turn
    user_id = store.commit_user(durable, "worker-b")
    assert user_id and store.commit_user(durable, "worker-b") == user_id
    assert store.terminalize(turn, "worker-b")
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


def test_real_sessiondb_append_survives_crash_before_terminal_ack(tmp_path):
    path = tmp_path / "state.db"
    db = SessionDB(path)
    db.create_session("session-1", source="telegram", session_key="telegram:1")
    db.append_message("session-1", "user", "ordinary")
    db.append_message("session-1", "assistant", "ordinary response")
    store = GatewayInbox(path)
    receipt = accept(store)
    leased = store.lease_next("worker-a")
    turn_id = store.commit_turn(leased, "worker-a")
    turn = store.lease_turn("worker-a", turn_id=turn_id)
    message_id = store.append_durable_notification(turn, "worker-a")
    assert message_id

    # Simulate process loss after transcript commit but before terminal ack.
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE gateway_turns SET lease_expires=0 WHERE turn_id=?", (turn_id,))
    restarted = GatewayInbox(path)
    reclaimed = restarted.lease_turn("worker-b", turn_id=turn_id)
    assert reclaimed
    assert restarted.append_durable_notification(reclaimed, "worker-b") == message_id
    assert restarted.terminalize(turn_id, "worker-b")

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT role,content,gateway_turn_digest,gateway_turn_scope FROM messages "
            "WHERE gateway_turn_id=?", (turn_id,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["role"] == "user"
        assert rows[0]["content"] == "hello"
        assert rows[0]["gateway_turn_digest"]
        assert rows[0]["gateway_turn_scope"].endswith(":plugin:telegram:1:session-1")
        assert conn.execute("SELECT state FROM gateway_turns WHERE turn_id=?", (turn_id,)).fetchone()[0] == "terminal"
    db.close()
