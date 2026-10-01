#!/bin/bash
# Published copy: local paths come from the environment (S = scratch dir holding h.git, W = staging worktree,
# HERMES_PYTHON = test venv python). The as-run copy had them inline; its sha256 is the one cited in the receipts.
set -u
S=${S:?set S to the scratch dir holding h.git}
W=${W:?set W to the staging worktree}
TH=$S/testhome-st-postmortem-logcalls-zero-hit
PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
cd $W
run_tests() { env -u __HERMES_ACTIVATED HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 "$@" -q 2>&1; }
arm() {
  local label=$1 tree=$2; shift 2
  local files=("$@")
  git checkout $tree -- "${files[@]}"
  echo "== arm $label (tree $tree) overlay: ${files[*]}"
  git status --short
  timeout 300 $PY $S/pmlc/roundtrip.py $W $label main=$S/pmlc/logcalls.main.py patched=$W/evals/postmortem/forensics/logcalls.py > $S/pmlc/rt_$label.json 2> $S/pmlc/rt_$label.err; echo "roundtrip rc=$?"
  local tests=(evals/postmortem/tests/test_postmortem_harness.py tests/agent/test_turn_usage_log_line.py)
  [ -f tests/agent/test_cache_log_states.py ] && tests+=(tests/agent/test_cache_log_states.py)
  run_tests "${tests[@]}" > $S/pmlc/tests_$label.txt; grep -E "Summary|✗" $S/pmlc/tests_$label.txt
  # restore: overlay files back to HEAD; remove files HEAD does not have
  for f in "${files[@]}"; do if git cat-file -e HEAD:$f 2>/dev/null; then git checkout HEAD -- $f; else git rm -q --cached $f 2>/dev/null; rm -f $f; fi; done
  git status --short
}
T1=$(git -C $S/h.git merge-tree --write-tree main refs/pr/121135 | head -1); T2=$(git -C $S/h.git merge-tree --write-tree main refs/pr/119713 | head -1)
arm a1_pr121135 $T1 agent/turn_usage.py agent/usage_pricing.py tests/agent/test_cache_log_states.py tests/agent/test_turn_usage_log_line.py
arm a2_pr119713 $T2 agent/turn_response_check.py agent/turn_usage.py tests/agent/test_turn_usage_log_line.py
echo "HEAD now: $(git rev-parse HEAD)"; git status --short
