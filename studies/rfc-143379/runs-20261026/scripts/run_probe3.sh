#!/bin/bash
# Probe v2 (adds ambiguous-match vector) on exact SHAs, plus the sanitized-echo candidate on main.
set -u
L=${LAB:?set LAB to a scratch lab dir containing repo/, wt-study/ and probes/}
export PATH=$HOME/.local/bin:$PATH TMPDIR=$L/tmp HERMES_HOME=$L/home
unset OPENAI_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY NOUS_API_KEY
P=$L/probes/test_blocked_echo_probe.py; O=$L/out/probe3; mkdir -p $O
echo "probe_sha256=$(sha256sum $P | cut -d' ' -f1) candidate_script_sha256=$(sha256sum $L/probes/make_candidate.py | cut -d' ' -f1)"
MAIN=0107da5d2a362b1b0b29aff8ada3fd2d4437f88e
for v in $MAIN f90969aef6a62ae475370fe43cc9a0c6d11d3122 candidate; do
  sha=$v; [ $v = candidate ] && sha=$MAIN
  W=$L/wt-p2-$v; git -C $L/repo worktree add -q --detach $W $sha
  cd $W
  if [ $v = candidate ]; then python3 $L/probes/make_candidate.py $W; git diff > $O/candidate.patch; fi
  cp $P tests/tools/
  echo "### $v head=$(git rev-parse HEAD) patched=$([ $v = candidate ] && echo yes || echo no)"
  scripts/run_tests.sh tests/tools/test_blocked_echo_probe.py --file-retries 0 -- -q --junitxml=$O/$v.xml > $O/$v.log 2>&1; echo "probe_exit=$?"
  if [ $v = candidate ] || [ $v = $MAIN ]; then
    files=$(git ls-files 'tests/tools/test_memory*.py' 'tests/agent/test_*memory*.py' | tr '\n' ' ')
    echo "suite_files=$(echo $files | wc -w)"
    scripts/run_tests.sh $files --file-retries 0 -- -q > $O/$v.suite.log 2>&1; echo "suite_exit=$?"
    grep -E "^=== Summary" $O/$v.suite.log
  fi
  cd $L; git -C $L/repo worktree remove --force $W
done
echo PROBE3_DONE
