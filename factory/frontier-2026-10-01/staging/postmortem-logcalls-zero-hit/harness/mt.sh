#!/bin/bash
# Published copy: local paths come from the environment (S = scratch dir holding h.git, W = staging worktree).
# The as-run copy had them inline; its sha256 is the one cited in the receipts' inputs.scripts.
S=${S:?set S to the scratch dir holding h.git}
g() { git -C $S/h.git "$@"; }
C=${C:-$(git -C "${W:?set W to the staging worktree}" rev-parse HEAD)}
echo "main=$(g rev-parse main)"
mt() { local out; if out=$(g merge-tree --write-tree --name-only "$1" "$2" 2>&1); then echo "$3: CLEAN tree=$(echo "$out" | head -1)"; else echo "$3: CONFLICT"; echo "$out" | sed 1d | head -8 | sed 's/^/    /'; fi; }
mt main refs/pr/121135 "main x #121135"
mt main refs/pr/119713 "main x #119713"
mt main $C "main x mine"
mt refs/pr/121135 $C "#121135 x mine"
mt refs/pr/119713 $C "#119713 x mine"
mt refs/pr/121135 refs/pr/119713 "#121135 x #119713"
