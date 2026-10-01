#!/bin/bash
S=$S
g() { git -C $S/h.git "$@"; }
C=${C:-$(git -C $ARTIFACTS/promotion-readiness-2026-10-01/wt/staging/postmortem-logcalls-zero-hit rev-parse HEAD)}
echo "main=$(g rev-parse main)"
mt() { local out; if out=$(g merge-tree --write-tree --name-only "$1" "$2" 2>&1); then echo "$3: CLEAN tree=$(echo "$out" | head -1)"; else echo "$3: CONFLICT"; echo "$out" | sed 1d | head -8 | sed 's/^/    /'; fi; }
mt main refs/pr/121135 "main x #121135"
mt main refs/pr/119713 "main x #119713"
mt main $C "main x mine"
mt refs/pr/121135 $C "#121135 x mine"
mt refs/pr/119713 $C "#119713 x mine"
mt refs/pr/121135 refs/pr/119713 "#121135 x #119713"
