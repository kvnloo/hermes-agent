# OX1000 C2 — Kanban worker command policy: implementation report

Branch: wt/t_ead2c57e · Status: implemented, gated default-off, awaiting 100-run canary before any post-change claims.

## What shipped

1. **`agent/kanban_command_policy.py`** — module-level constant
   `KANBAN_COMMAND_POLICY` covering all four fixed-design clauses:
   - no heredoc / `python -c` / shell `-c` / `echo`/`cat` file creation → use `write_file`/`patch`;
   - identical terminal command ≥4 attempts in one session → stop and replan;
   - same-file patch failure ×2 → re-read exact contents; third edit replaces the enclosing unit/file;
   - unchanged file/range re-reads reuse existing results unless freshness matters.
   Plus `worker_command_policy_enabled()` (config gate), `load_worker_command_policy_enabled()`
   (`hermes_cli.config.load_config_readonly`), and `command_policy_hash()` — a deterministic
   SHA-256 digest for local comparison/instrumentation. No outbound telemetry.

2. **Injection point** — the existing kanban-worker system-prompt hook.
   `agent/agent_init.py` resolves the policy once at init (same site as
   `_kanban_worker_guidance`), storing `agent._kanban_command_policy`;
   `agent/system_prompt.py` appends it immediately after the kanban
   lifecycle block inside the **stable tier**. Properties:
   - byte-stable content, no timestamps/session counters → prompt-cache safe;
   - resolved once per session, never mutated mid-conversation → cache invariant preserved;
   - present only when `kanban_show` is in valid tools (dispatcher-spawned workers);
     non-Kanban sessions never see it by construction.

3. **Config gate** — `kanban.worker_command_policy` in `DEFAULT_CONFIG`
   (`hermes_cli/config_defaults.py`), default `False`. No new env var,
   no core model tool. Enable per profile/board with:
   `kanban: { worker_command_policy: true }` in config.yaml.

## Verification

- `scripts/run_tests.sh tests/agent/test_kanban_command_policy.py -q` — 13 passed.
  Covers: all four clauses, bounded size, byte-stable hash, gate default-off,
  gate truthy handling, DEFAULT_CONFIG declaration, real-config E2E via temp
  HERMES_HOME, once-only append after guidance in the stable tier,
  rebuild equality, non-Kanban absence, legacy-path fallback.
- Existing suites green: `tests/tools/test_kanban_tools.py`,
  `tests/hermes_cli/test_kanban_core_functionality.py`,
  `tests/hermes_cli/test_kanban_review_surfaces.py` — 65 passed.
- `scripts/measure_kanban_command_policy.py` smoke-tested against a fixture log dir.

## Measurement plan (next 100 runs)

Baseline (OX1000 F1/F9): 1717 approval blocks across six profiles; 654 default
+ 82 canary sessions with ≥4 identical commands; 201 sessions patching one file
≥3×; ~39% redundant read volume.

After enabling `kanban.worker_command_policy: true` on the canary profile:

```
python scripts/measure_kanban_command_policy.py --runs 100 \
    --kanban-root <board-root> --out /tmp/c2-report.json
```

Counters: approval blocks / 1k tool calls; sessions with identical-command
loops (≥4); patch-loop sessions (≥3 patches on one file); policy-presence
evidence count. Coverage is explicit (`unparsed` list). No post-change result
is quoted anywhere until ≥100 real runs exist under the enabled gate.
