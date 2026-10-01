#!/usr/bin/env bash
# (worktree was removed after the run; recreate it first: git -C $S/h.git worktree add --detach $W refs/w2/main)
# usage: adjacent.sh <label> <state-ref>  -> $E/adjacent-<label>.log
# Adjacent ui-tui files: every test importing useSubmission/useQueue/useInputHandlers/
# domain/attachments/useComposerState/useMainApp/submissionCore, plus the fork-56 verdict's set.
set -u
S=/tmp/claude-1000/-home-kvn-zer0/0c40e097-3138-4d4c-a137-74e0e9bc7d3d/scratchpad
W=/mnt/zer0models/project-artifacts/hermes-agent/promotion-readiness-2026-10-01/wt/W2/paste
E=/mnt/zer0models/project-artifacts/hermes-agent/salvage-wave-2026-10-01/evidence/W2/queued-paste
label=$1; ref=$2
FILES="src/__tests__/attachments.test.ts src/__tests__/gatewayClientKillLatch.test.ts src/__tests__/inputSelectionClipboard.test.ts src/__tests__/libTextI18n.test.ts src/__tests__/orchestratorPromptSession.test.ts src/__tests__/platform.test.ts src/__tests__/queueScopeRenderer.test.tsx src/__tests__/queueSubmission.test.ts src/__tests__/submissionCore.test.ts src/__tests__/useComposerState.test.ts src/__tests__/useInputHandlers.test.ts src/__tests__/useQueue.test.ts src/__tests__/useSubmission.test.ts src/__tests__/createGatewayEventHandler.test.ts src/__tests__/voiceSubmitModeRenderer.test.tsx src/__tests__/startupLatency.test.ts src/__tests__/startupLatencyDashboard.test.ts src/__tests__/moaProgressActivity.test.ts src/__tests__/composerHighlights.test.ts"
cd "$W" || exit 2
git reset -q --hard "$ref" && git clean -qfdx -e node_modules -e ui-tui/node_modules
ln -sfn /workspace/hermes-home/hermes-agent/node_modules node_modules
ln -sfn /workspace/hermes-home/hermes-agent/ui-tui/node_modules ui-tui/node_modules
cd ui-tui
{
  echo "state=$label ref=$ref head=$(git rev-parse HEAD)"
  PATH=$S/w2-tripwire/bin:/usr/bin:/bin HOME=$S/testhome-W2-queued-paste timeout 900 npx vitest run $FILES 2>&1
} > "$E/adjacent-$label.log" 2>&1
grep -E '^ +(×)|^ FAIL|Test Files |Tests ' "$E/adjacent-$label.log" | sort -u | head -40
