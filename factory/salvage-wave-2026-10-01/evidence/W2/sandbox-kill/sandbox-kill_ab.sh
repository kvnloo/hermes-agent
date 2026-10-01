#!/usr/bin/env bash
# usage: sandbox-kill_ab.sh <label> [ref-to-merge ...] [-- extra test files]
# Resets the W2 sbkill worktree to refs/w2/main, merges each ref (rerere off),
# drops in the regression test and runs it (plus any extra files) isolated.
set -u
S=/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad
WT=/mnt/zer0models/project-artifacts/hermes-agent/promotion-readiness-2026-10-01/wt/W2/sbkill
E=/mnt/zer0models/project-artifacts/hermes-agent/salvage-wave-2026-10-01/evidence/W2/sandbox-kill
PY=/workspace/hermes-home/hermes-agent/venv/bin/python
TH=$S/testhome-W2-sandbox-kill
label=$1; shift
refs=(); extra=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then shift; extra=("$@"); break; fi
  refs+=("$1"); shift
done
mkdir -p "$TH/.hermes"; cp "$S/w2-tripwire/pytest_live_guard.py" "$TH/.hermes/"
cd "$WT" || exit 2
git reset -q --hard refs/w2/main && git clean -qfdx -e node_modules
echo "LABEL $label  main=$(git rev-parse HEAD)"
for r in ${refs[@]+"${refs[@]}"}; do
  if [ -f "$r" ]; then
    git apply --index "$r" && echo "APPLY $r: ok" || { echo "APPLY $r: FAILED"; exit 3; }
  elif git -c rerere.enabled=false -c user.name=w2 -c user.email=w2@local merge -q --no-ff --no-edit "$r" >/dev/null 2>&1; then
    echo "MERGE $r ($(git rev-parse --short "$r^{commit}")): clean"
  else
    echo "MERGE $r: CONFLICT in: $(git diff --name-only --diff-filter=U | tr '\n' ' ')"
    exit 3
  fi
done
cp "$E/test_sandbox_background_kill_tree.py" tests/tools/test_sandbox_background_kill_tree.py
if [ -n "${PROBE:-}" ]; then cp "$E/probe_sandbox_kill_term_ignored.py" tests/tools/test_w2_probe_sandbox_kill_term_ignored.py; extra+=(tests/tools/test_w2_probe_sandbox_kill_term_ignored.py); fi
before=$(wc -l < "$S/w2-tripwire/hits.log" 2>/dev/null || echo 0)
PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY \
  setsid -w bash scripts/run_tests.sh tests/tools/test_sandbox_background_kill_tree.py ${extra[@]+"${extra[@]}"} \
  -q -j 2 -rf -p no:randomly 2>&1 | grep -vE '^\s+[0-9.]+s +tests/|^  (P50|<1s|<2s|Total|Files|Top)' | tail -n 400
after=$(wc -l < "$S/w2-tripwire/hits.log" 2>/dev/null || echo 0)
echo "TRIPWIRE hits during run: $((after - before))"
