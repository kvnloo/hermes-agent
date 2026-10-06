# A: runnable native Tern fixture

Tracks #436 / #437. This is the first executable presentation slice, not a live
Hermes backend integration and not an approved visual design.

## Run the checked-out code

In a Tern shell at the root of `exp/tern-ux-omp-baseline`:

```bash
npm ci --workspace ui-tui --include-workspace-root --ignore-scripts
npm run tern:ux:preview --workspace ui-tui
```

The preview uses this worktree's TypeScript entrypoint. It never resolves a
possibly unrelated installed `hermes` executable. No Hermes account, model key,
Python agent environment, or copied private configuration is needed.

For a separate checkout without switching your active branch:

```bash
git fetch origin
git worktree add --detach ../hermes-tern-a-preview origin/exp/tern-ux-omp-baseline
cd ../hermes-tern-a-preview
```

Then run the install/preview commands above. The preview does not create files or
modify sessions; npm installation only prepares the checkout's dependencies.

## What is interactive

`n` / Right advances; `p` / Left goes back; `r` resets; `b` dismisses an inspector;
`q` / Ctrl+C quits. Pointer controls do the same. Tool/agent disclosures are
native and their chosen fold survives later fixture steps.

The composer is deliberately **read-only**. Model selection and allow/deny are
local simulations. The fixture advertises no `edit`, `undo`, or `send` feature.
Opening an inspector from the composer leaves the task step, transcript and
composer in place. Dismissing it does not jump to completion.

The 14-step walkthrough includes transcript, thinking/work status, read/edit,
subagent, queue, a simulated approval, separate failed/retry tool calls,
completion, model and background inspectors, and a file preview. Step 13's file
preview is explicitly **not a real Tern split/browser PiP**. Next/Previous select
scripted snapshots; they do not execute the simulated command after a decision.

## Representation and limitations

- One TSP inline surface owns `main`, `dock`, and `layer` throughout navigation.
- Stable IDs and minimal `add/set/text/move/del` patches preserve native view state.
- Growing assistant text uses `text append`; there is no per-token full rebuild.
- Frame credits bound in-flight updates; pending changes coalesce to the latest view.
- A failed attempt remains failed when a separate retry succeeds.
- Missing TSP/kinds fail explicitly; ordinary ANSI output is not passed off as native.
- `gone`/document errors stop the fixture rather than mutate stale node IDs.
- Close sends `x`, keeps raw input alive through a DA1 barrier, then restores it.
- Chunked terminal-to-program replies are explicitly unsupported by this viewer;
  the existing Hermes kernel handles outbound chunking.

The lab notice/navigation controls are test chrome, not the proposed product UI.
Do not include them in future salience comparisons. No human timing, eye travel,
pixel geometry, complete product view-graph coverage, or native visual parity is
claimed by these tests. Real Tern screenshots and host interactions still need
review before choosing a design or wiring it to Hermes sessions.

## Offline inspection and tests

```bash
npm run --silent tern:ux:preview --workspace ui-tui -- --dump > /tmp/native-a-views.json
npm run tern:ux:check --workspace ui-tui
npm test --workspace ui-tui -- src/tern
python3 ui-tui/scripts/tern-ux/smoke_preview.py
```

The JSON contains semantic documents, **not screenshots** or performance receipts.
The Python smoke test is POSIX-only: it runs the actual Node entrypoint in real
PTYs at 80x28, 120x36 and 180x44 with a fake Tern protocol peer. It checks
negotiation, all 14 states, one open/close, late-event drain, and restored TTY mode.
A fourth run checks unavailable TSP. This is process/protocol evidence, not a
replacement for running the native Tern GUI.

Production `App`, the existing composer hook and `tui_gateway` are unchanged.
Their approval fallback and runtime authority are not implemented by this demo.
B/C and the shared base are unchanged by this slice.

## Reference and credit

Kevin Rajan specified the evidence-first, multi-view experiment. Can Bölük /
Stencil Labs own the OMP native presentation and Tern/TSP designs referenced here.
Hermes contributors own the existing application semantics this experiment adapts.

- Canonical native visual reference: https://stencil.so/tern (03 Graphics)
- OMP user-card/composer shape reference pinned at `d9ee5e6a31d621f50ac6610cd1cdadccfbf41b0c`:
  `packages/tui/src/chat/user-message.ts`, `packages/tui/src/prompt/custom-editor.ts`
- Protocol: https://docs.stencil.so/tern/protocol/documents.html
- Native editor: https://docs.stencil.so/tern/elements/input.html

The `omp.user`, `omp.composer` and `omp.editor` roles deliberately opt this control
into Tern's built-in OMP styling hooks. The program identifies itself as
`hermes-ux-fixture`; these hooks are an experimental dependency, not a claim of
pixel parity or an OMP runtime port.
