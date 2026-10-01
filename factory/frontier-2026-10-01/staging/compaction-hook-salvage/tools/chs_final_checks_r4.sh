#!/usr/bin/env bash
# Round-2 closing checks for staging/compaction-hook-salvage (read-only against GitHub; local refs only).
# usage: chs_final_checks_r4.sh <h.git> <worktree>
set -uo pipefail
H=$1; W=$2
ST=$(cd "$(dirname "$0")/.." && pwd)
NEW=111f361fb0003405e4724b4c6523f6ce5d118c22
BASE=a3b56cac95488242856b6fb1f121842a38c3e391
R=refs/xf/arms/compaction-hook-salvage
echo "checked_at $(date -u +%FT%TZ)"
git -C "$H" -c credential.helper= fetch -q --filter=blob:none https://github.com/NousResearch/hermes-agent.git "+refs/heads/main:refs/heads/main"
MAIN=$(git -C "$H" rev-parse main)
echo "main $MAIN $(git -C "$H" log -1 --format=%cI main)"
echo "commits_since_base $(git -C "$H" rev-list --count "$BASE..main")"
echo "invalidate_on_changed [$(git -C "$H" diff --name-only "$BASE" main -- agent/conversation_compression.py agent/context_compressor.py hermes_cli/plugins.py hermes_cli/plugins_dispatch.py hermes_cli/lifecycle.py agent/conversation_compression_manual.py hermes_state_messages.py hermes_state_compression.py hermes_cli/hooks.py website/docs/user-guide/features/hooks.md agent/agent_init.py | tr '\n' ' ')]"
echo "merge_tree_main $(git -C "$H" merge-tree --write-tree main staging/compaction-hook-salvage 2>&1 | head -1) rc=$?"
echo "staging_tree $(git -C "$H" rev-parse "$NEW^{tree}")"
echo "branch $(git -C "$H" rev-parse staging/compaction-hook-salvage)"
# body.md's inline diff applies on top of the staging commit and reproduces c53806-foldin-r4
cd "$W"
git checkout -q -f --detach "$NEW" && test -z "$(git status --porcelain)" || echo "checkout failed"
python3 - "$ST/body.md" > "$ST/raw/body-inline.diff" <<'EOF'
import sys
t = open(sys.argv[1]).read()
print(t.split("```diff\n", 1)[1].split("\n```", 1)[0])
EOF
cmp <(sed -e '$a\' "$ST/raw/body-inline.diff") <(sed -e '$a\' "$ST/patches/arm-c53806-foldin.patch") && echo "body diff == patches/arm-c53806-foldin.patch"
git apply --check "$ST/raw/body-inline.diff" && git apply "$ST/raw/body-inline.diff" && echo "body diff applies on $NEW"
echo "diff vs c53806-foldin-r4: [$(git diff --stat "$R/c53806-foldin-r4" | tail -1)]"
git checkout -q -f --detach "$NEW"; test -z "$(git status --porcelain)" && echo "worktree clean"
# staging patch applies to main with git am semantics (3-way not needed)
git checkout -q -f --detach "$BASE" && git apply --check "$ST/patches/staging-compaction-hook-salvage.patch" && echo "staging patch applies on $BASE"
git checkout -q -f --detach "$NEW"
echo "fork_refs [$(git ls-remote https://github.com/kvnloo/hermes-agent.git 'refs/heads/staged/*' 'refs/heads/staging' | tr '\n' ' ')] at $(date -u +%FT%TZ)"
for p in 53806 93391 118847 125881 119347; do
  echo "pr $p $(gh pr view $p -R NousResearch/hermes-agent --json state,headRefOid --jq '"\(.state) \(.headRefOid[0:10])"')"
done
echo "new_hook_prs_today [$(gh search prs --repo NousResearch/hermes-agent 'compaction hook' --created '>=2026-10-01' --json number --jq '.[].number' | tr '\n' ' ')|$(gh search prs --repo NousResearch/hermes-agent 'compression hook' --created '>=2026-10-01' --json number --jq '.[].number' | tr '\n' ' ')]"
echo "issue_118382_last $(gh issue view 118382 -R NousResearch/hermes-agent --json comments --jq '.comments[-1] | "\(.createdAt) \(.author.login)"')"
echo "issue_130139 $(gh issue view 130139 -R NousResearch/hermes-agent --json state,comments --jq '"\(.state) comments=\(.comments|length)"')"
echo "kvnloo_issues_24h [$(gh search issues --repo NousResearch/hermes-agent --author kvnloo --created '>=2026-09-30T13:00:00Z' --json number --jq '.[].number' | tr '\n' ' ')]"
echo "kvnloo_prs_today [$(gh search prs --repo NousResearch/hermes-agent --author kvnloo --created '>=2026-10-01' --json number --jq '.[].number' | tr '\n' ' ')]"
echo "done $(date -u +%FT%TZ)"
