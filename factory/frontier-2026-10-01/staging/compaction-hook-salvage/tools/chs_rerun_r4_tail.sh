#!/usr/bin/env bash
# Re-run the two r4 steps that /tmp running out of space (13:20:44Z) broke: the last OWN cell
# (c53806-foldin-own-adapted: the guard log write failed with ENOSPC) and the guard canary (the worktree
# checkout to the staging commit failed). Waits for >= 5 MB free (the shared tmpfs stayed at ~8 MB free; the git index is ~2 MB) on the test HOME's filesystem first.
# usage: chs_rerun_r4_tail.sh <worktree> <testhome> <python>
set -uo pipefail
W=$1; TH=$2; PY=$3
ST=$(cd "$(dirname "$0")/.." && pwd)
R=refs/xf/arms/compaction-hook-salvage
LOG=$ST/raw/rerun-r4-tail.stdout
exec >> "$LOG" 2>&1
echo "== wait for space $(date -u +%FT%TZ)"
until [ "$(df -Pk "$TH" | awk 'NR==2 {print $4}')" -ge 5120 ]; do sleep 10; done
echo "== space ok $(date -u +%FT%TZ): $(df -Pk "$TH" | awk 'NR==2 {print $4}') KB free"
cd "$W"
git checkout -q -f --detach "$R/c53806-foldin-r4" && test -z "$(git status --porcelain)" || { echo "worktree reset failed"; exit 1; }
OUT=$ST/raw/own-r4
mkdir -p "$OUT/enospc-1"
mv "$OUT/c53806-foldin-own-adapted.log" "$OUT/c53806-foldin-own-adapted.egress.log" "$OUT/c53806-foldin-own-adapted.egress.stacks" "$OUT/enospc-1/" 2>/dev/null
grep -v '^c53806-foldin-own-adapted ' "$OUT/cells.txt" > "$OUT/cells.txt.new" && mv "$OUT/cells.txt.new" "$OUT/cells.txt"
P=tests/agent/test_zz_chs_c53806_own.py
touch "$TH/chs-egress.stacks-on"
cp "$ST/tools/chs_c53806_own_tests_adapted.py" "$P"
rm -f "$TH/chs-egress.log" "$TH/chs-egress.stacks"
HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 "$P" -q > "$OUT/c53806-foldin-own-adapted.log" 2>&1 || true
touch "$TH/chs-egress.log" "$TH/chs-egress.stacks"
mv "$TH/chs-egress.log" "$OUT/c53806-foldin-own-adapted.egress.log"; mv "$TH/chs-egress.stacks" "$OUT/c53806-foldin-own-adapted.egress.stacks"
rm -f "$P"
echo "c53806-foldin-own-adapted $(git rev-parse HEAD) $P chs_c53806_own_tests_adapted.py" >> "$OUT/cells.txt"
echo "own cell: $(grep -m1 '=== Summary' "$OUT/c53806-foldin-own-adapted.log")"
echo "== canary r4 $(date -u +%FT%TZ)"
rm -f "$TH/chs-egress.stacks-on" "$TH/chs-egress.log" "$TH/chs-egress.stacks"
mkdir -p "$ST/raw/guard-canary-r4-enospc-1"
mv "$ST/raw/guard-canary-r4.log" "$ST/raw/guard-canary-r4.egress.log" "$ST/raw/guard-canary-r4-enospc-1/" 2>/dev/null
git checkout -q --detach 111f361fb0003405e4724b4c6523f6ce5d118c22 && test -z "$(git status --porcelain)" || { echo "checkout failed"; exit 1; }
cp "$ST/tools/chs_guard_canary_r4.py" tests/agent/test_zz_chs_guard_canary.py
HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 tests/agent/test_zz_chs_guard_canary.py -q > "$ST/raw/guard-canary-r4.log" 2>&1
touch "$TH/chs-egress.log"; mv "$TH/chs-egress.log" "$ST/raw/guard-canary-r4.egress.log"
rm -f tests/agent/test_zz_chs_guard_canary.py
echo "canary: $(grep -m1 '=== Summary' "$ST/raw/guard-canary-r4.log") head=$(git rev-parse HEAD) status=[$(git status --porcelain)]"
grep -l "Errno 28\|No space left" "$OUT/c53806-foldin-own-adapted.log" "$ST/raw/guard-canary-r4.log" && echo "ENOSPC AGAIN" || echo "no ENOSPC in rerun logs"
echo "== done $(date -u +%FT%TZ)"
