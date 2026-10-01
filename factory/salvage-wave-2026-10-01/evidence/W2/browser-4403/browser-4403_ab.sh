#!/usr/bin/env bash
# usage: browser-4403_ab.sh <label> [git-ref-to-merge ...] ; runs the W2 regression test on refs/w2/main (+ merged refs)
set -u
S=$S
WT=$ARTIFACTS/promotion-readiness-2026-10-01/wt/W2/browser
E=$ARTIFACTS/salvage-wave-2026-10-01/evidence/W2/browser-4403
PY=<hermes-home>/hermes-agent/venv/bin/python
TH=$S/testhome-W2-browser-4403
label=$1; shift
mkdir -p $TH/.hermes; cp $S/w2-tripwire/pytest_live_guard.py $TH/.hermes/
cd "$WT" || exit 2
git reset -q --hard refs/w2/main && git clean -qfdx -e node_modules
echo "main=$(git rev-parse refs/w2/main)"
for ref in "$@"; do
  if git -c rerere.enabled=false -c user.name=w2 -c user.email=w2@local merge -q --no-ff --no-edit "$ref" >/dev/null 2>&1; then
    echo "MERGE $ref ($(git rev-parse --short "$ref")): clean"
  else
    echo "MERGE $ref: CONFLICT in: $(git diff --name-only --diff-filter=U | tr '\n' ' ')"; exit 3
  fi
done
cp "$E/test_browser_controller_session_profile.py" tests/gateway/test_browser_controller_session_profile.py
PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY \
  setsid -w bash scripts/run_tests.sh tests/gateway/test_browser_controller_session_profile.py -q -j 2 -rf -p no:randomly 2>&1 \
  | grep -vE '^\s+[0-9.]+s +tests/|^  (P50|<1s|<2s|Top|Total|Files)|Per-file subprocess' | tail -n 30
