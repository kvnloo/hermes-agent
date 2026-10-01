#!/usr/bin/env bash
# Round-3 (r5) evidence chain for staging/compaction-hook-salvage: F05 r5 (+ negative/sabotage arms), E12 r5, OWN r5,
# MRG r5 (composition with #127058). Strictly sequential: one isolated test HOME, one guard log (r4 guard, unchanged).
# usage: chs_run_all_r5.sh <worktree> <testhome> <python>
set -uo pipefail
W=$1; TH=$2; PY=$3
ST=$(cd "$(dirname "$0")/.." && pwd)
R=refs/xf/arms/compaction-hook-salvage
rm -f "$TH/chs-egress.stacks-on" "$TH/chs-egress.log" "$TH/chs-egress.stacks"
echo "== F05 r5 $(date -u +%FT%TZ)"
python3 "$ST/tools/chs_ab_runner_r5.py" --worktree "$W" --run-id f05-r5 --arms "$(cat "$ST/raw/f05-r5.arms")" --reps 3 --testhome "$TH" --python "$PY"
echo "== F05 r5s $(date -u +%FT%TZ)"
rm -f "$TH/chs-egress.stacks-on"
python3 "$ST/tools/chs_ab_runner_r5.py" --worktree "$W" --run-id f05-r5s --arms "$(cat "$ST/raw/f05-r5s.arms")" --reps 3 --testhome "$TH" --python "$PY" --skip-probe
echo "== E12 r5 $(date -u +%FT%TZ)"
bash "$ST/tools/chs_guards_r5.sh" base "$R/staging-r5" e12-r5 "$W" "$TH" "$PY"
bash "$ST/tools/chs_guards_r5.sh" foldin "$R/foldin-r5" e12-r5 "$W" "$TH" "$PY"
bash "$ST/tools/chs_guards_r5.sh" foldin-x127058 "$R/foldin-x127058-r5" e12-r5 "$W" "$TH" "$PY"
echo "== OWN r5 $(date -u +%FT%TZ)"
bash "$ST/tools/chs_own_r5.sh" "$W" "$TH" "$PY"
echo "== MRG r5 $(date -u +%FT%TZ)"
bash "$ST/tools/chs_merge127058_r5.sh" "$W" "$TH" "$PY"
rm -f "$TH/chs-egress.stacks-on"
echo "== done $(date -u +%FT%TZ)"
