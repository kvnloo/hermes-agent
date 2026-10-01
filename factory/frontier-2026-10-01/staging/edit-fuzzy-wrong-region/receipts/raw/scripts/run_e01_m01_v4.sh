#!/usr/bin/env bash
# Round-4 fix (rebased head on main 44a1ce9724): E01 (#111127 evals/edittool battery pinned at 5444b1a2a8) and the
# M01 meter probe on each arm, on the amended head's main. Direct calls, no model.
# Arms overlay tools/fuzzy_match.py from overlay-v4 (built on the declared main
# from the published diffs / PR heads). Never uses git stash.
set -uo pipefail
S=${S:?set S to the scratch dir}
P=$S/st-edit-fuzzy
WT=${WT:?set WT to the worktree}
TH=$S/testhome-sf3-edit-fuzzy-wrong-region
PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test interpreter}
cd "$WT" || exit 99
rm -rf evals/edittool
git -C "$S/h.git" archive 5444b1a2a8 evals/edittool | tar -x -C "$WT"
mkdir -p "$P/e01-v4" "$P/m01-v4" "$TH/.hermes"
for arm in "$@"; do
  git checkout -q HEAD -- tools tests
  [ "$arm" != "base" ] && cp "$P/overlay-v4/$arm/tools/fuzzy_match.py" tools/fuzzy_match.py
  echo "=== $arm head=$(git rev-parse --short=10 HEAD) fuzzy_match.py sha256[:16]=$(sha256sum tools/fuzzy_match.py | cut -c1-16)"
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
    $PY evals/edittool/runner.py --label "$arm" --output "$P/e01-v4/$arm.json" >/dev/null
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 \
    $PY evals/edittool/report.py "$P/e01-v4/$arm.json" > "$P/e01-v4/$arm.report.txt"
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 \
    $PY evals/edittool/test_edittool.py > "$P/e01-v4/$arm.tripwire.txt" 2>&1; echo "tripwire rc=$? ($(tail -1 "$P/e01-v4/$arm.tripwire.txt"))"
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
    $PY "$P/meter_probe.py" "$WT" > "$P/m01-v4/$arm.json"; echo "meter rc=$?"
done
git checkout -q HEAD -- tools tests
rm -rf evals/edittool
git status --short
