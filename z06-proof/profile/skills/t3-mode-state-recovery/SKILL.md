---
name: t3-mode-state-recovery
description: "Use when T3 permissions and Plan mode appear inconsistent."
---

# T3 interaction-mode recovery

Distinguish runtime permissions from interaction mode. `runtimeMode: full-access` allows commands without prompts; `interactionMode: plan` separately limits work to read-only investigation. A screenshot of Full access does not show the interaction mode.

Read `t3_thread_configuration` once when the injected instruction and the user's UI appear inconsistent. Acknowledge the setting the screenshot actually shows, explain the distinction once, then investigate the supported mode control in that same turn. Do not repeatedly recheck and return the same blocker after successive approvals, or tell the user the mismatch must be resolved without supplying the verified recovery action. Treat repeated “go ahead” messages as authorization already given, not a reason to request it again.

Find the actual mode control in the relevant client's source before giving directions. In the inspected T3 mobile implementation, `apps/mobile/src/features/threads/ThreadComposer.tsx` exposes `/default` as “Switch to default mode”; selecting the suggestion invokes `onUpdateInteractionMode("default")`. `/plan off` is not that control. Reverify this behavior if the client changes. Do not invent an “Implementation” label.

`t3_thread_configure` changes provider/model selection, not permission modes; do not pass guessed interaction-mode fields. Respect Plan restrictions until a new interaction-mode instruction arrives. Continue useful read-only discovery rather than treating the restriction as a reason to stall all work.

Once T3 injects Default mode, resume the already-authorized task without requesting another approval. For isolated work in the same thread, `t3_worktree_handoff` can create and bind a worktree and queue `continuationPrompt`. Call it last in the turn because it detaches the provider session. Report the queued continuation as queued, not as executed implementation or verified installation. At the continuation's first tool step, verify the actual terminal cwd and Git branch against the returned worktree path; a successful app handoff does not prove every tool backend changed directories. Use an explicit workdir and absolute file paths if they disagree, so subsequent edits cannot land in root main.

A T3 server restart cancels a queued handoff continuation, and T3 then reports it as cancelled background work. Do not call `t3_worktree_handoff` again, because the worktree and branch already exist. Read the worktree's `git status` and the task's artifact directory to see what was finished, then resume from there in the current turn.
