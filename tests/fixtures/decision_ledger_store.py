"""A real store opened on the storage interface, with the decision-ledger calls the ledger tests make.

``append_decision_ledger_entry`` goes through ``agent.decision_ledger.record_decision`` (bounding and redaction,
as every production writer does); the other verbs are the ``sessions`` repository's own.
"""

from persistence_assembly import open_persistence, profile_scope
from tests.fixtures.storage_holder import raw_holder
from tests.fixtures.storage_seed import seed_session


class LedgerStore:
    def __init__(self, home):
        self.store = open_persistence(profile_scope(home=home), eager=True)
        self.sessions = self.store.sessions

    def create_session(self, session_id, source="test", parent_session_id=None):
        if parent_session_id is None:
            seed_session(self.store, session_id, source)
        else:
            from persistence.conversation.sessions import NewSession
            self.sessions.create(NewSession(session_id=session_id, source=source, parent_session_id=parent_session_id))

    def append_decision_ledger_entry(self, session_id, kind, text, *, turn_id=""):
        from agent.decision_ledger import record_decision
        record_decision(self.sessions, session_id, kind, text, turn_id=turn_id)

    def get_decision_ledger_entries(self, session_id):
        return self.sessions.get_decision_ledger_entries(session_id)

    def copy_decision_ledger_entries(self, parent_session_id, child_session_id):
        self.sessions.copy_decision_ledger_entries(parent_session_id, child_session_id)

    def get_messages(self, session_id):
        from persistence.sqlite.conversation._store.messages import get_messages
        return get_messages(raw_holder(self.store), session_id)

    def archive_and_compact(self, session_id, messages):
        from persistence.sqlite.conversation._store.messages import archive_and_compact
        return archive_and_compact(raw_holder(self.store), session_id, messages)

    def _write_sql(self, sql, params=()):
        raw_holder(self.store)._execute_write(lambda conn: conn.execute(sql, params))

    def _read_all(self, sql, params=()):
        with raw_holder(self.store)._read_ctx() as conn:
            return conn.execute(sql, params).fetchall()

    def close(self):
        self.store.close()
