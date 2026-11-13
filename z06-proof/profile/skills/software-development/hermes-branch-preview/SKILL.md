---
name: hermes-branch-preview
description: Use when running Hermes branches for review in Tern panes.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, tern, worktree, preview, ui-tsp, qa]
    related_skills: [terminal-agent-orchestration, hermes-openui-tern-evidence]
---

# Hermes branch preview and qualification

## When to Use

Use when the user wants to see or test a Hermes fork branch (especially the Tern `ui-tsp` frontend) running next to the conversation, or when qualifying a PR branch before merging it into a preview/integration branch. Flow the user wants: feature branch -> integration/preview branch, each branch runnable in its own pane and tested separately.

## Procedure

1. **Worktree per branch.** `git fetch origin +refs/heads/B:refs/remotes/origin/B` (explicit refspec: a shared bare clone may not have that remote-tracking ref), then `git worktree add --detach <root>/qa-<slug> origin/B` (or `-b` a local QA branch). Never check out a branch inside a worktree that a live pane is using.
2. **Dependencies.** Borrow `node_modules` from a built worktree by linking per entry, and re-point `@hermes/*` workspace links at THIS worktree's own sources. A whole-directory symlink resolves `@hermes/shared` to the donor's `apps/shared`, giving false "has no exported member" typecheck errors for types the branch added. Keep a reusable script for this beside the preview homes.
3. **Gates, in order:** in `ui-tsp/`: `npm run typecheck`, `npx vitest run`, `npx eslint src/`. Gateway changes add `scripts/run_tests.sh <tests>` (set `HERMES_PYTHON` to an existing Hermes venv if the bootstrap cannot find an interpreter) and the generated-contract staleness test. Record counts; distinguish pre-existing warnings from new errors.
4. **Isolated runtime home per branch.** Create `<preview-homes>/<name>/`: copy the profile's `config.yaml`, symlink only `.env` (API-key credentials). Never copy `auth.json` (OAuth/refresh tokens rotate and break the other client). This keeps older branch code away from the real profile's `state.db` schema. The first launch per home prepares deps, node and the ui-tsp build, so allow a minute or more.
5. **Launch script** (keep one, parameterized by worktree and home): export `HERMES_HOME`, `HERMES_TERN=1`, `OPENUI_TELEMETRY_DISABLED=1`, `DO_NOT_TRACK=1`, `HERMES_PYTHON_SRC_ROOT=<wt>`, `PYTHONPATH=<wt>`; `cd <wt>`; print branch@sha and home; `exec <venv>/bin/python -m hermes_cli.main`.
   - A disposable home only carries `.env` API keys, so OAuth/pool providers from `auth.json` are missing from the model picker. Shared-store providers such as Nous Portal are missing too. Never use a disposable home when the user is checking providers or doing real testing. Before filing a "provider missing" bug, compare `hermes_cli.inventory.build_model_options_payload(load_picker_context())` under the real profile's HERMES_HOME. To give the user their real providers, launch on the real profile: first `sqlite3 <profile>/state.db ".backup '<backup-dir>/state.db'"` (older branch code may touch a newer schema), then pass the absolute profile path as the home argument.
6. **Open it beside the user's conversation:** `tern split $TERN_PANE right --keep-open --cwd <wt> --json -- <launch script> <wt> <home> [hermes args...]`. Have the launcher forward its extra arguments (`"${@:3}"`) to `hermes_cli.main`, so a session-only model override (`--provider openrouter -m <id>`) leaves the profile config untouched. Further branches split `down` from the previous preview pane. Anchor on `$TERN_PANE`, never `@focused` (that is whichever tab the user is viewing). Tell the user where the pane is and what to try in it. A pane that landed in the wrong tab moves with `tern move <block> right-of $TERN_PANE`. To swap which branch a pane shows, `tern close <block>` and split again from the neighbouring preview pane, so the layout stays put.
   - **Drive and inspect it yourself:** `tern send <block> text "<prompt>"`, then `tern send <block> keys enter`; chords look like `keys alt+m` and `keys escape`. `tern capture <block> --surfaces` returns the transcript's main-region text, which is enough to check a turn's content. Overlays, docks and layout are invisible to it, so judge those from a `grim` screenshot cropped to the pane (vision `region`).
   - **Real-use check is mandatory:** once a build lands, and again after every merge wave into the plugin's main, run one multi-tool turn in the pane (todo + file read + shell + table) and critique the screenshot before telling the user anything works. Then open each feature the wave added (slash completion, Settings, Plan/BTW sheets, artifacts) and screenshot it. Green CI and merged PRs are not "works"; the owner expects the live test without being asked.
   - **Testing the hermes-tern plugin itself (not a Hermes branch):** it is loaded from `$HERMES_HOME/plugins/hermes-tern`, so a disposable home gets `plugins/hermes-tern -> <worktree>` and `plugins.enabled: [hermes-tern]`. Rebuild `frontend/dist/entry.js` locally when the fork's bundle publish is stale: check out hermes-agent at `frontend/hermes-src.lock`, run `npm ci --ignore-scripts --workspace ui-tui` in that checkout, then in `frontend/` run `HERMES_SRC=<checkout> node scripts/hermes-src.mjs && bun install --linker hoisted && node scripts/build.mjs`. The build uses `preserveSymlinks`, so bun's isolated linker leaves `@hermes/shared` and transitive deps unresolvable. Revert `bun.lock` afterwards.
   - **Disposable-home gateway:** disable every `platforms.*` entry copied from the profile and export `API_SERVER_ENABLED=false` in the launcher, because the linked `.env` enables the API server and the copied config enables Telegram. Otherwise the pane loops on `gateway draining: not ready` and `errors.log` shows a non-retryable startup conflict.
   - **Virtual-monitor window:** run Tern on a Hyprland headless output, not the pixman nested Sway (no 8-bit non-sRGB surface, so Tern panics) and not the `agent` workspace on `AGENT-1` (the nested Sway window floats full-size over it, so screenshots come out black). Recipe:
     1. `hyprctl output create headless <OUT>`, then `hyprctl keyword monitor "<OUT>,1600x1000@60,12000x12000,1"`.
     2. The new output immediately takes the next free numeric workspace. Rename it (`hyprctl dispatch renameworkspace <id> <run-ws>`) instead of borrowing a user number.
     3. Launch with `hyprctl dispatch exec "[workspace name:<ws> silent; no_initial_focus on] <absolute launcher>"` and private `TERN_CONFIG_DIR`/`TERN_DAEMON_SOCKET`, or move the client with `movetoworkspacesilent "name:<run-ws>,address:<addr>"`.
     4. Screenshot with `WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/$UID grim -o <OUT> <png>`.
     5. Compare `hyprctl activewindow -j` address before and after; it must not change.
     6. When done, move the window silently to visible isolation workspace 9 for the owner, then `hyprctl output remove <OUT>`.
6a. **Test model for live runs:** use a normal general-purpose free model, OpenRouter `:free`. Fast specialised endpoints such as Cerebras/Groq are helper models the user reserves for special uses. Pick it by measurement:
   - list `https://openrouter.ai/api/v1/models`, keeping ids ending `:free` whose `supported_parameters` include `tools`;
   - for each, stream ~500 tokens and record time-to-first-token and tok/s;
   - send one tools request and require a `tool_calls` response;
   - drop 403/429/400 models and anything with multi-second TTFT.
   State the measured numbers when you name the pick.
7. **Fixes on a PR branch:** separate commits (`fix(ui-tsp): ...`), keep the PR author's commits, re-check `git ls-remote` that the remote head is still the audited SHA, push fast-forward only. Post a receipt comment: exact head SHA, commands and counts, root cause per fix, and what was NOT verified (native e2e, real window, fallback).
8. **Before merging siblings:** in a scratch detached worktree from the base, merge all sibling PR branches in order and rerun typecheck+tests to catch combined conflicts.
9. **Merging:** once the user approves, verify every PR head and the base are ancestors of the scratch head (`git merge-base --is-ancestor`), rerun the gates, then push the scratch head fast-forward to the base branch. GitHub marks each contained PR as merged. Close their task issues and update the roadmap.
10. **Promoting the integration lane into the dogfood/preview branch:** check `git ls-remote` that preview is an ancestor of the lane, then push the lane SHA to preview, fast-forward only. The user's live preview pane runs from a worktree that has preview checked out. `tern close` that pane first, then `git merge --ff-only` the checkout, then relaunch the pane (the launcher rebuilds `ui-tsp/dist`). Updating files under a running frontend leaves it serving stale code.
11. **Signed-out isolated Tern:** an isolated `TERN_CONFIG_DIR` can stop at the closed-beta sign-in gate, which blocks ordinary-window journeys. Label `tern serve` results as their own evidence class and never copy the user's Tern auth into the test config. Offer to open the isolated instance once so the user signs in themselves.

## Pitfalls

- When a sheet/overlay test fails because keys never arrive, check whether the launch splash still owns the surface and keyboard; opening a modal must dismiss it. Fix the ownership handoff and keep the test assertions unchanged.
- A local `origin/main` in a shared worktree store can be thousands of commits stale. Compare against `gh api repos/O/R/branches/main` before quoting "behind N" or trusting a merge dry-run.
- A visible test-run script launched as a Tern pane does not inherit the agent shell's environment. Export everything the e2e runner reads, including `TMPDIR`, inside the script.
- Use a dedicated detached worktree for the user's live pane, e.g. `preview-live`, never the merge worktree subagents reuse. `git worktree add --detach <path> <sha>` already checks out; don't chain a second `git checkout --detach <ref>` after it, because that misparses and breaks the `&&` chain before node_modules get linked.
- Never preview a plugin change by force-reinstalling it into the profile your own pane runs on, and never open a second frontend on the same session (`hermes tern --resume $HERMES_SESSION_ID`). Use a disposable home and a new session. Do not `tern focus` or `tern ctl key` the owner's window either: focus moves to a pane that may stall on frame credits, so the owner's Ctrl+C never reaches the agent and the pane looks frozen.
- `pkill -f <pattern>` matches your own terminal command line when the pattern appears in it, killing the tool call. Kill by PID from `pgrep -af` output instead.
- When composing a fix-pass task for a subagent, give it the real-window screenshots (`images`) and require regression tests that assert rendered text/layout at measured widths, plus before/after captures.
- **Running a Hermes fix inside another ACP host (T3, editors) without touching the live install:** take the live runtime command from `<install>/.hermes/bin/hermes --print-runtime-command -- <args>`. Write a launcher that runs it, then prepends an overlay dir holding only the changed package. Prepending the overlay to `sys.path` is not enough: bootstrap puts the Hermes root first again, so the live module loads instead. After `import hermes_bootstrap`, insert the overlay, `import <pkg.module>` to pin it in `sys.modules`, then remove the overlay from `sys.path`. Prove the fixed module ran (a debug log line in the overlay copy only) before reading any before/after result. Point the host's provider config at that launcher in a sandbox home.
- For native e2e evidence in an isolated Tern (private display, own config/socket), follow `hermes-openui-tern-evidence`.
