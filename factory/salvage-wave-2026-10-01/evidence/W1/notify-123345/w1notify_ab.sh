#!/usr/bin/env bash
# usage: w1notify_ab.sh <label> [pr-number] ; runs the regression test on pinned main (+ merged PR)
set -u
S=/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad
W=/mnt/zer0models/project-artifacts/hermes-agent/promotion-readiness-2026-10-01/wt/W1/notify-123345
E=/mnt/zer0models/project-artifacts/hermes-agent/salvage-wave-2026-10-01/evidence/W1/notify-123345
PY=/workspace/hermes-home/hermes-agent/venv/bin/python
label=$1; pr=${2:-}
cd "$W" || exit 2
git reset -q --hard refs/w1/main && git clean -qfdx -e node_modules
if [ -n "$pr" ]; then
  if git -c user.name=w1 -c user.email=w1@local merge -q --no-edit --no-ff "refs/w1notify/pr/$pr" >/dev/null 2>&1; then
    echo "MERGE $pr: clean"
  else
    echo "MERGE $pr: CONFLICT in: $(git diff --name-only --diff-filter=U | tr '\n' ' ')"
    exit 3
  fi
fi
cp "$E/test_terminal_notify_string_bool.py" tests/tools/test_terminal_notify_string_bool.py
HOME=$S/testhome-W1-notify HERMES_HOME=$S/testhome-W1-notify/.hermes HERMES_PYTHON=$PY \
  bash scripts/run_tests.sh tests/tools/test_terminal_notify_string_bool.py -q -rf -p no:randomly 2>&1 | tail -n 25
