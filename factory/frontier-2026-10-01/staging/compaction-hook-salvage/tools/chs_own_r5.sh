#!/usr/bin/env bash
# OWN r5: each carrier's own tests on its r5 arm (the r4 arm diffs re-applied onto the r5 staging commit, same patch-ids) (fairness), including #53806's own tests ported from its
# compression commit e560abd758 (verbatim, and with two marked drift adaptations), under the r4 egress guard.
# usage: chs_own_r4.sh <worktree> <testhome> <python>
set -euo pipefail
W=$1; TH=$2; PY=$3
ST=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ST/raw/own-r5; mkdir -p "$OUT"; : > "$OUT/cells.txt"
R=refs/xf/arms/compaction-hook-salvage
EG=$TH/chs-egress.log; STK=$TH/chs-egress.stacks
touch "$TH/chs-egress.stacks-on"
cd "$W"
cell() {  # <label> <commitish> <test path> [factory file to copy in]
  local label=$1 ref=$2 path=$3 src=${4:-}
  test -z "$(git status --porcelain)"
  git checkout -q --detach "$ref"
  [ -n "$src" ] && cp "$ST/tools/$src" "$path"
  rm -f "$EG" "$STK"
  HOME="$TH" HERMES_HOME="$TH/.hermes" HERMES_PYTHON="$PY" bash scripts/run_tests.sh -j 2 "$path" -q > "$OUT/$label.log" 2>&1 || true
  touch "$EG" "$STK"; mv "$EG" "$OUT/$label.egress.log"; mv "$STK" "$OUT/$label.egress.stacks"
  [ -n "$src" ] && rm -f "$path"
  echo "$label $(git rev-parse HEAD) $path ${src:-carrier-file}" >> "$OUT/cells.txt"
  echo "$label $(grep -m1 '=== Summary' "$OUT/$label.log" || echo unparsed)"
}
BASE=$(git rev-parse "$R/staging-r5")
cell base-rotation_state "$BASE" tests/agent/test_compression_rotation_state.py
cell c93391-code "$R/c93391-code-r5" tests/agent/test_compression_rotation_state.py
cell c118847-handport "$R/c118847-handport-r5" tests/agent/test_post_compaction_hook.py
cell c125881-merge "$R/c125881-merge-r5" tests/agent/test_context_governance.py
P=tests/agent/test_zz_chs_c53806_own.py
cell base-c53806-own "$BASE" "$P" chs_c53806_own_tests.py
cell c53806-handport-own "$R/c53806-handport-r5" "$P" chs_c53806_own_tests.py
cell foldin-own "$R/foldin-r5" "$P" chs_c53806_own_tests.py
cell base-c53806-own-adapted "$BASE" "$P" chs_c53806_own_tests_adapted.py
cell c53806-handport-own-adapted "$R/c53806-handport-r5" "$P" chs_c53806_own_tests_adapted.py
cell foldin-own-adapted "$R/foldin-r5" "$P" chs_c53806_own_tests_adapted.py
test -z "$(git status --porcelain)"
echo "own-r5 done"
