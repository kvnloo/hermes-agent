from tests.fixtures.decision_ledger_store import LedgerStore


def test_decision_ledger_is_fifo_capped_and_survives_reopen(tmp_path):
    db = LedgerStore(tmp_path)
    db.create_session("session")
    for index in range(52):
        db.append_decision_ledger_entry("session", "correction", f"choice {index}", turn_id="turn")
    assert db.get_decision_ledger_entries("session") == [{"kind": "correction", "text": f"choice {index}", "turn_id": "turn"} for index in range(2, 52)]
    db.close()
    reopened = LedgerStore(tmp_path)
    reopened.create_session("child", parent_session_id="session")
    reopened.copy_decision_ledger_entries("session", "child")
    reopened.copy_decision_ledger_entries("session", "child")
    assert reopened.get_decision_ledger_entries("child") == reopened.get_decision_ledger_entries("session")
    reopened.close()
