#!/usr/bin/env bash
# usage: memmon-heartbeat_ab.sh <label> [port-diff] [extra test files...]
# Resets the worktree to pinned main, optionally applies a candidate port diff
# (main -> candidate re-anchored on main), drops in the regression test and runs it.
set -u
S=$S
WT=$ARTIFACTS/promotion-readiness-2026-10-01/wt/W2/memmon
EV=$ARTIFACTS/salvage-wave-2026-10-01/evidence/W2/memmon-heartbeat
PY=<hermes-home>/hermes-agent/venv/bin/python
TH=$S/testhome-W2-memmon-heartbeat
label=$1; port=${2:-}; shift; [ $# -gt 0 ] && shift
cd "$WT" || exit 2
git reset -q --hard refs/w2/main && git clean -qfdx -e node_modules
echo "label=$label main=$(git rev-parse HEAD) port=${port:-none}"
if [ -n "$port" ]; then
  git apply --index "$port" || { echo "PORT APPLY FAILED: $port"; exit 3; }
fi
cp "$EV/test_memory_monitor_gateway_wiring.py" tests/gateway/test_memory_monitor_gateway_wiring.py
mkdir -p "$TH/.hermes"; cp "$S/w2-tripwire/pytest_live_guard.py" "$TH/.hermes/"
before=$(wc -l < "$S/w2-tripwire/hits.log" 2>/dev/null || echo 0)
PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY \
  setsid -w bash scripts/run_tests.sh tests/gateway/test_memory_monitor_gateway_wiring.py "$@" -q -j 2 -rf -p no:randomly 2>&1 \
  | grep -vE '^\s+[0-9.]+s +tests/|^=== Per-file|Total subprocess|P50:|<1s:|Top 10' | tail -n 60
after=$(wc -l < "$S/w2-tripwire/hits.log" 2>/dev/null || echo 0)
echo "tripwire hits during run: $((after-before))"
