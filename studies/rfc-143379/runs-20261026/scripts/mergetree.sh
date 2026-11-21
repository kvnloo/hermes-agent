#!/bin/bash
cd "$1"
for pair in "pr141876 pr116673" "jf-readfix pr116673" "upstream-main pr141876" "upstream-main jf-readfix" "upstream-main pr116673"; do
  set -- $pair
  out=$(git merge-tree --write-tree --name-only --no-messages "$1" "$2" 2>&1); rc=$?
  echo "## $1($(git rev-parse --short=12 $1)) x $2($(git rev-parse --short=12 $2)) exit=$rc"
  echo "$out" | tail -n +2 | grep -v '^$' | sed 's/^/  conflict: /'
done
