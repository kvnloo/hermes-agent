#!/usr/bin/env bash
# Round-4 fix: rebuild every arm's tools/fuzzy_match.py (and the carrier tests
# for both+fold) on the rebased head's main, from the published diffs / PR heads.
# Never uses git stash. Restores the worktree to HEAD after each arm.
set -euo pipefail
S=${S:?}; WT=${WT:?}
P=$S/st-edit-fuzzy; O=$P/overlay-v4
D=${D:?set D to the staging dir}
C54575=$D/c54575-rebased-on-main.diff; FOLD=$D/foldin-125376-stripped-guard.diff
cd "$WT"
clean() { git checkout -q HEAD -- tools tests; git reset -q; test -z "$(git status --porcelain)"; }
leaf() { git diff 5f3f5896a4^ 5f3f5896a4 | git apply; }
take() { mkdir -p "$O/$1/tools"; cp tools/fuzzy_match.py "$O/$1/tools/fuzzy_match.py"; }
rm -rf "$O"; clean
git apply --check "$C54575"; git apply "$C54575"; take c54575; clean
leaf; take c125376-leaf; clean
git apply "$C54575"; leaf; take both; clean
leaf; git apply "$FOLD"; take leaf+fold; clean
git apply "$C54575"; leaf; git apply "$FOLD"; take both+fold
mkdir -p "$O/both+fold/tests/tools"; cp tests/tools/test_fuzzy_match.py tests/tools/test_file_tools_live.py "$O/both+fold/tests/tools/"
git diff --numstat > "$O/both+fold.numstat"; clean
T=$(git merge-tree --write-tree HEAD 6d4fbff950); git cat-file -p "$T:tools/fuzzy_match.py" > tools/fuzzy_match.py; take c126502
leaf; git apply "$FOLD"; take c126502+leaf+fold; clean
echo "c126502 merge tree: $T"
sha256sum "$O"/*/tools/fuzzy_match.py "$O"/both+fold/tests/tools/* | sed "s#$O/##"
cat "$O/both+fold.numstat"
