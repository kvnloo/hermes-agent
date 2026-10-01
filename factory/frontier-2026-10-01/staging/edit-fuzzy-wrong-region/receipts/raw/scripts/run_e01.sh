#!/usr/bin/env bash
# E01: #111127 evals/edittool battery (pinned at 5444b1a2a8) on each arm, direct calls, no model.
set -uo pipefail
S=${S:?set S to the scratch dir}
P=$S/st-edit-fuzzy
WT=${WT:?set WT to the worktree}
TH=$S/testhome-st-edit-fuzzy-wrong-region
PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test interpreter}
cd "$WT" || exit 99
rm -rf evals/edittool
git -C "$S/h.git" archive 5444b1a2a8 evals/edittool | tar -x -C "$WT"
mkdir -p "$P/e01"
for arm in "$@"; do
  git checkout -q HEAD -- tools tests
  [ "$arm" != "base" ] && cp "$P/overlay/$arm/tools/fuzzy_match.py" tools/fuzzy_match.py
  echo "=== $arm fuzzy_match.py sha256[:16]=$(sha256sum tools/fuzzy_match.py | cut -c1-16)"
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
    $PY evals/edittool/runner.py --label "$arm" --output "$P/e01/$arm.json" >/dev/null
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 \
    $PY evals/edittool/report.py "$P/e01/$arm.json" | tee "$P/e01/$arm.report.txt"
  env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes TZ=UTC LANG=C.UTF-8 \
    $PY evals/edittool/test_edittool.py > "$P/e01/$arm.tripwire.txt" 2>&1; echo "tripwire rc=$? ($(tail -1 "$P/e01/$arm.tripwire.txt"))"
done
git checkout -q HEAD -- tools tests
rm -rf evals/edittool
git status --short
