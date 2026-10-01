#!/usr/bin/env bash
# E12 guards + adjacent tests for staging/compaction-hook-salvage, r3 (one arm per invocation).
# usage: chs_guards_r3.sh <arm-label> <commitish> <run-id> <worktree> <testhome> <python>
# Runs in the given worktree (checked out detached at <commitish>) with an isolated HOME/HERMES_HOME and the
# r3 egress guard (tools/chs_egress_guard.py: connect + DNS blocked, openrouter-prewarm suppressed). The
# guard log ($testhome/chs-egress.log) is truncated before and moved to raw/<run-id>/<arm>-<label>.egress.log
# after every harness, so each harness's blocked attempts are counted separately (FACTORY S16).
set -euo pipefail
ARM=$1; REF=$2; RUN=$3; W=$4; TH=$5; PY=$6
ST=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ST/raw/$RUN; mkdir -p "$OUT"
EG=$TH/chs-egress.log
cd "$W"
test -z "$(git status --porcelain)"
git checkout -q --detach "$REF"
echo "$ARM $(git rev-parse HEAD) $(git rev-parse 'HEAD^{tree}')" >> "$OUT/arms.txt"
egress_take() { touch "$EG"; mv "$EG" "$OUT/$ARM-$1.egress.log"; }
run_py() {  # <label> <args...>
  local label=$1; shift
  rm -f "$EG"
  env -i PATH=/usr/bin:/bin HOME="$TH" HERMES_HOME="$TH/.hermes" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1 "$PY" "$@" > "$OUT/$ARM-$label.log" 2>&1 || echo "rc=$? ($label)" >> "$OUT/$ARM-$label.log"
  egress_take "$label"
}
run_py replay_gates "$ST/tools/chs_guard_wrap.py" "$W" evals/token_accounting/replay_gates.py "$OUT/$ARM-replay_gates.counts.json" --out "$OUT/$ARM-replay_gates.json"
run_py ab_checkpoint_preflight "$ST/tools/chs_guard_wrap.py" "$W" evals/native_compaction/ab_checkpoint_preflight.py "$OUT/$ARM-ab_checkpoint_preflight.counts.json" --out "$OUT/$ARM-ab_checkpoint_preflight.json"
# test_region_scoping.py is a script (run_mode() + __main__), not a pytest module.
rm -f "$EG"
env -i PATH=/usr/bin:/bin HOME="$TH" HERMES_HOME="$TH/.hermes" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$ST/tools" "$PY" -c "import chs_egress_guard, runpy, sys; sys.argv=['evals/compaction/test_region_scoping.py']; sys.path.insert(0, '.'); runpy.run_path('evals/compaction/test_region_scoping.py', run_name='__main__')" \
  > "$OUT/$ARM-test_region_scoping.log" 2>&1 || echo "rc=$?" >> "$OUT/$ARM-test_region_scoping.log"
egress_take test_region_scoping
# Adjacent: the r2 set of 8 (notify / manual compress / VALID_HOOKS consumers) plus 8 more siblings of the
# touched seams (hooks CLI payloads, plugin dispatch, compression commit/rotation/persistence, manual compress).
rm -f "$EG"
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
  -q > "$OUT/$ARM-adjacent.log" 2>&1 || true
egress_take adjacent
test -z "$(git status --porcelain)"
echo "done $ARM"
