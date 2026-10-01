#!/usr/bin/env bash
# MRG r5: does the fold-in compose with NousResearch/hermes-agent#127058 (memory on_session_switch delivered after
# the commit fence is released, for #118120)? Runs, under the r4 egress guard and an isolated HOME:
#   x127058-*   on foldin-x127058-r5 (fold-in merged with #127058 head f306319fe7; the one conflict resolved by
#               keeping both post-fence deliveries): the contract test, #127058's own test, and its 4 named neighbours;
#   s5x127058-* on the r5 staging commit merged with #127058 (merge-tree clean): the same files, as the baseline.
# usage: chs_merge127058_r5.sh <worktree> <testhome> <python>
set -euo pipefail
W=$1; TH=$2; PY=$3
ST=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ST/raw/mrg-r5; mkdir -p "$OUT"; : > "$OUT/cells.txt"
R=refs/xf/arms/compaction-hook-salvage
EG=$TH/chs-egress.log; STK=$TH/chs-egress.stacks
touch "$TH/chs-egress.stacks-on"
cd "$W"
test -z "$(git status --porcelain)"
if ! git rev-parse -q --verify "$R/s5x127058-r5" >/dev/null; then
  git checkout -q --detach "$R/staging-r5"
  git -c user.name="Kevin Rajan" -c user.email="7121943+kvnloo@users.noreply.github.com" merge -q --no-ff --no-edit \
    -m "arm s5x127058-r5 (factory-only: r5 staging commit merged with #127058 head f306319fe7)" refs/xf/pr/127058
  git update-ref "$R/s5x127058-r5" HEAD
fi
cell() {  # <label> <commitish> <test paths...>
  local label=$1 ref=$2; shift 2
  test -z "$(git status --porcelain)"
  git checkout -q --detach "$ref"
  rm -f "$EG" "$STK"
  HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 "$@" -q > "$OUT/$label.log" 2>&1 || true
  touch "$EG" "$STK"; mv "$EG" "$OUT/$label.egress.log"; mv "$STK" "$OUT/$label.egress.stacks"
  echo "$label $(git rev-parse HEAD) $*" >> "$OUT/cells.txt"
  echo "$label $(grep -m1 '=== Summary' "$OUT/$label.log" || echo unparsed)"
}
C=tests/agent/test_compaction_observer_hook_contract.py
F=tests/agent/test_compression_fence_memory_hook_118120.py
N="tests/agent/test_memory_session_switch.py tests/agent/test_memory_boundary_commit.py tests/agent/test_compression_rotation_state.py tests/agent/test_compression_concurrent_fork.py"
for arm in x127058:foldin-x127058-r5 s5x127058:s5x127058-r5; do
  label=${arm%%:*}; ref=$R/${arm#*:}
  cell "$label-contract" "$ref" "$C"
  cell "$label-118120" "$ref" "$F"
  # shellcheck disable=SC2086
  cell "$label-neighbours" "$ref" $N
done
test -z "$(git status --porcelain)"
echo "mrg-r5 done"
