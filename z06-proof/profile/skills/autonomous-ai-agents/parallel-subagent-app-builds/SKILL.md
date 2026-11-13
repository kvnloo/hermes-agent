---
name: parallel-subagent-app-builds
description: "Use when fanning out builders on one app. Seams first."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [delegation, subagents, orchestration, verification]
    related_skills: [session-recovery, rendered-ui-qualification]
---

# Parallel subagent builds on one app

## When to Use
The owner asks for several features at once on one product (web app, phone app, services) and you dispatch 3-10 `delegate_task` builders in parallel.

## Procedure
1. **Cut seams before dispatch** (yourself, small, tested, committed): a plugin API so each builder owns its own files. For a web app: a global `GR`-style client API + module loader (`modules/<name>.js` exporting `init(api)`, placeholders committed so boot tests stay green), and server route plugins (`routes/<name>.py` with `handle(h, method, path)`). Add placeholder slots for every planned module up front; a 404 module import fails the console-error smoke test.
2. **One owner per file.** Each task context names the files it owns, says core files are off-limits unless it is THE core task, and lists the other builders working in parallel. Tell every builder: re-read before editing, targeted patches only, never overwrite from a stale copy, commit only its own paths. If you (the parent) also edit a shared file mid-run, steer the owning child about your hunks.
3. **Self-contained contexts.** Children know nothing: include paths, ports, restart command, auth, test commands, design-system classes, git identity, secret-loading recipe (never print values), and the owner's exact words for the feature. Put long shared context in a file and point to it. `delegate_task` rejects goals containing angle-bracket placeholder markers, so write `ITEMID`/`NAME` instead.
4. **Contract-first for cross-repo work** (backend + Android client): fix the API in the backend task (base URL, auth header, endpoint shapes) and paste the same contract into the client task with instructions to test against a mock; then have the client probe the real service before shipping. Response-shape drift (wrapper objects vs bare arrays) is the usual break.
5. **Every task must end with owner-visible evidence**: tests on a phone-sized real-GPU browser, screenshots inspected with vision, state readback after reload, the exact URL/APK the owner will use fetched for real. Ask for 'what is NOT verified on the physical phone' in the final reply.
6. **Name an integration owner up front.** Feature builders each finish on their own branch/draft PR (or extract code into a separate repo); none of it reaches the owner until one worker merges it into the branch his running services serve. Before reporting any feature as available, find what he actually runs (`systemctl --user show <svc> -p WorkingDirectory` -> `git -C <dir> branch --show-current`) and confirm the feature's commit is an ancestor of it and any extracted package is a real dependency. Otherwise he tests the old build and concludes nothing landed.
7. **On completion, re-verify yourself** before telling the owner: rerun the combined test suites (one background command), restart services, and fix integration seams no single builder owns (e.g. overlapping HUD controls). Rerun a flaky suite once before reporting it as broken.
8. **Model per batch**: `delegation.model` in profile config decides the child model. To run a cheap batch (e.g. Luna for audits), edit config, dispatch, confirm via `delegate_task(action='list')`, restore immediately.
9. **Visibility and mid-run corrections.** The owner watches work in the subagent panel, and plain terminal background jobs never appear there. Run multi-hour or multi-step workstreams through `delegate_task`, and keep background shell jobs for short scripts. Write the shared brief once (`/workspace/zer0/coordination/<project>-<wave>/BRIEF.md`: repo, worktree naming, rules, the baseline failures already present on main, the full task list) and point every child at it. When the owner corrects a premise mid-run (e.g. "X is already installed"), verify it, write the evidence to a file beside the brief, and `steer` every affected child instead of re-dispatching. Tell children to compare each failing gate against an origin/main control before attributing it.
   - Before saying a runtime (ComfyUI, 3D generators, Unsloth, local models) is missing, look for an existing install: venvs under the data drive, `models/` trees, Ollama, GGUF folders, and a probe of each venv's torch/CUDA. A service that isn't running is not a missing install. Write what you find into a `LOCAL-STACK.md` beside the brief, so children reuse installs instead of mocking or reinstalling.
   - "Parallelize across the tailnet with k3s": the agents themselves run on the parent host. The cluster takes only the offloadable jobs (static scans, stdlib-Python tasks, queued GPU Jobs). Say this when dispatching, and ask children to report which node each offloaded job ran on.
10. **Killed batches**: if the parent exits, children die with unknown status. Re-dispatch with pointers to their original goal and `cache/delegation/live/<deleg>/task-<n>.log` (read its tail), and tell them to inspect on-disk state (git status, `git worktree list`, services) first. Check for any review or comment it already posted before letting it post again. The same applies to a single child reported `interrupted`. `async_delegations.task_json` keeps goals but not per-task context.

## Pitfalls
- All subagents and the parent share one saved terminal shell state, so an `export HOME=/XDG_*/TERN_*/ADB_SERVER_SOCKET=...` in any task leaks into every other worker's commands (configs written into a lab dir, adb talking to the wrong phone). Put in every brief: set such variables per command only. After a batch, check `env | rg 'scratch|ADB_SERVER_SOCKET'` in your own shell and unset leftovers.
- The shared shell also persists its cwd: deleting the directory you (or a child) last `cd`'d into makes every later terminal command fail before running (`cd: ... No such file or directory`). Clean up scratch dirs only after `cd` out, or pass the terminal `workdir` explicitly.
- Builders sometimes shell out to `codex exec` or leave side worktrees under `cache/scratch/`; forbid `codex exec` in the brief (owner prefers Hermes subagents) and check `git worktree list` before declaring done.
- A 'done' report verified headless is not done for this owner: links must open on his phone, actions must visibly change the scene. Rerun the journey on the owner surface before relaying success.
- History audits: use the `ctx` CLI (`nice -n 19 ionice -c3 timeout 90 ctx search ... --provider P --since 60d`), one query at a time, appending JSONL records as you go; the ctx MCP tools time out at 120 s and trip the unreachable breaker.
- Some filenames are write-protected for agents (e.g. `claude.md`); name shard outputs `<shard>_shard.md`.
- Pushing a pairing/secret link to the phone: use ADB (`adb shell am start -a android.intent.action.VIEW -d LINK -p PKG`) while the phone is unlocked on the home screen, then `uiautomator dump` to confirm; never paste tokens into chat. With another app in front, the confirm screen opens behind it and times out.
