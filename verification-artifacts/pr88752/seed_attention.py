import os
import sys

os.environ["HERMES_HOME"] = sys.argv[1]
from hermes_cli import kanban_db as kb

kb.init_db()
conn = kb.connect()
try:
    active = kb.create_task(conn, title="Active actual task", body="Verify actual Electron attention lifecycle", assignee="reviewer", initial_status="running")
    settled = kb.create_task(conn, title="Settled actual task", body="Must appear only in settled disclosure", assignee="reviewer", initial_status="running")
    kb.update_task_attention(conn, settled, action="settle", actor="captain", source="seed", idempotency_key="settled-seed", expected_revision=0)
    snoozed = kb.create_task(conn, title="Snoozed actual task", body="Must not duplicate into active workflow", assignee="reviewer", initial_status="running")
    kb.update_task_attention(conn, snoozed, action="snooze", actor="captain", source="seed", idempotency_key="snoozed-seed", expected_revision=0, wake_at=1_900_000_000)
    conn.commit()
finally:
    conn.close()
