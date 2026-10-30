#!/bin/bash
# Runs the unchanged #654 probes via #659's run_fixed_substrate.py on several exact SHAs.
set -u
L=${LAB:?set LAB to a scratch lab dir containing repo/, wt-study/ and probes/}
export PATH=$HOME/.local/bin:$PATH TMPDIR=$L/tmp
unset OPENAI_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY NOUS_API_KEY
R=$L/repo; S=$L/wt-study/studies/rfc-143379/checkout
mkdir -p $L/out
for sha in f90969aef6a62ae475370fe43cc9a0c6d11d3122 af16e3ab16eed2492552c325ad1777533a8b7004 ffc651bd11982eb5b4e1412f1b4b4c34d91cd42d; do
  m=$L/out/manifest-$sha.txt
  git -C $R ls-tree -r --name-only $sha tests/tools | grep -E '^tests/tools/test_memory[^/]*\.py$' > $m
  echo "### $sha files=$(wc -l < $m) start=$(date -u +%FT%TZ)"
  python3 $S/run_fixed_substrate.py $R $sha $L/out/$sha --suite-manifest $m > $L/out/$sha.stdout 2>&1
  echo "exit=$? end=$(date -u +%FT%TZ)"; tail -2 $L/out/$sha.stdout
done
echo MATRIX_DONE
