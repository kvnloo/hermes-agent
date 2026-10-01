#!/usr/bin/env bash
# (worktree was removed after the run; recreate it first: git -C $S/h.git worktree add --detach $W refs/w2/main)
# usage: queued-paste_ab.sh <label> <state-ref> [extra vitest files...]
#   state refs (pinned in $S/h.git):
#     refs/w2/main                      = upstream main 298a01c79b
#     refs/w2/queued-paste/m99042       = main + #99042 a549960398 (one mechanical conflict, see pr99042-merge-resolution.cc.diff)
#     refs/w2/queued-paste/mfork56      = main + ready/fork-56-queued-paste-payload e8d70c6409 (clean merge)
#     refs/w2/queued-paste/mcompose     = main + #99042 + fork-56 (see compose-*.diff)
# Runs the regression test + the probe file, then `npm run typecheck`, and logs to $E/ab-<label>.log.
set -u
S=/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad
W=/mnt/zer0models/project-artifacts/hermes-agent/promotion-readiness-2026-10-01/wt/W2/paste
E=/mnt/zer0models/project-artifacts/hermes-agent/salvage-wave-2026-10-01/evidence/W2/queued-paste
label=$1; ref=$2; shift 2
cd "$W" || exit 2
git reset -q --hard "$ref" && git clean -qfdx -e node_modules -e ui-tui/node_modules
ln -sfn /workspace/hermes-home/hermes-agent/node_modules node_modules
ln -sfn /workspace/hermes-home/hermes-agent/ui-tui/node_modules ui-tui/node_modules
cp "$E/queuedPasteSubmission.test.tsx" ui-tui/src/__tests__/queuedPasteSubmission.test.tsx
cp "$E/queuedPasteProbe.test.tsx" ui-tui/src/__tests__/queuedPasteProbe.test.tsx
{
  echo "state=$label ref=$ref head=$(git rev-parse HEAD)"
  cd ui-tui
  PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$S/testhome-W2-queued-paste \
    timeout 600 npx vitest run src/__tests__/queuedPasteSubmission.test.tsx src/__tests__/queuedPasteProbe.test.tsx "$@" 2>&1
  echo "=== typecheck"
  PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$S/testhome-W2-queued-paste timeout 600 npm run -s typecheck 2>&1 | tail -n 30
  echo "typecheck rc=${PIPESTATUS[0]}"
} > "$E/ab-$label.log" 2>&1
grep -E '^ +(✓|×)|Tests |typecheck rc|error TS' "$E/ab-$label.log"
