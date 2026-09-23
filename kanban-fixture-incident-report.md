# Kanban fixture contamination incident report

Incident: `req_20260824_kanban_reliability_troubleshoot`  
Board inspected read-only: `/home/kvn/.hermes/kanban/boards/zer0-company/kanban.db`  
Production mutations performed: **none**

## Root cause

The dominant writer was the standalone scale program `tests/stress/test_benchmarks.py`. Its `main()` created a temporary `HERMES_HOME`, but did not clear the `HERMES_KANBAN_*` variables inherited when it ran inside a dispatched Kanban worker. `kanban_db_path()` gives `HERMES_KANBAN_DB` precedence over `HERMES_HOME`, so all `seed_tasks()` calls continued writing to the worker-pinned `zer0-company` database.

The database fingerprint exactly matches that program:

- 26,635 rows have `tenant='bench'` and titles matching `bench N`.
- Creation was one uninterrupted five-minute run, 2026-08-21 12:39:09–12:44:09 CDT.
- Assignee/status phases match the benchmark sections: unassigned ready/todo/done rows, 4,435 `bench-worker` ready rows, and 941 `canary-worker` done/blocked rows caused when the live dispatcher claimed benchmark cards.
- The writer existed since Kanban's original stress suite (`c868425467`) and was removed as “never-executed” by `cce2d9418b` on 2026-08-23. This branch still contained/restored the standalone program, so deletion alone was not an isolation contract.

The bounded fix makes the benchmark remove every inherited `HERMES_KANBAN_*` route and then explicitly pins `HERMES_KANBAN_DB` to `<temporary-home>/kanban.db` before importing `hermes_cli.kanban_db`.

## Sibling fixture paths

Two earlier fixture writers also targeted this board:

- `created_by='desktop-e2e'`: 14 rows created 2026-08-17 20:01:45–20:01:47 CDT. Ten titles begin `Synthetic`; four are generated/decomposed children with fixture titles and `fixture-alpha` ownership.
- `created_by='preview-fixture'`: 6 rows created 2026-08-17 22:53:24 CDT, all with `Synthetic *` titles.
- An unmarked preview/geometry writer created 8 `Long card 0..7 detail...` rows in the same second, 2026-08-18 00:13:52 CDT, with null `created_by`/tenant and alternating `alpha`/`beta` assignment.

Current repository safeguards inspected:

- `tests/conftest.py` now strips all board/DB/task/workspace Kanban routing variables from every pytest test, preventing inherited worker pins from reaching ordinary Python tests.
- Desktop `createSandbox()` sets a temporary `HERMES_HOME`; the current E2E environment builder is separately guarded against direct execution on a live Wayland desktop.
- The standalone stress benchmark does not run under pytest fixtures, which is why it requires its own explicit pin and regression.
- No current tracked source contains the exact Synthetic/Long-card seed strings. Their durable `created_by`, timestamp, title/body, and event payloads are therefore the authoritative provenance retained in the DB.

## Exact classification

The cleanup classifier intentionally uses independent, conjunctive provenance:

1. Benchmark rows: `tenant='bench'` plus numeric `bench` title shape: **26,635**.
2. Explicit fixture creators: `created_by IN ('desktop-e2e','preview-fixture')`: **20** (including four generated fixture children that a title-only count misses).
3. Unmarked long-card batch: exact creation second, null creator/tenant, and bounded `Long card [0-7] detail*` title shape: **8**.

The union is **26,663 distinct tasks**. None has a live claim or `current_run_id`. The supplied SQL fails closed unless that exact count is selected.

## Reversible cleanup dry-run

File: `kanban-fixture-quarantine.sql`

Default behavior:

- begins one transaction;
- snapshots each selected task's status and claim/run fields into an incident table keyed by task id;
- checks the exact expected count;
- changes selected task statuses to `archived` without deleting tasks, runs, events, comments, or links;
- prints selected/remaining counts;
- **ROLLBACKs by default**.

Verified on a fresh SQLite backup:

- dry-run selected: 26,663;
- non-archived selected rows after the in-transaction update: 0;
- after rollback, quarantine table did not exist and the copied DB retained its original 2 archived rows.

To apply only after explicit approval, replace the final `ROLLBACK` with `COMMIT` and run against an approved backup/copy first. The reversal transaction is included at the bottom of the file.

## Copied-DB performance evidence

Measured with real `hermes_cli.kanban_db` functions over ten iterations on `/tmp/zer0-company-incident-tb3f7445c.db`. The production DB was opened read-only only to create the SQLite backup.

| Operation | Before median | After median | Before result | After result |
|---|---:|---:|---:|---:|
| `list_tasks()` | 636.01 ms | 39.50 ms | 27,932 rows | 1,274 rows |
| `board_stats()` | 4.88 ms | 1.73 ms | fixture-heavy counts | fixture rows excluded |
| `dispatch_once(dry_run=True, reconcile_orphans=False, max_spawn=0)` | 147.22 ms | 10.22 ms | empty dispatch result | empty dispatch result |

Min/max ranges:

- list: 541.97–753.86 ms before; 30.65–63.42 ms after;
- stats: 4.29–6.80 ms before; 1.41–3.71 ms after;
- dispatch dry-run: 115.56–565.01 ms before; 8.60–352.45 ms after.

The copied DB had 27,934 total rows at backup time (the incident task itself was created after the initial 27,933 observation). Classification remained exactly 26,663.

## Regression evidence

Test: `tests/hermes_cli/test_kanban_benchmark_isolation.py`

RED was observed against the old benchmark behavior: the test failed because no isolation helper existed and inherited production routes remained authoritative. GREEN was then observed with the explicit sandbox DB pin. The behavioral assertion initializes the real Kanban DB resolver, proves it resolves to the temporary benchmark DB, and proves the simulated production DB was not created.
