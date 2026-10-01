#!/usr/bin/env bash
# X2b: does each contract test actually exercise the production capability seam?
# On the c126447 arm, break ONLY _CuaDriverSession.supports_input_property (always False) and re-run the three
# contract files. A test that goes RED depends on the real seam; one that stays GREEN stubs it away (D3).
# Usage: run_seam_sabotage.sh <worktree> <out dir> <reps>
set -euo pipefail
WT=$1; OUT=$2; REPS=${3:-3}
S=${SCRATCH:?set SCRATCH to the scratch directory (holds the test home)}
TH=$S/testhome-st-cu-capture-mode-projection
mkdir -p "$TH/.hermes" "$OUT"
export HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
unset __HERMES_ACTIVATED || true
cd "$WT"
BASE=$(git rev-parse HEAD)
git reset -q --hard "$BASE"; git clean -fdq -- tests tools
git diff 105568c155 8891ff469a | git apply --3way --whitespace=nowarn; git reset -q
git show "7e809555e6:tests/tools/test_computer_use_capture_modes.py" > tests/tools/test_computer_use_capture_modes.py
python3 - <<'PY'
import pathlib
p = pathlib.Path("tools/computer_use/cua_backend_session.py"); s = p.read_text()
old = '        """Live tools/list schema accepts *property_name* (fails closed; no version guessing)."""\n'
assert old in s
p.write_text(s.replace(old, old + "        return False  # X2b sabotage\n", 1))
PY
git diff -- tools > "$OUT/seam-sabotage.prod.diff"
for rep in $(seq 1 "$REPS"); do
  bash scripts/run_tests.sh -j 2 tests/tools/test_computer_use_capture_lane_schema.py \
    tests/tools/test_computer_use_cheap_lanes.py tests/tools/test_computer_use_capture_modes.py -q \
    > "$OUT/seam-sabotage.r$rep.log" 2>&1 || true
done
git reset -q --hard "$BASE"; git clean -fdq -- tests tools
