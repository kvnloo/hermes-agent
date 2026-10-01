#!/usr/bin/env bash
# Round-2 (r4) evidence chain for staging/compaction-hook-salvage: F05 r4 (+ negative/sabotage arms), E12 r4,
# OWN r4, guard canary r4. Strictly sequential: every step shares the one isolated test HOME and its guard log.
# usage: chs_run_all_r4.sh <worktree> <testhome> <python>
set -uo pipefail
W=$1; TH=$2; PY=$3
ST=$(cd "$(dirname "$0")/.." && pwd)
R=refs/xf/arms/compaction-hook-salvage
rm -f "$TH/chs-egress.stacks-on" "$TH/chs-egress.log" "$TH/chs-egress.stacks"
echo "== F05 r4 $(date -u +%FT%TZ)"
python3 "$ST/tools/chs_ab_runner_r4.py" --worktree "$W" --run-id f05-r4 --arms "$(cat "$ST/raw/f05-r4.arms")" --reps 3 --testhome "$TH" --python "$PY"
echo "== F05 r4s $(date -u +%FT%TZ)"
python3 "$ST/tools/chs_ab_runner_r4.py" --worktree "$W" --run-id f05-r4s --arms "$(cat "$ST/raw/f05-r4s.arms")" --reps 3 --testhome "$TH" --python "$PY" --skip-probe
echo "== E12 r4 $(date -u +%FT%TZ)"
bash "$ST/tools/chs_guards_r4.sh" base 111f361fb0003405e4724b4c6523f6ce5d118c22 e12-r4 "$W" "$TH" "$PY"
bash "$ST/tools/chs_guards_r4.sh" c53806-foldin "$R/c53806-foldin-r4" e12-r4 "$W" "$TH" "$PY"
bash "$ST/tools/chs_guards_r4.sh" foldin-bounded "$R/foldin-bounded-r4" e12-r4 "$W" "$TH" "$PY"
echo "== OWN r4 $(date -u +%FT%TZ)"
bash "$ST/tools/chs_own_r4.sh" "$W" "$TH" "$PY"
echo "== canary r4 $(date -u +%FT%TZ)"
rm -f "$TH/chs-egress.stacks-on" "$TH/chs-egress.log" "$TH/chs-egress.stacks"
cd "$W" && git checkout -q --detach 111f361fb0003405e4724b4c6523f6ce5d118c22
cp "$ST/tools/chs_guard_canary_r4.py" tests/agent/test_zz_chs_guard_canary.py
HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 tests/agent/test_zz_chs_guard_canary.py -q > "$ST/raw/guard-canary-r4.log" 2>&1
touch "$TH/chs-egress.log"; mv "$TH/chs-egress.log" "$ST/raw/guard-canary-r4.egress.log"
rm -f tests/agent/test_zz_chs_guard_canary.py
git status --porcelain
echo "== done $(date -u +%FT%TZ)"
