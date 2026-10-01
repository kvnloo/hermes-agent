#!/usr/bin/env bash
# usage: mem-config_ab.sh <label> [git-ref-to-merge ...] ; runs #126106's test file on refs/w2/main (+ merged refs)
set -u
S=/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad
WT=/mnt/zer0models/project-artifacts/hermes-agent/promotion-readiness-2026-10-01/wt/W2/memcfg
E=/mnt/zer0models/project-artifacts/hermes-agent/salvage-wave-2026-10-01/evidence/W2/mem-config
PY=/workspace/hermes-home/hermes-agent/venv/bin/python
TH=$S/testhome-W2-mem-config
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
cp "$E/test_memory_bootstrap_independence.py" tests/agent/test_memory_bootstrap_independence.py
PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY \
  setsid -w bash scripts/run_tests.sh tests/agent/test_memory_bootstrap_independence.py -q -j 2 -rf -p no:randomly --tb=line 2>&1 \
  | grep -E '^FAILED|Summary|^E  |MERGE|passed|failed' | grep -v '^\s*[0-9.]*s ' | sort -u | tail -n 40
