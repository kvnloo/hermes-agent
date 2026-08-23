# Architecture Note: OMP /autoresearch → Hermes port (t_fce7eebf)

Implementation: `hermes_cli/autoresearch.py` (single module), wired via
`hermes_cli/main.py` (argparse), `hermes_cli/commands.py` (slash registry),
`cli.py` + `hermes_cli/cli_commands_mixin.py` (CLI dispatch).
Branch: `wt/t_fce7eebf` in `/workspace/zer0/oss/hermes-agent/.worktrees/t_fce7eebf`.

## Provenance / attribution

Ported from OMP (`/workspace/omp`, MIT license, Copyright 2025 Mario Zechner;
2025-2026 Can Bölück). Behavioral contracts (state math, storage schema,
branch handling, METRIC/ASI parsing, lifecycle semantics) are ported; the
Python module header carries the required MIT attribution notice. No OMP
code was copied verbatim — this is a behavioral port to Python/Hermes.

## Component mapping (OMP → Hermes)

| OMP module | Hermes port | Notes |
|---|---|---|
| index.ts (extension, command handler) | `run_slash()` + `hermes autoresearch` argparse | CLI-first; slash registry parity |
| state.ts (ExperimentState math) | `current_results/find_baseline_*/find_best_kept_metric/compute_confidence/sorted_median` | 1:1 port of segment/baseline/confidence math |
| storage.ts (SQLite WAL, sessions/runs) | `AutoresearchStorage` + SCHEMA_SQL | Same schema shape + `provider`/`model` pin columns; `$HERMES_HOME/autoresearch/<project-key>.db` |
| git.ts (branch ensure, dirty parsing) | `ensure_autoresearch_branch`, `git_dirty_paths` | Hardened: refuses non-git dirs (OMP warns + continues); `-z` porcelain parsing ported |
| helpers.ts (metric/ASI parsing, killTree, path specs) | `parse_metric_lines`, `parse_asi_lines`, `sanitize_*`, `_kill_process_tree`, `path_matches_spec` | DENIED_KEY_NAMES prototype-pollution guard ported |
| tools/init-experiment.ts | `cmd_init` | Harness must exist AND be committed (OMP only auto-commits) |
| tools/run-experiment.ts | `cmd_run` + `run_experiment_process` | Process-group kill via `start_new_session` + `killpg`; full log to `$HERMES_HOME/autoresearch/<key>/runs/NNNN/benchmark.log` |
| tools/log-experiment.ts | `cmd_log` | KEEP commits modified files; discard resets to HEAD only (prior keeps survive) |
| tools/update-notes.ts | deferred | Notes column exists in schema; CLI verb not yet exposed (documented gap) |
| dashboard.ts / shortcuts | deferred | No dashboard polish before durable loop (per task); `hermes autoresearch status/runs` covers the read surface |
| prompt*.md / resume-message.md | `run_slash()` static instruction text | See cache-safety below |
| tests/autoresearch-*.test.ts | `tests/hermes_cli/test_autoresearch.py` | 30 tests: parsing, branch isolation, full lifecycle, security, isolation, model pin, cache-stability guard |

## Cache-safety adaptation (the critical one)

OMP toggles four experiment tools in/out of the live toolset via
`setActiveTools` and rewrites the system prompt every turn
(`before_agent_start`). Both violate Hermes invariants (mid-conversation
toolset/schema mutation breaks prompt caching; system prompt must be
byte-stable).

Hermes design instead:
- `/autoresearch <goal>` returns a **static instruction string** delivered
  as the command's printed output (user-visible), seeding the agent's next
  turn — same pattern as skill commands.
- The agent drives the loop through the **existing** `terminal`/file tools
  (`hermes autoresearch run/log/...`). Zero new model tools; zero toolset
  mutation; system prompt untouched. Footprint ladder rung 2 (CLI command).
- `TestCacheStability` asserts the module exposes no tool-registration or
  toolset-mutation surface at all.

## Security hardening vs OMP

- OMP: "edits are not blocked" — scope deviations on KEEP are only warned.
  Hermes: **KEEP is REFUSED** when modified paths hit off-limits/scope
  violations without explicit `--justification`. Nothing is logged or
  committed. Fail closed.
- OMP: continues unisolated outside git. Hermes: refuses (pure-jj and
  non-git both fail closed).
- Harness: must exist AND be fully committed before `init` (frozen per
  segment; baseline = HEAD at init).
- Discard: `git reset --hard HEAD` + `clean -fd` **only on a dedicated
  `autoresearch/*` branch**; off-branch discard restores only run-modified
  tracked paths and removes only run-created untracked files (pre-run
  dirty snapshot protects user dirt). `clear --reset-tree` refuses to
  destroy user dirt outside an autoresearch branch.
- Model pin: sessions record provider/model; `require_canary_model`
  fails closed on anything but `nous/stealth/ox-alpha` (env-overridable
  via `HERMES_AUTORESEARCH_EXPECT_{PROVIDER,MODEL}` for other hosts).
- Timeout: process-group SIGKILL kills detached descendants (tested with
  a backgrounded grandchild).
- Malicious harness output: NaN/inf rejected, prototype-pollution keys
  dropped recursively from METRIC and ASI data.

## Profile isolation

State lives at `$HERMES_HOME/autoresearch/--<repo-path-mangled>--.db`
(WAL, busy_timeout 5s, foreign keys). Our own WAL traffic is filtered out
of dirty-path detection (`_is_state_path`) so state writes never read as
user dirt. Tested: two projects → independent DBs/id spaces.

## Documented parity gaps (deliberate, not hidden)

1. No TUI dashboard/widget/overlay (OMP dashboard.ts) — read surface is
   `status`/`runs`; per task, no polish before durable loop.
2. No `update_notes` CLI verb (schema column exists).
3. Auto-continue (OMP `agent_end` resume pump) is agent-driven here: the
   model re-issues `hermes autoresearch run` each turn; there is no
   gateway-side auto-resume loop yet. Max-iteration stop is enforced
   server-side (session closes).
4. Segments exist (`--new-segment`) but no confidence-based segment
   promotion logic.
5. Hidden-evaluator / cold-warm distinctions: ASI metadata passthrough
   only; no separate hidden-eval harness identity yet.
6. Slack surface: adding `/autoresearch` at the 50-slash cap clamped
   `/platform`; `platform` was added to `_SLACK_VIA_HERMES_ONLY` per the
   documented convention (Telegram parity test enforces curation).

## Verification evidence

- `scripts/run_tests.sh tests/hermes_cli/test_autoresearch.py` → 30/30 pass.
- `tests/hermes_cli/test_commands.py` + `test_subcommands_batch.py` → pass
  (after the `_SLACK_VIA_HERMES_ONLY` curation).
- `tests/hermes_cli/` full dir: only pre-existing failures
  (`test_mcp_config.py`, `test_doctor.py` — fail identically on stashed
  base) + one parallel-load flake (`test_kanban_dispatch_health.py`,
  passes consistently in isolation and with our file).
- Live canary (`/tmp/ar-canary-fresh/repo`): slash enter → harness commit →
  init (branch `autoresearch/session-20260823`) → baseline KEEP(50ms) →
  improvement KEEP(30ms, committed) → regression DISCARD (reset to HEAD,
  kept commit survived, worktree restored to `WORK = 3`) → status → bare
  toggle off → resume → tampered-harness KEEP **REFUSED** →
  `clear --reset-tree` rolled back to baseline (`WORK = 5`), session closed.
- CLI smoke: `hermes autoresearch --help` / `status` via the real parser.
