#!/usr/bin/env bash
# X2: A/B regression harness. Arms differ only in the production tree applied on top of the staging commit
# (which carries the fold-in contract test). Every arm also gets the OTHER implementations' own test files
# cross-applied, so each candidate is judged by its rival's contract too.
#
#   main      staging commit only (fold-in test on main)
#   c126447   + diff 105568c155..8891ff469a (NousResearch#126447, MwC-Trexx, unmodified)
#   donor     + diff d0288be5b3..7e809555e6 (fork feat/cu-capture-mode-projection-112639 = closed #113389)
#   neg-*     the arm with ONLY its selector-projection lines reverted (negative control)
#
# Usage: run_ab_arms.sh <worktree> <bare repo> <out dir> <reps>
set -euo pipefail
WT=$1; R=$2; OUT=$3; REPS=${4:-3}
S=${SCRATCH:?set SCRATCH to the scratch directory (holds the test home)}
TH=$S/testhome-st-cu-capture-mode-projection
mkdir -p "$TH/.hermes" "$OUT"
export HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
unset __HERMES_ACTIVATED || true
cd "$WT"
BASE=$(git rev-parse HEAD)
CONTRACT="tests/tools/test_computer_use_capture_lane_schema.py tests/tools/test_computer_use_cheap_lanes.py tests/tools/test_computer_use_capture_modes.py"
ADJ="tests/tools/test_computer_use_ax_walk_bound.py tests/tools/test_computer_use.py tests/tools/test_computer_use_null_pid_windows.py tests/tools/test_computer_use_capture_routing.py tests/tools/test_computer_use_fullscreen_capture.py tests/tools/test_computer_use_cua_backend_linux.py tests/tools/test_computer_use_screenshot_dedup.py tests/tools/test_computer_use_vision_routing.py tests/tools/test_computer_use_cua_0_9.py tests/tools/test_computer_use_capture_fence.py tests/tools/test_computer_use_zero_bounds.py"

reset_tree() { git reset -q --hard "$BASE"; git clean -fdq -- tests tools; }

cross_tests() {  # rival contract files, only when the arm did not bring its own copy
  [ -f tests/tools/test_computer_use_cheap_lanes.py ] || git show "refs/pr/126447:tests/tools/test_computer_use_cheap_lanes.py" > tests/tools/test_computer_use_cheap_lanes.py
  [ -f tests/tools/test_computer_use_capture_modes.py ] || git show "7e809555e6:tests/tools/test_computer_use_capture_modes.py" > tests/tools/test_computer_use_capture_modes.py
}

apply_arm() {
  case "$1" in
    main) ;;
    c126447) git diff 105568c155 8891ff469a | git apply --3way --whitespace=nowarn ;;
    donor) git diff d0288be5b3 7e809555e6 | git apply --3way --whitespace=nowarn ;;
    neg-c126447) apply_arm c126447
      python3 - <<'PY'
import re, pathlib
p = pathlib.Path("tools/computer_use/cua_backend_capture.py"); s = p.read_text()
s2 = s.replace('args["include_accessibility_tree"] = False', 'pass').replace('args["include_screenshot"] = False', 'pass')
assert s2 != s; p.write_text(s2)
PY
      ;;
    neg-donor) apply_arm donor
      python3 - <<'PY'
import pathlib
p = pathlib.Path("tools/computer_use/cua_backend_capture.py"); s = p.read_text()
s2 = s.replace("args[selector] = False", "pass")
assert s2 != s; p.write_text(s2)
PY
      ;;
  esac
  git reset -q  # 3way apply stages; keep it as a working-tree change only
}

run_files() {  # arm label files...
  local label=$1; shift
  bash scripts/run_tests.sh -j 2 "$@" -q > "$OUT/$label.log" 2>&1 || true
  tail -n 60 "$OUT/$label.log" | grep -E '^(FAILED|ERROR) |passed|failed|error' | tail -n 40 > "$OUT/$label.summary" || true
}

for arm in main c126447 donor neg-c126447 neg-donor; do
  reset_tree
  apply_arm "$arm"
  cross_tests
  git diff --stat > "$OUT/$arm.diffstat"
  git diff -- tools > "$OUT/$arm.prod.diff"
  sha256sum tools/computer_use/cua_backend_capture.py tests/tools/test_computer_use_capture_lane_schema.py \
    tests/tools/test_computer_use_cheap_lanes.py tests/tools/test_computer_use_capture_modes.py \
    tests/tools/test_computer_use_ax_walk_bound.py > "$OUT/$arm.sha256"
  for rep in $(seq 1 "$REPS"); do run_files "$arm.contract.r$rep" $CONTRACT; done
  case "$arm" in neg-*) ;; *) run_files "$arm.adjacent" $ADJ ;; esac
done
reset_tree
