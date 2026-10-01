#!/usr/bin/env bash
# usage: run_arm_v3.sh <arm> <rep> <logname> <files...>
# Round-1 fix re-proof. Overlays the arm's files onto the worktree (at the
# amended staging commit on current main), plus the carrier tests from the
# published diffs (c54575-rebased-on-main.diff + 5f3f5896a4) when
# CARRIER_TESTS=1 (default), runs the files, then restores the worktree to HEAD.
# Arms: base (no production change) | both+fold (built on current main from
# c54575-rebased-on-main.diff + cherry-pick 5f3f5896a4 + foldin diff).
# Never uses git stash.
set -uo pipefail
S=${S:?set S to the scratch dir}
WT=${WT:?set WT to the worktree}
P=$S/st-edit-fuzzy
O=$P/overlay-v3
TH=$S/testhome-sf-edit-fuzzy-wrong-region
arm=$1; rep=$2; logname=$3; shift 3
cd "$WT" || exit 99
git checkout -q HEAD -- tools tests
if [ "${CARRIER_TESTS:-1}" = "1" ]; then
  cp "$O/both+fold/tests/tools/test_fuzzy_match.py" tests/tools/test_fuzzy_match.py
  cp "$O/both+fold/tests/tools/test_file_tools_live.py" tests/tools/test_file_tools_live.py
fi
if [ "$arm" != "base" ]; then
  cp "$O/$arm/tools/fuzzy_match.py" tools/fuzzy_match.py
fi
if [ -n "${SABOTAGE:-}" ]; then
  python3 "$P/sabotage.py" "$SABOTAGE" tools/fuzzy_match.py || { git checkout -q HEAD -- tools tests; exit 98; }
fi
mkdir -p "$P/runs-v3/$arm"
log="$P/runs-v3/$arm/$logname.rep$rep.log"
fm_sha=$(sha256sum tools/fuzzy_match.py | cut -c1-16)
mkdir -p "$TH/.hermes"
{
  echo "# arm=$arm rep=$rep sabotage=${SABOTAGE:-none} carrier_tests=${CARRIER_TESTS:-1} head=$(git rev-parse --short=10 HEAD) main=$(git rev-parse --short=10 HEAD^) fuzzy_match.py sha256[:16]=$fm_sha"
  echo "# files: $*"
  HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=${HERMES_PYTHON:?} \
    bash scripts/run_tests.sh -j 2 "$@" -q -m 'not live and not integration' 2>&1
  echo "# rc=$?"
} > "$log"
git checkout -q HEAD -- tools tests
grep -E "^\[.*\] [✓✗]" "$log" | sed 's/^\[[^]]*\] //'
grep -E "^=== Summary" "$log"
