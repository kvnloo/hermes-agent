---
name: hermes-openui-tern-evidence
description: Use when proving Hermes OpenUI previews in real Tern.
version: 1.0.0
metadata:
  hermes:
    tags: [hermes, tern, openui, evidence, gui]
---

# OpenUI boards and native integration evidence

## Connected-app board delivery

For a requested `openui-v2` board, describe the required connected-tool schemas together, then invoke independent read-only calls in parallel. Honor an explicit once-per-tool budget; perform catalog discovery without repeating account queries. Preserve literal queries and place names, and do not attach booking, merge, or other mutation callbacks to a read-only board.

Read the active client's component catalog before composing the fence; tool result field names are not necessarily component prop names. Prefer a targeted lookup of `OpenUiAppCards.tsx` and the Board definition in `OpenUiCharts.tsx` within the known checkout, rather than searching the entire scratch tree or dependencies. Use the positional `root = Board(...)` language inside one `openui-v2` fence, not invented JSON or a substitute HTML board. Follow the [app-card mapping recipe](references/connected-app-boards.md) for the inspected catalog, and recheck signatures when the client changes.

Carry demo/fixture provenance into both the board and its concise summary; a connected-app label does not make fixture responses live prices, traffic, inbox data, or repository state. Match the requested summary sentence count and state that no booking occurred when relevant. Distinguish an emitted catalog-conformant fence from a verified rendered board; do not claim pixel or parser verification without execution evidence.

## Native integration evidence

For stock parser/React catalog experiments, follow [catalog renderer qualification](references/catalog-renderer-qualification.md) before native integration. Keep parser/SSR smoke results, real generation measurements, integrated UI proof and installation proof separate; progress in one does not satisfy the others.

Read the branch's OPENUI-DISCOVERY.md, OPENUI-FRONTEND.md and experiment READMEs before running. Keep discovery/frontend and independent Git collector heads separate; preserve the active preview branch in detached worktrees.

Use an ordinary Tern window on a private display, not `tern serve`, `tern shot`, surface replay or mocked JSX as substitutes. Set per-process `TERN_CONFIG_DIR`, `TERN_DAEMON_SOCKET`, `DISPLAY`, unset host `WAYLAND_DISPLAY`; verify the config-local plugin directory before `tern plugin link`. Inspect host.luau, window.luau, plugin.toml and CSS first. Read back ready status and problems. Unlink only in the disposable configuration for file-viewer fallback tests.

Keep OPENUI_TELEMETRY_DISABLED=1 and DO_NOT_TRACK=1 on every actual prepare execution, including the agent's terminal command. Parent shell environment may not reach the backend terminal. Failed tool output must not become a discovered candidate; test a successful real terminal --json result. Use /visual's literal current stored-session/branch scope. Resumed history can omit completed tool results, so no picker after resume is documented rather than necessarily a defect.

Prefer canonical scratch TMPDIR for alias-sensitive file guards. With TypeScript6, focused CLI file invocations may need --ignoreConfig --types node; project typecheck may need --types node. Record stock failures separately from adjusted green. Isolated sibling imports can require a node_modules link; keep it ignored and preserve source cleanliness.

For parity feature qualification, use the owned `scripts/dev/tern-e2e.sh TARGET JOURNEY... --node NODE` runner when present. It can target a different exact-SHA worktree while keeping harness and product heads separate. Preserve all ten native Settings cases; a short `tern serve` journey is a separately labelled fallback, never that suite's acceptance. Use short private scratch child names: long canonical XDG runtime paths can overflow Sway's Unix socket limit. Keep both Tern's config/socket and HOME/all XDG paths private so a disposable daemon cannot restore ambient tabs/state.

After native key/click delivery, wait for or repeatedly observe the expected actual state before claiming success. A file block at `load=opening` proves allocation only: use `file wait loaded`, then require exact-path `load=ready` and inspect its pixels. Wait for populated acknowledged Settings and stable native target identity/geometry before dispatch; never retry an ACTION_MAY_HAVE_COMMITTED input. Verify copy bytes and host clipboard readback separately: an exact answer-only OSC52 payload is not evidence the host Paste returned it. Immediate tree reads can race the Luau update. File links may require `click "SELECTOR" meta` as their native title describes. Native focus can require a first pointer click before keys reach a newly opened artifact.

For a separately labelled headless Luau regression, `tern serve` does not load normal daemon/plugin routes by itself. Set an owned `STENCIL_FIXTURE_ROOT` to a disposable app-crate directory, place the exact plugin under its sibling `plugins/fixtures/`, then explicitly invoke `plugins fixtures` before `file open`. Read back actual main+dock and cell rectangles; label this `tern-serve+real-Luau+fixture-plugin-root`, never ordinary-window route evidence. Preserve copied shots outside scratch. Pin Node 26.7/npm 11.19 for the frontend installer: npm 10.9.8 can reproduce an Arborist `edgesOut` crash on its workspace graph even with workspaces disabled. Exercise installs in a tracked-HEAD archive, never a linked donor tree. Keep standalone E2E framework dependencies local via its ignored node_modules link.

Do not assume `plugins expect` searches dock text. Verify a main title and a dock identity independently: the preview recipe can time out on dock markers while the native tree and PNG visibly show them. Repair identity placement or focused main+dock verification; never remove fail-closed full-ID checks.

Check dense real document layout, not only a three-tile fixture. Measure every .nv-cell rectangle against .nv-map. Fixed leaf padding and recursive gaps can force 8px minimum geometry and overflow even with min-width/min-height zero. Correct geometry budgets rather than hiding overflow.

Require positive visible map and cell dimensions after drill, especially directories with exactly one child. Root containment can pass while a singleton `.nv-cell.nv-map` inherits a zero basis and collapses to height zero; a capture recipe can likewise pass identity/navigation checks despite an empty drilled view. Inspect root, drill and restored PNGs and test each topology, not only dense-root bounds.

Measure actual grid columns/rows from control state. Tern's minimum window width can defeat80columns at13px; a disclosed consistent15px font permits80x28,120x36,180x44. Inspect actual PNGs; screenshot headers alone are not a pixel pass.

Separate generation/compile, native startup marks, command-to-observed-state, frame present summaries and input-to-paint. CLI round trips and polling are upper-bound observation latency, not physical paint latency. Retain samples and calculate percentiles in code. A failed capture recipe cannot mint first-verified-artifact latency. Keep host inspection/publication authority untouched.

Use manual approvals in an isolated profile when testing the native deny path. Create only owned empty disposable data; do not bypass the gate. Escape can deny a pending approval while closing another overlay, so observe the actual top layer and verify the data survives. True bound-callback races require controlled live evidence; ordinary dismiss/resume tests do not prove those races.

Preserve logs, screenshots and exact source heads outside auto-pruned scratch. Exclude auth/config secrets, dependencies and unrelated shared shot files. Do not copy another client's refresh token for provider setup: use the configured authentication authority without rotating another client's grant.
