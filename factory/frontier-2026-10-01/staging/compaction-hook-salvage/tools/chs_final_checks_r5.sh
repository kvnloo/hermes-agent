#!/usr/bin/env bash
# Round-3 closing checks for staging/compaction-hook-salvage (read-only against GitHub; local refs only).
# usage: chs_final_checks_r5.sh <h.git> <worktree>
set -uo pipefail
H=$1; W=$2
ST=$(cd "$(dirname "$0")/.." && pwd)
NEW=1ab964166a125b64ea4d5c05e7f5813bffd7bb2d
BASE=44a1ce9724502b9c692faaef00af3054bf11f1a6
R=refs/xf/arms/compaction-hook-salvage
INV="agent/conversation_compression.py agent/context_compressor.py hermes_cli/plugins.py hermes_cli/plugins_dispatch.py hermes_cli/lifecycle.py agent/conversation_compression_manual.py hermes_state_messages.py hermes_state_compression.py hermes_cli/hooks.py website/docs/user-guide/features/hooks.md agent/agent_init.py agent/compression_facade.py"
echo "checked_at $(date -u +%FT%TZ)"
git -C "$H" -c credential.helper= fetch -q --filter=blob:none https://github.com/NousResearch/hermes-agent.git "+refs/heads/main:refs/heads/main" "+refs/pull/127058/head:refs/xf/pr/127058"
MAIN=$(git -C "$H" rev-parse main)
echo "main $MAIN $(git -C "$H" log -1 --format=%cI main)"
echo "commits_since_base $(git -C "$H" rev-list --count "$BASE..main")"
# shellcheck disable=SC2086
echo "invalidate_on_changed [$(git -C "$H" diff --name-only "$BASE" main -- $INV | tr '\n' ' ')]"
echo "merge_tree_main $(git -C "$H" merge-tree --write-tree main staging/compaction-hook-salvage 2>&1 | head -1) rc=$?"
echo "staging_tree $(git -C "$H" rev-parse "$NEW^{tree}")"
echo "branch $(git -C "$H" rev-parse staging/compaction-hook-salvage)"
echo "pr127058_head $(git -C "$H" rev-parse refs/xf/pr/127058)"
echo "foldin_vs_127058 $(git -C "$H" merge-tree --write-tree --name-only "$R/foldin-r5" refs/xf/pr/127058 2>&1 | tr '\n' ' ')"
echo "foldin_on_main $(git -C "$H" merge-tree --write-tree --name-only main "$R/foldin-r5" 2>&1 | head -1)"
# body.md's inline diff applies on top of the staging commit and reproduces foldin-r5
cd "$W"
git checkout -q -f --detach "$NEW" && test -z "$(git status --porcelain)" || echo "checkout failed"
python3 - "$ST/body.md" > "$ST/raw/body-inline-r5.diff" <<'EOF'
import sys
t = open(sys.argv[1]).read()
print(t.split("```diff\n", 1)[1].split("\n```", 1)[0])
EOF
cmp <(sed -e '$a\' "$ST/raw/body-inline-r5.diff") <(sed -e '$a\' "$ST/patches/arm-foldin.patch") && echo "body diff == patches/arm-foldin.patch"
git apply --check "$ST/raw/body-inline-r5.diff" && git apply "$ST/raw/body-inline-r5.diff" && echo "body diff applies on $NEW"
git add -A -N . && echo "diff vs foldin-r5: [$(git diff --stat "$R/foldin-r5" | tail -1)]"
git reset -q; git checkout -q -f --detach "$NEW"; git clean -q -fd -- agent; test -z "$(git status --porcelain)" && echo "worktree clean"
git checkout -q -f --detach "$BASE" && git apply --check "$ST/patches/staging-compaction-hook-salvage.patch" && echo "staging patch applies on $BASE"
git checkout -q -f --detach "$NEW"
echo "fork_refs [$(git ls-remote https://github.com/kvnloo/hermes-agent.git 'refs/heads/staged/*' 'refs/heads/staging' | tr '\n' ' ')] at $(date -u +%FT%TZ)"
echo "done $(date -u +%FT%TZ)"
