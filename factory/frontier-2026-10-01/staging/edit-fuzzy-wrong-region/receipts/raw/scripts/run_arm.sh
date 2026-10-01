#!/usr/bin/env bash
# usage: run_arm.sh <arm> <rep> <logname> <files...>
# Overlays the arm's files onto the worktree (at the staging commit), plus the
# union of both carriers' tests (cross-applied to every arm), runs the files,
# then restores the worktree to HEAD. Never uses git stash.
set -uo pipefail
S=${S:?set S to the scratch dir}
P=$S/st-edit-fuzzy
WT=${WT:?set WT to the worktree}
TH=$S/testhome-st-edit-fuzzy-wrong-region
arm=$1; rep=$2; logname=$3; shift 3
cd "$WT" || exit 99
git checkout -q HEAD -- tools tests
if [ "${CARRIER_TESTS:-1}" = "1" ]; then
  # carrier tests cross-applied to every arm (union of #54575 + #125376 tests)
  cp "$P/overlay/both/tests/tools/test_fuzzy_match.py" tests/tools/test_fuzzy_match.py
  cp "$P/overlay/both/tests/tools/test_file_tools_live.py" tests/tools/test_file_tools_live.py
fi
if [ "$arm" != "base" ]; then
  cp "$P/overlay/$arm/tools/fuzzy_match.py" tools/fuzzy_match.py
fi
if [ -n "${SABOTAGE:-}" ]; then
  python3 "$P/sabotage.py" "$SABOTAGE" tools/fuzzy_match.py || { git checkout -q HEAD -- tools tests; exit 98; }
fi
mkdir -p "$P/runs/$arm"
log="$P/runs/$arm/$logname.rep$rep.log"
fm_sha=$(sha256sum tools/fuzzy_match.py | cut -c1-16)
{
  echo "# arm=$arm rep=$rep sabotage=${SABOTAGE:-none} head=$(git rev-parse --short=10 HEAD) fuzzy_match.py sha256[:16]=$fm_sha"
  echo "# files: $*"
  HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=${HERMES_PYTHON:?} \
    bash scripts/run_tests.sh -j 2 "$@" -q -m 'not live and not integration' 2>&1
  echo "# rc=$?"
} > "$log"
git checkout -q HEAD -- tools tests
grep -E "^\[.*\] [✓✗]" "$log" | sed 's/^\[[^]]*\] //'
tail -1 "$log"
