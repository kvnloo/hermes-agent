#!/usr/bin/env bash
# Sequential reruns on the final head after the proof driver: T0, E17, E17d, E17c, merged-tree tests, #92118 probe.
set -u
S=$ARTIFACTS/frontier-2026-10-01/staging/memory-prefetch-metric
W=$ARTIFACTS/promotion-readiness-2026-10-01/wt/stfix/memory-prefetch-metric
R=$S/mpm-r3
TH=$S/testhome-sf-memory-prefetch-metric
PY=<hermes-home>/hermes-agent/venv/bin/python
HEAD=569ad4d84b0f9888ea2598c2a8ea416b2c75bad6
OLD=519876fa02f5e5812f5763cef03c5fed054d6cf7
cd $W
test "$(git rev-parse HEAD)" = $HEAD && test -z "$(git status --porcelain)" || { echo "worktree not at clean head"; exit 1; }
echo "== T0"; env -i PATH=/usr/bin:/bin $PY -B $S/work/r3/t0_schema_contract_check_r3.py --repo $W --out $S/work/r3/t0_schema_contract_check_r3.json | head -3
echo "== E17"; env -i PATH=/usr/bin:/bin $PY -B $S/work/e17_prefetch_fault_probe.py --repo $W --base-mm $S/work/r3/base_memory_manager_d023a57f8b.py --out $S/work/r3/e17_result_r3.json > $S/work/r3/e17_run_r3.log 2>&1; echo rc=$?
echo "== E17d"; env -i PATH=/usr/bin:/bin $PY -B $S/work/r3/micro_attribution_r3.py --repo $W --base-mm $S/work/r3/base_memory_manager_d023a57f8b.py --sandbox-root $R --out $S/work/r3/micro_attribution_r3.json > $S/work/r3/micro_attribution_r3.log 2>&1; echo rc=$?
echo "== E17c"; env -i PATH=/usr/bin:/bin $PY -B $S/work/e17c_holographic_probe.py --repo $W --out $S/work/r3/e17c_result_r3.json > $S/work/r3/e17c_run_r3.log 2>&1; echo rc=$?
echo "== merged trees"
for pair in 124151:3ee6189dbad0485790893c5098b20f00d27a1d51 120042:641f6b94c5 126457:822f7b2835; do
  p=${pair%%:*}; h=${pair#*:}
  git checkout -q --detach $HEAD
  git -c user.name=x -c user.email=x@x merge -q --no-commit --no-ff $h >/dev/null 2>&1
  u=$(git diff --name-only --diff-filter=U | tr '\n' ' ')
  [ -n "$u" ] && python3 $R/resolve_keep_both.py
  files="tests/hermes_cli/test_shared_metrics_loop.py tests/agent/test_memory_provider.py"
  [ $p = 126457 ] && files="$files tests/agent/test_memory_health.py"
  env -u HERMES_HOME HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 $files -q > $S/work/r3/merged_${p}_tests.log 2>&1
  echo "#$p unmerged=[$u] $(grep '=== Summary' $S/work/r3/merged_${p}_tests.log) $(grep -o 'FAILED tests/[^ ]*' $S/work/r3/merged_${p}_tests.log | sort -u | tr '\n' ' ')"
  git merge --abort; git checkout -q -f --detach $HEAD
done
echo "== 92118 probe"
rm -f $R/probe_out.txt
for head in $OLD $HEAD; do
  git checkout -q --detach $head
  git -c user.name=x -c user.email=x@x merge -q --no-commit --no-ff 2ad5cc73fac3e519deec7d4d9ff6eccb494aa953 >/dev/null 2>&1
  python3 $R/resolve_92118.py >/dev/null
  cp $R/test_zz_probe_92118.py tests/hermes_cli/
  echo "head ${head:0:10}" >> $R/probe_out.txt
  env -u HERMES_HOME HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 1 tests/hermes_cli/test_zz_probe_92118.py -q 2>&1 | grep -E "=== Summary" >> $R/probe_out.txt
  rm -f tests/hermes_cli/test_zz_probe_92118.py
  git merge --abort; git checkout -q -f --detach $head
done
git checkout -q --detach $HEAD
sed 's/^/  /' $R/probe_out.txt > $S/work/r3/probe_92118_out.txt; cat $S/work/r3/probe_92118_out.txt
git log -1 --format=%h; git status --porcelain
