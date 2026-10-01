#!/usr/bin/env bash
# Round-1: carrier suites + harness on (declared main x carrier) with the staging patch applied. Worktree = main + staging patch.
set -u
S=$1; W=$2; R=$3
# Published copy: the test venv python comes from HERMES_PYTHON; the as-run copy had it inline (its sha256 is in the receipt).
TH=$S/testhome-sf-postmortem-logcalls-zero-hit; PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
cd "$W"
M=aea969677c60a1bb72fe227fdfb98f196a2092cc
run_tests() { env -u __HERMES_ACTIVATED HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 "$@" -q 2>&1; }
arm() {
  local label=$1 tree=$2; shift 2; local files=("$@")
  git checkout "$tree" -- "${files[@]}"
  echo "== arm $label (main x carrier tree $tree) overlay: ${files[*]}"
  local tests=(evals/postmortem/tests/test_postmortem_harness.py tests/agent/test_turn_usage_log_line.py)
  [ -f tests/agent/test_cache_log_states.py ] && tests+=(tests/agent/test_cache_log_states.py)
  run_tests "${tests[@]}" > "$R/tests_$label.txt"; grep -E "Summary|✗" "$R/tests_$label.txt"
  for f in "${files[@]}"; do if git cat-file -e "HEAD:$f" 2>/dev/null; then git checkout HEAD -- "$f"; else git rm -q --cached "$f" 2>/dev/null; rm -f "$f"; fi; done
}
T1=$(git -C "$S/h.git" merge-tree --write-tree "$M" refs/pr/121135 | head -1); T2=$(git -C "$S/h.git" merge-tree --write-tree "$M" refs/pr/119713 | head -1)
arm a1_pr121135 "$T1" agent/turn_usage.py agent/usage_pricing.py tests/agent/test_cache_log_states.py tests/agent/test_turn_usage_log_line.py
arm a2_pr119713 "$T2" agent/turn_response_check.py agent/turn_usage.py tests/agent/test_turn_usage_log_line.py
echo "tree after restore: $(git write-tree)"; git status --short
