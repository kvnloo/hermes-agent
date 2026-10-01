#!/usr/bin/env bash
# Round-3 freshness: merge-tree matrix and invalidate_on drift against a new main.
# Usage: bash harness/r3/mt_r3.sh <bare repo> [main sha]
set -u
cd "$1"   # bare repo
M=${2:-34f8ec3b407e50bad3ae27e4cd79d65212061356}
B=234badf4012af380d23c91eae55d045a69c69ffb; D1=aea969677c60a1bb72fe227fdfb98f196a2092cc
ST=dd4dd10611e8c23c7579a4ddb95655abebbaca27; A=dd4a0ca4cf3345702eb7be95e11873308d3015b5; T=7471d9915d7d1ce3e94f9d18c9d775461d269815
PATHS=(evals/postmortem agent/turn_usage.py agent/usage_pricing.py hermes_logging.py tests/agent/test_turn_usage_log_line.py .github/workflows)
echo "main=$M commit_date=$(git log -1 --format=%cI "$M") tree=$(git rev-parse "$M^{tree}")"
echo "staging=$ST parent=$(git rev-parse "$ST^") tree=$(git rev-parse "$ST^{tree}")"
echo "#121135 head=$A"; echo "#119713 head=$T"
echo "base_is_ancestor_of_main=$(git merge-base --is-ancestor "$B" "$M" && echo yes || echo no)"
echo "commits base..main=$(git rev-list --count "$B..$M") previous_declared..main=$(git rev-list --count "$D1..$M")"
for pair in "main|$M|staging|$ST" "main|$M|#121135|$A" "main|$M|#119713|$T" "#121135|$A|staging|$ST" "#119713|$T|staging|$ST" "#121135|$A|#119713|$T"; do
  IFS='|' read -r n1 c1 n2 c2 <<< "$pair"
  if out=$(git merge-tree --write-tree --name-only "$c1" "$c2" 2>&1); then echo "$n1 x $n2: CLEAN tree=$out"
  else echo "$n1 x $n2: CONFLICT"; echo "$out" | sed 's/^/    /'; fi
done
echo "--- invalidate_on paths changed base..main:"
git diff --stat "$B" "$M" -- "${PATHS[@]}"
git log --format='%h %s' "$B..$M" -- "${PATHS[@]}"
echo "--- invalidate_on paths changed previous_declared..main:"
git log --format='%h %s' "$D1..$M" -- "${PATHS[@]}"
echo "--- diff of those paths base..main:"
git diff "$B" "$M" -- "${PATHS[@]}"
echo "--- changed by the staging commit:"
git diff --stat "$B" "$ST"
