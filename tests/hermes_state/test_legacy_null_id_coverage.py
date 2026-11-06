"""Legacy untyped message ids must not abort compaction coverage matching.

Regression for ysun0804's #148742 report and the guard carried by #143407;
kouyichi also identified the other unnameable-row compaction sites.
"""

import sqlite3
from contextlib import closing

from hermes_state import SessionDB


def test_legacy_null_id_match_skipped_without_losing_named_match():
    # The old schema's bare id is NOT a rowid alias. Appends that omit id leave it NULL.
    with closing(sqlite3.connect(":memory:")) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE messages (
                id, session_id TEXT, role TEXT, content TEXT, active INTEGER
            );
            INSERT INTO messages (session_id, role, content, active)
                VALUES ('legacy', 'user', 'held', 1);
            INSERT INTO messages (id, session_id, role, content, active)
                VALUES (17, 'legacy', 'user', 'held', 1);
            INSERT INTO messages (id, session_id, role, content, active)
                VALUES (18, 'elsewhere', 'user', 'held', 1);
            INSERT INTO messages (id, session_id, role, content, active)
                VALUES (19, 'legacy', 'user', 'held', 0);
            """
        )
        assert conn.execute("SELECT id FROM messages WHERE rowid = 1").fetchone()[0] is None

        # Exercise the real coverage matcher, without initializing/migrating this legacy DB.
        db = object.__new__(SessionDB)
        assert db._matching_active_ids(
            conn, "legacy", {"role": "user", "content": "held"}
        ) == [17]
