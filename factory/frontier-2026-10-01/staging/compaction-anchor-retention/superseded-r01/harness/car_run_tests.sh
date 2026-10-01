#!/usr/bin/env bash
# usage: car_run_tests.sh <outfile> <files...>   (run from worktree root)
set -u
S=$S
TH=$S/testhome-st-compaction-anchor-retention
mkdir -p "$TH/.hermes"
out=$1; shift
for f in "$@"; do [ -e "$f" ] || { echo "missing $f"; exit 3; }; done
HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=$VENV/bin/python timeout 1200 bash scripts/run_tests.sh -j 2 "$@" -q > "$out.full" 2>&1
rc=$?
grep -E "Summary:|^FAILED|tests failed\)|^ERROR" "$out.full" | head -40 > "$out"
echo "rc=$rc" >> "$out"
cat "$out"
