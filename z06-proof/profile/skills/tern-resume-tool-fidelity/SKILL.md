---
name: tern-resume-tool-fidelity
description: "Use when qualifying resumed Tern tool cards."
---

# Tern resume fidelity

- Trace `tui_gateway/session_history.py` and `ui-tsp/src/transcript.ts` together: SQLite results may be dropped only by the display projection.
- Reuse the live completion fold as well as the card builder. Restore exit/status/interruption, final todos and persisted diffs; leave durations absent unless actually stored.
- Bound structured display copies in one helper shared by live completion and history. Preserve scalar metadata and command-output tails without changing SQLite/provider bytes.
- Project dangling invocations after assistant text/reasoning; never turn a missing result into success.
- Exercise cold and lazy session.resume with a real SessionDB in a temp HERMES_HOME; disable agent-build scheduling, not persistence reads.
- Mount real App/SDK with a fake gateway, intercept surface.render and inspect View.from(value). Its normalized Tree objects are not SDK Node instances: recurse without instanceof Node.
- Prove regression tests fail with the base loader, then restore and run the full Vitest suite.
- Update protocol/Codex-sidecar expectations for retained outputs and dangling invocations. Raw stored message counts need not equal projected row counts.
- Compose run-box and resume fidelity explicitly: retain live `finishedAt` alongside the shared completion fold; carry unknown-result status into the run-box footer as muted “no result recorded”, never default success. Keep output-only disclosure callbacks and prevent whole-tool folding from hiding the footer.
- Update resumed App harnesses for frame pacing: install `acknowledgeFrames(tern)` before `App.run()` and disable/restore the launch splash in isolated tests. Otherwise valid resumed entries may never reach the captured surface while paint credit or splash ownership blocks rendering.
- Compare live/resumed semantic input, output and outcome separately from observed-only elapsed time. A true tool.start/tool.complete pair may show timing; history or late-completion recovery without an observed start must not. Keep an exact-tree comparison for the no-observed-timing case too.
- Scope eslint --fix to owned files: whole-tree fixing can change unrelated baseline warnings.
- Report tern-serve separately from native-window evidence. After uncertain committed input, do not retry in the same runtime; use a fresh isolated runner.
