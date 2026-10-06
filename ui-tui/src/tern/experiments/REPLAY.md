# Replay export reconciled with the interactive A viewer

The earlier `hermes-tern-a-native-preview.patch` was authored against `6e75b1ed`.
Before publishing it, #437 had advanced to `f7c9d582` with a runnable interactive
fixture. This change salvages the archive's deterministic JSONL export, manifests
and no-overwrite command while preserving that newer implementation.

There is one source of fixture presentation: `nativeView.ts` and
`NativeFixtureSession`. No second `nativePreview.ts` task, duplicated reconciler,
or replacement of the existing preview runbook is introduced. Old archive
recordings depict the old authored task; do not mix them with this revision.

```bash
npm run tern:ux:record --workspace ui-tui -- /tmp/hermes-tern-a-replay-1
npm run tern:ux:check --workspace ui-tui
npm test --workspace ui-tui -- src/tern
```

The command writes `narrow`, `normal` and `wide` JSONL/manifest pairs. Existing
output files are refused. The default is the ignored worktree-local
`.hermes-sandbox/tern-ux-preview-a/`. A partial I/O failure can leave some files;
choose a fresh directory rather than deleting another run.

All three recordings have the same semantic frames. Their 80x28, 120x36 and
180x44 manifest targets do not resize the actual terminal. The one-second beats
and ACKs are authored, not measurements. The final frame remains open.

Use the installed Tern binary's `tern help dev` and its `surface-play` developer
control to replay in a **disposable pane/window**. The first playback can replace
the focused pane's program; never target a live agent, server or unsaved shell.
This export does not invoke Tern automatically. Playback has no application
listener, so the visible fixture buttons and composer are not interactive.
Use `npm run tern:ux:preview --workspace ui-tui` for the interactive simulator.

Native GUI captures, real pointer/focus/scroll behavior, host splits and human
attention measurements are still pending. No live Hermes authority is changed.

Credit: Can Bölük / Stencil Labs for OMP's native reference patterns; Stencil
Labs for Tern/TSP and replay tooling; Hermes contributors for application
semantics; Kevin Rajan for the experiment brief and evidence-first review.
