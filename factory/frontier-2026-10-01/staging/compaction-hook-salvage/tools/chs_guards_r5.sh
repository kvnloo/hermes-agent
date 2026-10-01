#!/usr/bin/env bash
# E12 guards + adjacent tests for staging/compaction-hook-salvage, r5 (one arm per invocation).
# r5: the r4 script plus the three neighbours of the compress_context finally that #127058 also edits
# (memory session switch, memory boundary commit, concurrent fork): 20 adjacent files.
# usage: chs_guards_r4.sh <arm-label> <commitish> <run-id> <worktree> <testhome> <python>
# Runs in the given worktree (checked out detached at <commitish>) with an isolated HOME/HERMES_HOME and the
# r4 egress guard (tools/chs_egress_guard_r4.py: connect + DNS blocked and logged with the thread name;
# nothing suppressed, so the openrouter-prewarm thread's lookup is counted too). The guard log
# ($testhome/chs-egress.log) and its stack dump (chs-egress.stacks, written because chs-egress.stacks-on exists)
# are truncated before and moved to raw/<run-id>/<arm>-<label>.egress.{log,stacks} after every harness, so
# each harness's blocked attempts are counted and attributed separately (FACTORY S16).
set -euo pipefail
ARM=$1; REF=$2; RUN=$3; W=$4; TH=$5; PY=$6
ST=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ST/raw/$RUN; mkdir -p "$OUT"
EG=$TH/chs-egress.log
STK=$TH/chs-egress.stacks
touch "$TH/chs-egress.stacks-on"
cd "$W"
test -z "$(git status --porcelain)"
git checkout -q --detach "$REF"
echo "$ARM $(git rev-parse HEAD) $(git rev-parse 'HEAD^{tree}')" >> "$OUT/arms.txt"
egress_reset() { rm -f "$EG" "$STK"; }
egress_take() { touch "$EG" "$STK"; mv "$EG" "$OUT/$ARM-$1.egress.log"; mv "$STK" "$OUT/$ARM-$1.egress.stacks"; }
run_py() {  # <label> <args...>
  local label=$1; shift
  egress_reset
  env -i PATH=/usr/bin:/bin HOME="$TH" HERMES_HOME="$TH/.hermes" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1 "$PY" "$@" > "$OUT/$ARM-$label.log" 2>&1 || echo "rc=$? ($label)" >> "$OUT/$ARM-$label.log"
  egress_take "$label"
}
run_py replay_gates "$ST/tools/chs_guard_wrap_r4.py" "$W" evals/token_accounting/replay_gates.py "$OUT/$ARM-replay_gates.counts.json" --out "$OUT/$ARM-replay_gates.json"
run_py ab_checkpoint_preflight "$ST/tools/chs_guard_wrap_r4.py" "$W" evals/native_compaction/ab_checkpoint_preflight.py "$OUT/$ARM-ab_checkpoint_preflight.counts.json" --out "$OUT/$ARM-ab_checkpoint_preflight.json"
# test_region_scoping.py is a script (run_mode() + __main__), not a pytest module.
egress_reset
env -i PATH=/usr/bin:/bin HOME="$TH" HERMES_HOME="$TH/.hermes" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$ST/tools" "$PY" -c "import chs_egress_guard_r4, runpy, sys; sys.argv=['evals/compaction/test_region_scoping.py']; sys.path.insert(0, '.'); runpy.run_path('evals/compaction/test_region_scoping.py', run_name='__main__')" \
  > "$OUT/$ARM-test_region_scoping.log" 2>&1 || echo "rc=$?" >> "$OUT/$ARM-test_region_scoping.log"
egress_take test_region_scoping
# Adjacent: the same 17 files as r3 (notify / manual compress / VALID_HOOKS consumers, hooks CLI payloads, plugin
# dispatch, compression commit/rotation/persistence, manual compress).
egress_reset
HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 \
  tests/agent/test_compaction_observer_hook_contract.py \
  tests/agent/test_compression_boundary_hook.py \
  tests/hermes_cli/test_cli_manual_compress.py \
  tests/hermes_cli/test_shared_metrics_engagement.py \
  tests/agent/test_compression_attempt_telemetry.py \
  tests/agent/test_auxiliary_hooks.py \
  tests/agent/test_shell_hooks.py \
  tests/gateway/test_gateway_platform_event_hook.py \
  tests/hermes_cli/test_hooks_cli.py \
  tests/hermes_cli/test_plugins.py \
  tests/hermes_cli/test_kanban_lifecycle_hooks.py \
  tests/agent/test_conversation_compression_manual.py \
  tests/agent/test_compression_rotation_state.py \
  tests/agent/test_compression_persistence.py \
  tests/agent/test_compression_commit_fence_race.py \
  tests/agent/test_compression_attempt_lifecycle.py \
  tests/agent/test_pre_compress_memory_context_handoff.py \
  tests/agent/test_memory_session_switch.py \
  tests/agent/test_memory_boundary_commit.py \
  tests/agent/test_compression_concurrent_fork.py \
  -q > "$OUT/$ARM-adjacent.log" 2>&1 || true
egress_take adjacent
test -z "$(git status --porcelain)"
echo "done $ARM"
