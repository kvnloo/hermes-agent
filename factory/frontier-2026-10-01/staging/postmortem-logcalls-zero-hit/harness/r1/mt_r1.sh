#!/usr/bin/env bash
# Round-1 freshness re-measure: merge-tree matrix + drift counts against the declared main.
set -u
cd "$1"   # bare repo
M=aea969677c60a1bb72fe227fdfb98f196a2092cc; B=234badf4012af380d23c91eae55d045a69c69ffb
ST=dd4dd10611e8c23c7579a4ddb95655abebbaca27; A=dd4a0ca4cf3345702eb7be95e11873308d3015b5; T=7471d9915d7d1ce3e94f9d18c9d775461d269815
echo "main=$M (fetched 2026-10-01T11:04Z; commit date 2026-10-01T10:56:05Z)"
echo "staging=$ST parent=$(git rev-parse "$ST^")"
echo "#121135 head=$A"; echo "#119713 head=$T"
for pair in "main|$M|staging|$ST" "main|$M|#121135|$A" "main|$M|#119713|$T" "#121135|$A|staging|$ST" "#119713|$T|staging|$ST" "#121135|$A|#119713|$T"; do
  IFS='|' read -r n1 c1 n2 c2 <<< "$pair"
  if out=$(git merge-tree --write-tree --name-only "$c1" "$c2" 2>&1); then echo "$n1 x $n2: CLEAN tree=$out"
  else echo "$n1 x $n2: CONFLICT"; echo "$out" | sed 's/^/    /'; fi
done
P="evals/postmortem agent/turn_usage.py agent/usage_pricing.py hermes_logging.py tests/agent/test_turn_usage_log_line.py"
echo "drift $B..$M: $(git rev-list --count $B..$M) commits"
echo "drift commits touching $P: $(git rev-list --count $B..$M -- $P)"
echo "drift commits touching .github/workflows: $(git rev-list --count $B..$M -- .github/workflows)"
