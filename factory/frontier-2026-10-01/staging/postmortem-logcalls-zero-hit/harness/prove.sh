#!/bin/bash
# Full proof on the exact staging commit. Outputs to $S/pmlc/final/.
# Published copy: local paths come from the environment (S = scratch dir, W = staging worktree,
# HERMES_PYTHON = test venv python). The as-run copy had them inline; its sha256 is the one cited in the receipt.
set -u
S=${S:?set S to the scratch dir}
W=${W:?set W to the staging worktree}
TH=$S/testhome-st-postmortem-logcalls-zero-hit
PY=${HERMES_PYTHON:?set HERMES_PYTHON to the test venv python}
O=$S/pmlc/final; rm -rf $O; mkdir -p $O
cd $W
echo "HEAD=$(git rev-parse HEAD) main=$(git rev-parse main)" | tee $O/heads.txt
run_tests() { env -u __HERMES_ACTIVATED HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 2 "$@" -q 2>&1; }
F=evals/postmortem/forensics/logcalls.py
# RED: committed tests, main's parser
git show main:$F > $F
run_tests evals/postmortem/tests/test_postmortem_harness.py > $O/red.txt; echo "RED: $(grep Summary $O/red.txt)"; grep -E "^E  " $O/red.txt | sort -u
git checkout HEAD -- $F
# GREEN x3 + adjacent
for i in 1 2 3; do run_tests evals/postmortem/tests/test_postmortem_harness.py tests/agent/test_turn_usage_log_line.py > $O/green$i.txt; echo "GREEN$i: $(grep Summary $O/green$i.txt)"; done
# NEG per hunk (logcalls)
cp $F $O/logcalls.head.py
for m in N1_require_cache N2_no_unavailable N3_no_field_counts N4_cache_state_unread N5_ratio_over_all N6_plateau_unfiltered; do
  /usr/bin/python3 $S/pmlc/mutate.py $O/logcalls.head.py $F $m
  run_tests evals/postmortem/tests/test_postmortem_harness.py > $O/neg_$m.txt
  echo "NEG $m: $(grep Summary $O/neg_$m.txt) :: $(grep -E '^E  ' $O/neg_$m.txt | sort -u | head -2 | tr '\n' '|')"
done
git checkout HEAD -- $F
# NEG for probe hunks: base regex vs patched regex on real producer lines
mkdir -p $O/base_probes; for p in cache_prefix_live.py cache_prefix_wire.py; do git show main:evals/postmortem/live_ab/$p > $O/base_probes/$p; done
/usr/bin/python3 $S/pmlc/sibling_regex.py $O/base_probes $W $S/pmlc/rt_main.json $S/pmlc/rt_a1_pr121135.json $S/pmlc/rt_a2_pr119713.json > $O/sibling.json
/usr/bin/python3 -m py_compile evals/postmortem/live_ab/cache_prefix_live.py evals/postmortem/live_ab/cache_prefix_wire.py && echo "probes compile: ok"
ruff check evals/postmortem/forensics/logcalls.py evals/postmortem/live_ab/cache_prefix_live.py evals/postmortem/live_ab/cache_prefix_wire.py evals/postmortem/tests/test_postmortem_harness.py > $O/ruff.txt 2>&1; echo "ruff: $(tail -1 $O/ruff.txt)"
git status --short
