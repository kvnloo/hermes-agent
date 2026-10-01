#!/usr/bin/env bash
# X4 (staging fix, round 1): re-prove the amended fold-in on current main, sabotage the carrier hunk by hunk,
# and run every tests/tools/test_computer_use_*.py file on main and on main + the carrier.
#
# Arms are working-tree changes on top of the fold-in commit (HEAD of <worktree>), reset between arms:
#   main          fold-in only                                    RED expected (the 3 skip cases)
#   c126447       + diff 105568c155..8891ff469a (NousResearch#126447, MwC-Trexx, unmodified)
#   neg           c126447 with both selector assignments replaced by `pass` (combined negative control)
#   mut-<hunk>    c126447 with ONE production hunk reverted (per-hunk sabotage, see MUTANTS below)
#   seam          c126447 with _CuaDriverSession.supports_input_property forced to False
#   donor         + diff d0288be5b3..7e809555e6 (closed #113389); only ax_walk_bound is run
#   carrier-head  unmodified 8891ff469a with the fold-in file added (as if folded into #126447)
#
# Usage: TESTHOME=<scratch home> HERMES_PYTHON=<venv python> run_stfix_r1.sh <worktree> <out dir> [reps]
set -euo pipefail
WT=$1; OUT=$2; REPS=${3:-3}
: "${TESTHOME:?set TESTHOME to a scratch directory}" "${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}"
mkdir -p "$TESTHOME/.hermes" "$OUT"
export HOME=$TESTHOME HERMES_HOME=$TESTHOME/.hermes HERMES_PYTHON
unset __HERMES_ACTIVATED || true
cd "$WT"
FOLDIN=$(git rev-parse HEAD)
LANE=tests/tools/test_computer_use_capture_lane_schema.py
CONTRACT="$LANE tests/tools/test_computer_use_cheap_lanes.py tests/tools/test_computer_use_ax_walk_bound.py"
ADJ=$(git ls-tree --name-only "$FOLDIN" tests/tools/ | grep -E '/test_computer_use(_.*)?\.py$' | grep -v "$LANE" | tr '\n' ' ')
echo "$ADJ" | tr ' ' '\n' | sed '/^$/d' > "$OUT/adjacent.files"

reset_tree() { git reset -q --hard; git clean -fdq -- tests tools; git checkout -q --detach "$FOLDIN"; }
carrier() { git diff 105568c155 8891ff469a | git apply --3way --whitespace=nowarn; git reset -q; }

mutate() {  # file old new  (exactly one occurrence must exist)
  python3 - "$@" <<'PY'
import pathlib, sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(path); s = p.read_text()
assert s.count(old) == 1, (path, old, s.count(old))
p.write_text(s.replace(old, new, 1))
PY
}

CAP=tools/computer_use/cua_backend_capture.py
apply_mutant() {
  case "$1" in
    mut-title)        mutate $CAP '    if not title:
        sc = out.get("structuredContent")' '    if False:
        sc = out.get("structuredContent")' ;;
    mut-guard)        mutate $CAP 'getattr(sess, "capabilities_discovered", False)' 'True' ;;
    mut-gate-vision)  mutate $CAP 'args["include_accessibility_tree"] = False' 'pass' ;;
    mut-gate-ax)      mutate $CAP 'args["include_screenshot"] = False' 'pass' ;;
    mut-vision-mcp)   mutate $CAP 'self._call_capture_tool("get_window_state", self._gws_args("vision"))' \
                                  'self._call_capture_tool("get_window_state", self._gws_args())' ;;
    mut-vision-cli)   mutate $CAP '"get_window_state", self._gws_args("vision"), 30.0, "vision screenshot",' \
                                  '"get_window_state", self._gws_args(), 30.0, "vision screenshot",' ;;
    mut-ws-mode)      mutate $CAP '"get_window_state", self._gws_args(mode), 30.0, "get_window_state",' \
                                  '"get_window_state", self._gws_args(), 30.0, "get_window_state",' ;;
    mut-capture-mode) mutate $CAP 'else self._capture_window_state(mode))' 'else self._capture_window_state())' ;;
    neg)              apply_mutant mut-gate-vision; apply_mutant mut-gate-ax ;;
    seam)             mutate tools/computer_use/cua_backend_session.py \
                        '        """Live tools/list schema accepts *property_name* (fails closed; no version guessing)."""
' '        """Live tools/list schema accepts *property_name* (fails closed; no version guessing)."""
        return False  # X4 seam sabotage
' ;;
  esac
}
MUTANTS="mut-title mut-guard mut-gate-vision mut-gate-ax mut-vision-mcp mut-vision-cli mut-ws-mode mut-capture-mode"

run_files() {  # label files...
  local label=$1; shift
  bash scripts/run_tests.sh -j 2 "$@" -q > "$OUT/$label.log" 2>&1 || true
}
record() {  # label
  git diff -- tools > "$OUT/$1.prod.diff"
  sha256sum $CAP tools/computer_use/cua_backend_session.py $LANE > "$OUT/$1.sha256"
}

date -Iseconds > "$OUT/started"
git rev-parse "$FOLDIN" "$FOLDIN^" 8891ff469a 7e809555e6 > "$OUT/revisions"

reset_tree; record main
for rep in $(seq 1 "$REPS"); do run_files "main.contract.r$rep" $LANE; done
run_files main.adjacent $ADJ

reset_tree; carrier; record c126447
for rep in $(seq 1 "$REPS"); do run_files "c126447.contract.r$rep" $CONTRACT; done
run_files c126447.adjacent $ADJ

for arm in neg seam; do
  reset_tree; carrier; apply_mutant "$arm"; record "$arm"
  for rep in $(seq 1 "$REPS"); do run_files "$arm.contract.r$rep" $CONTRACT; done
done

for m in $MUTANTS; do
  reset_tree; carrier; apply_mutant "$m"; record "$m"
  run_files "$m.contract.r1" $CONTRACT
done

reset_tree; git diff d0288be5b3 7e809555e6 | git apply --3way --whitespace=nowarn; git reset -q; record donor
run_files donor.ax_walk_bound tests/tools/test_computer_use_ax_walk_bound.py

reset_tree; git checkout -q --detach 8891ff469a; git show "$FOLDIN:$LANE" > "$LANE"; record carrier-head
for rep in $(seq 1 "$REPS"); do run_files "carrier-head.contract.r$rep" $CONTRACT; done

reset_tree
date -Iseconds > "$OUT/finished"
