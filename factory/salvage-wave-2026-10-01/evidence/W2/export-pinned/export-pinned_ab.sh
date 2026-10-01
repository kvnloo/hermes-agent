#!/usr/bin/env bash
# usage: export-pinned_ab.sh <label> [git-ref-to-merge | patch-file] [extra test files...]
# Resets the worktree to refs/w2/main, optionally merges a ref (rerere off) or applies a patch,
# drops the regression test in, and runs it (plus any extra files) with isolated HOME + tripwires.
set -u
S=/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad
WT=/mnt/zer0models/project-artifacts/hermes-agent/promotion-readiness-2026-10-01/wt/W2/export
EV=/mnt/zer0models/project-artifacts/hermes-agent/salvage-wave-2026-10-01/evidence/W2/export-pinned
PY=/workspace/hermes-home/hermes-agent/venv/bin/python
TH=$S/testhome-W2-export-pinned
mkdir -p "$TH/.hermes"; cp "$S/w2-tripwire/pytest_live_guard.py" "$TH/.hermes/"
label=$1; src=${2:-}; shift 2 2>/dev/null || shift $#
cd "$WT" || exit 2
git reset -q --hard refs/w2/main && git clean -qfdx -e node_modules
echo "label=$label main=$(git rev-parse refs/w2/main)"
if [ -n "$src" ]; then
  if [ -f "$src" ]; then
    git apply --index "$src" && echo "APPLY $src: ok" || { echo "APPLY $src: FAILED"; exit 3; }
  elif git -c rerere.enabled=false -c user.name=w2 -c user.email=w2@local merge -q --no-ff --no-edit "$src" >/dev/null 2>&1; then
    echo "MERGE $src ($(git rev-parse --short=12 "$src")): clean"
  else
    echo "MERGE $src: CONFLICT in: $(git diff --name-only --diff-filter=U | tr '\n' ' ')"; exit 3
  fi
fi
cp "$EV/test_sessions_export_filtered_pinned.py" tests/hermes_cli/test_sessions_export_filtered_pinned.py
PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY \
  setsid -w bash scripts/run_tests.sh tests/hermes_cli/test_sessions_export_filtered_pinned.py "$@" -q -j 2 -rf -p no:randomly 2>&1 \
  | grep -vE '^\s+[0-9.]+s +tests/|^  (P50|<1s|<2s|Total|Files|Top)' | tail -n 200
