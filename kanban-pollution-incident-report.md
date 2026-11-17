# Kanban fixture pollution incident report

Incident: `req_20260824_kanban_reliability_troubleshoot`

## Root cause

The P0 bulk writer was `tests/stress/test_benchmarks.py` as introduced by commit `c868425467` (`feat(kanban): durable multi-profile collaboration board`). The script set disposable `HERMES_HOME` and `HOME`, but did not clear the stronger inherited Kanban selectors. When run by a worker pinned to `HERMES_KANBAN_DB` / `HERMES_KANBAN_BOARD=zer0-company`, `kanban_db_path()` correctly honored that inherited production path before `HERMES_HOME` (`hermes_cli/kanban_db.py:713-735`).

The timestamps and counts identify the exact interrupted run: 26,635 `tenant='bench'` rows were inserted from 2026-08-21 17:39:09 through 17:44:09 UTC. The count decomposes as 11,100 dispatch seeds + 11,100 parent-graph seeds + 4,435 rows from the interrupted list benchmark. This matches the benchmark's section order and cardinalities exactly.

The bounded fix makes the benchmark clear every inherited `HERMES_KANBAN_*` selector and then explicitly pins `HERMES_KANBAN_DB` to `<temp-home>/kanban.db` before importing `kanban_db`. The regression test starts with hostile worker routing and proves only the disposable pin remains.

## Sibling fixture paths

- Ten `created_by='desktop-e2e'` `Synthetic %` rows came from the pre-fix `apps/desktop/e2e/kanban-mobile-shell.spec.ts` fixture. Its old `runBoardScript()` forwarded all of `process.env`; commit `a3ff680ccc` fixed this by deleting inherited Kanban routing, with follow-up fail-closed coverage in `9afa9fabfa` and `78b2d786a5`.
- Six `created_by='preview-fixture'` `Synthetic %` rows came from Kanban preview fixture work recorded in task logs `t_10cb0636`, `t_24253896`, and `t_026ae4df`; those scripts called `create_task(... created_by='preview-fixture')`. They were one-off worker preview scripts, not a current repository path.
- Eight `Long card [0-7] detail...` rows were created in one second at Unix time `1787030032`, with alternating `alpha`/`beta`, no tenant, and no `created_by`. No matching source exists in the repository or retained task/session command logs, so the originating one-off preview command cannot be attributed more narrowly without inventing evidence. Their exact row IDs and conjunctive fingerprint remain recoverable from the DB.
- Current pytest has an autouse real-Kanban write guard in `tests/conftest.py:593-685`, and current Desktop E2E sanitizes inherited Kanban selectors. The standalone scale benchmark was the remaining sibling bypass because it is executable directly rather than only through pytest.

## Exact read-only classification

Run:

`sqlite3 -readonly /path/to/kanban.db < kanban-fixture-classification.sql`

Observed production result:

| class | rows | first created | last created |
|---|---:|---:|---:|
| scale-benchmark | 26,635 | 1787333949 | 1787334249 |
| desktop-e2e | 10 | 1787014905 | 1787014907 |
| long-card-fixture | 8 | 1787030032 | 1787030032 |
| preview-fixture | 6 | 1787025204 | 1787025204 |

Total: 26,659. The predicates require numeric-only `bench N`, explicit synthetic provenance plus `Synthetic %`, or the exact one-second/NULL-provenance/long-card fingerprint. Four other `desktop-e2e` records are deliberately excluded because their titles are not part of this incident fixture set.

## Dry-run quarantine safety

`kanban-fixture-quarantine.sql` is dry-run-only and ends in `ROLLBACK`. It snapshots original status and claim fields in an invocation-scoped TEMP table, fails closed unless exactly 26,659 rows match, and updates only IDs selected into that TEMP table by the current invocation. A stale persistent `incident_20260824_fixture_quarantine` table cannot contribute IDs. The packet explicitly forbids changing `ROLLBACK` to `COMMIT`; any apply packet requires separate review and invocation-scoped persistent provenance. No production record was mutated.

The adversarial regression preloads a persistent stale snapshot ID for an unrelated human task. The old packet reported 26,660 updated rows (RED); the revised packet reports exactly 26,659 and leaves the copied DB byte-identical after rollback (GREEN).

## Copied-DB performance evidence

Reproduce from the repository root with the exact `runner_command` recorded in `kanban-quarantine-performance.json`, or choose fresh `--copy` / `--output` paths. `scripts/benchmark_kanban_fixture_quarantine.py` creates the copy with `sqlite3.Connection.backup`, records SQLite version, exact classification and workload SQL, source/copy SHA-256 before and after, three warmups and fifteen measured runs, and fails closed if the source changes during copy, classification differs from 26,659, selected active rows remain, or rollback changes the copied DB bytes.

| operation | before | after quarantine | rows before → after |
|---|---:|---:|---:|
| active task list | 19.351 ms | 2.614 ms | 27,940 → 1,282 |
| ready dispatch scan | 6.766 ms | 0.015 ms | 14,696 → 34 |
| status counts | 0.879 ms | 0.989 ms | 8 groups → 8 groups |

The copied DB used all 26,659 classified rows and verified zero classified active rows after quarantine. Production was read-only throughout.

## Verification

- RED: the new regression failed against the original benchmark with `AttributeError: ... has no attribute 'configure_benchmark_home'`.
- GREEN: `HERMES_PYTHON=/workspace/hermes-home/hermes-agent/venv/bin/python scripts/run_tests.sh tests/hermes_cli/test_kanban_benchmark_isolation.py -q` → 1 passed.
- Adversarial stale-snapshot RED: old packet reported `dry-run fixture rows|26660`.
- Adversarial stale-snapshot GREEN plus provenance runner: `scripts/run_tests.sh tests/hermes_cli/test_kanban_fixture_quarantine_packet.py -q` → 2 passed.
- Classification SQL returned exactly 26,659 incident rows.
- Reproducible run used SQLite 3.53.4; immutable online-backup copy SHA-256 before/after was `88aa682e577f3a4631cac6bf474a74cf5bd0a4586035a9ed8ed3cecf943e4a99`; source file hash was stable at `c66fed38d3db5cb1daaca2a3f5392cb239fe74b4795a0b9cc19e22ad6c0ac96f`.
