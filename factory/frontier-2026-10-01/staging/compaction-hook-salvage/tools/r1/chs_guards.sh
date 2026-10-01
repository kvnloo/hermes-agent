#!/usr/bin/env bash
# E12 guards + adjacent tests for staging/compaction-hook-salvage, one arm per invocation.
# usage: chs_guards.sh <arm-label> <commitish> <run-id>
# Runs in the single staging worktree (checked out detached at <commitish>), isolated HOME/HERMES_HOME,
# loopback-only socket guard (tools/chs_loopback_guard.py). Writes raw/<run-id>/<arm>-*.{json,log}.
set -euo pipefail
ARM=$1; REF=$2; RUN=$3
S=$S
W=$ARTIFACTS/promotion-readiness-2026-10-01/wt/staging/compaction-hook-salvage
ST=$ARTIFACTS/frontier-2026-10-01/staging/compaction-hook-salvage
PY=<hermes-home>/hermes-agent/venv/bin/python
TH=$S/testhome-st-compaction-hook-salvage
OUT=$ST/raw/$RUN; mkdir -p "$OUT"
cd "$W"
test -z "$(git status --porcelain)"
git checkout -q --detach "$REF"
echo "$ARM $(git rev-parse HEAD) $(git rev-parse 'HEAD^{tree}')" >> "$OUT/arms.txt"
# Harness env: clean, isolated; the harnesses themselves hard-set HERMES_HOME to a fresh temp dir.
run_py() {  # <label> <args...>
  local label=$1; shift
  env -i PATH=/usr/bin:/bin HOME="$TH" HERMES_HOME="$TH/.hermes" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1 "$PY" "$@" > "$OUT/$ARM-$label.log" 2>&1 || echo "rc=$? ($label)" >> "$OUT/$ARM-$label.log"
}
run_py replay_gates "$ST/tools/chs_guard_wrap.py" "$W" evals/token_accounting/replay_gates.py "$OUT/$ARM-replay_gates.counts.json" --out "$OUT/$ARM-replay_gates.json"
run_py ab_checkpoint_preflight "$ST/tools/chs_guard_wrap.py" "$W" evals/native_compaction/ab_checkpoint_preflight.py "$OUT/$ARM-ab_checkpoint_preflight.counts.json" --out "$OUT/$ARM-ab_checkpoint_preflight.json"
# test_region_scoping.py is a script (run_mode() + __main__), not a pytest module.
env -i PATH=/usr/bin:/bin HOME="$TH" HERMES_HOME="$TH/.hermes" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$ST/tools" "$PY" -c "import chs_loopback_guard, runpy, sys; sys.argv=['evals/compaction/test_region_scoping.py']; sys.path.insert(0, '.'); runpy.run_path('evals/compaction/test_region_scoping.py', run_name='__main__')" \
  > "$OUT/$ARM-test_region_scoping.log" 2>&1 || echo "rc=$?" >> "$OUT/$ARM-test_region_scoping.log"
# Adjacent: sibling files of the touched seam (notify / manual compress / VALID_HOOKS consumers).
HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 \
  tests/agent/test_compaction_observer_hook_contract.py \
  tests/agent/test_compression_boundary_hook.py \
  tests/hermes_cli/test_cli_manual_compress.py \
  tests/hermes_cli/test_shared_metrics_engagement.py \
  tests/agent/test_compression_attempt_telemetry.py \
  tests/agent/test_auxiliary_hooks.py \
  tests/agent/test_shell_hooks.py \
  tests/gateway/test_gateway_platform_event_hook.py \
  -q > "$OUT/$ARM-adjacent.log" 2>&1 || true
test -z "$(git status --porcelain)"
echo "done $ARM"
