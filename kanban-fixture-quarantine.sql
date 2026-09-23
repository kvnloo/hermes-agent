-- Dry-run fixture quarantine for incident req_20260824_kanban_reliability_troubleshoot.
-- DO NOT run against production without explicit human approval.
-- Default mode is a dry run: all changes are rolled back at the end.
-- This evidence packet is dry-run-only; do not replace ROLLBACK with COMMIT.
-- No rows are deleted; task/event/run audit evidence remains intact.

.bail on
BEGIN IMMEDIATE;

-- Connection-local by design: a persistent artifact from an older attempt
-- must never contribute IDs to this invocation's UPDATE.
CREATE TEMP TABLE incident_20260824_current_fixture_quarantine (
    task_id          TEXT PRIMARY KEY,
    original_status  TEXT NOT NULL,
    claim_lock       TEXT,
    claim_expires    INTEGER,
    worker_pid       INTEGER,
    current_run_id   INTEGER,
    quarantined_at   INTEGER NOT NULL
);

INSERT INTO incident_20260824_current_fixture_quarantine
SELECT id, status, claim_lock, claim_expires, worker_pid, current_run_id,
       unixepoch()
FROM tasks
WHERE (tenant = 'bench' AND title GLOB 'bench [0-9]*'
       AND substr(title, 7) NOT GLOB '*[^0-9]*')
   OR (created_by IN ('desktop-e2e', 'preview-fixture') AND title LIKE 'Synthetic %')
   OR (created_at = 1787030032 AND created_by IS NULL AND tenant IS NULL
       AND title GLOB 'Long card [0-7] detail*');

-- Fail closed unless the exact observed incident population is selected.
CREATE TEMP TABLE fixture_count_guard (n INTEGER CHECK (n = 26659));
INSERT INTO fixture_count_guard
SELECT count(*)
FROM tasks
WHERE (tenant = 'bench' AND title GLOB 'bench [0-9]*'
       AND substr(title, 7) NOT GLOB '*[^0-9]*')
   OR (created_by IN ('desktop-e2e', 'preview-fixture') AND title LIKE 'Synthetic %')
   OR (created_at = 1787030032 AND created_by IS NULL AND tenant IS NULL
       AND title GLOB 'Long card [0-7] detail*');

UPDATE tasks
SET status = 'archived', claim_lock = NULL, claim_expires = NULL,
    worker_pid = NULL, current_run_id = NULL
WHERE id IN (SELECT task_id FROM incident_20260824_current_fixture_quarantine);

SELECT 'dry-run fixture rows' AS metric, count(*) AS value
FROM incident_20260824_current_fixture_quarantine
UNION ALL
SELECT 'remaining non-archived fixtures', count(*)
FROM tasks
WHERE status != 'archived'
  AND id IN (SELECT task_id FROM incident_20260824_current_fixture_quarantine);

ROLLBACK;

-- This packet intentionally has no COMMIT mode: the invocation-scoped TEMP
-- snapshot disappears with the connection. A separately reviewed apply
-- packet must persist an invocation ID and its exact snapshot before COMMIT.
