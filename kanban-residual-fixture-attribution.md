# Residual Kanban fixture attribution

Task: `t_764f1843`
Board: `zer0-company`
Production mutation: none; all DB inspection used SQLite read-only mode.

## Six `preview-fixture` Synthetic rows: exact writer attributed

The exact writer was task `t_4f2c775f`, run 309, session `20260817_224918_05e805`, not the three earlier preview tasks cited in the parent report.

Authoritative evidence:

- `/workspace/hermes-home/kanban/boards/zer0-company/logs/t_4f2c775f.log:21-52` defines the six titles and idempotency keys, then calls `kb.create_task` with body `Synthetic Tailnet preview fixture. Contains no user tasks, chats, or secrets.`, assignee `fixture-worker`, and `created_by="preview-fixture"`.
- The same log at lines 169-184 records the root-cause repair: remove every inherited `HERMES_KANBAN_*` variable before setting the isolated home/board.
- `kanban_show(t_4f2c775f)` comments explicitly disclose that the first #88716 wrapper inherited `HERMES_KANBAN_DB` and list all six resulting canonical IDs: `t_88f549e2`, `t_571dc2ab`, `t_f92ae139`, `t_b44c8ab7`, `t_1cb4d35a`, `t_1e52279f`.
- A read-only production query matches those IDs one-for-one by title, body, assignee, provenance, idempotency key, and common `created_at=1787025204`.

The writer was a one-off `/tmp/hermes-pr88716/.preview/mobile_preview.py` preview harness. Its certified replacement was isolated in the same task; it is not a current repository path.

## Eight NULL-provenance Long-card rows: attribution boundary

Exact IDs: `t_15ced879`, `t_3877fc55`, `t_bc49c14f`, `t_15a9fe29`, `t_058d2e75`, `t_8eb5007c`, `t_87a24eda`, `t_fc54bc17`.

The DB proves one loop-shaped writer but does not retain caller identity:

- all eight were created at Unix `1787030032` (`2026-08-18 00:13:52 CDT`);
- titles are `Long card 0..7` followed by exactly repeated `detail` text;
- even indices are assigned `beta`, odd indices `alpha`;
- all have `created_by`, `tenant`, `idempotency_key`, `body`, and `session_id` NULL;
- their `created` task_events also have `run_id=NULL` and payloads containing only the ordinary task fields.

Exhaustive retained-source searches found no creating command or source in:

- current repository sources;
- `/workspace/hermes-home/kanban/boards/zer0-company/logs`;
- retained `canary-worker`, `chiefstaff`, and `vanilla` session dumps.

Later terminal-output caches show only list/readback appearances of these IDs, not creation. Therefore the narrowest truthful attribution is: an unlogged one-off command using the normal Kanban create path, executed at 2026-08-18 00:13:52 CDT. No task ID, profile, or session can be assigned without inventing evidence.

## Sibling recreation-path audit

1. `tests/stress/test_benchmarks.py:26-34` is isolated by the parent fix: it strips inherited Kanban selectors and explicitly pins a disposable DB.
2. Pytest execution is guarded by `tests/conftest.py:593-685`, which fails closed on writes resolving beneath the real Kanban root.
3. The exact preview harness from `t_4f2c775f` was repaired in its retained one-off script and is not present in the repository.
4. Desktop's shared E2E environment remains a recreation risk: `apps/desktop/e2e/fixtures.ts:223-263` copies `process.env`, overrides `HERMES_HOME`, but does not remove stronger `HERMES_KANBAN_*` selectors. Any E2E backend path that writes Kanban can therefore escape the sandbox.
5. Direct stress scripts remain a recreation risk outside pytest: `tests/stress/test_atypical_scenarios.py:40-55` and `tests/stress/test_subprocess_e2e.py:31-38` set disposable `HERMES_HOME`/`HOME` while inheriting stronger Kanban selectors. The pytest autouse guard does not protect child processes or direct script execution.

A bounded follow-up should centralize fail-closed Kanban selector scrubbing/pinning for the shared Desktop E2E environment and every directly executable stress harness, with hostile-routing regression coverage. No production records should be touched.
