# Live-input prerequisite, separate from the fixture

The interactive A viewer and replay export remain synthetic. This follow-up
repairs the inherited `useTernComposerSurface` path before live transcript work:

- The long-lived listener reads current Hermes busy/modal state on every event,
  rather than startup values captured by its React effect.
- Native send no longer references an undefined `sendable` variable.
- Unresolved completions disable native send in both the event gate and editor.
- The submitted native snapshot is invalidated synchronously before forwarding
  the exact text through Hermes' existing submission callback.
- Wrong-surface, wrong-editor and stale-text events are not submitted.

The preceding `8350d0cf` backpressure fix is preserved in this branch's ancestry.
Its regression tests cover A-B-A supersession and invalid ACK credit release.
The input follow-up adds tests against the handler actually used by the hook.
It does not claim a full React/Ink mount or real-Tern GUI input test.

Still pending: live transcript/tool/agent projection, native cursor/Ink input
handoff, complete native modal parity and real-Tern captures. A passing fixture
or transport test does not make `hermes --tui --native` production-ready. No
Python gateway, backend approval authority, provider or prompt-cache behavior
changes in this slice.

References: #432 (protocol/ownership), #436 (experiment), #437 (A). Credit remains
with Can Bölük / Stencil Labs for OMP/Tern reference patterns, Hermes contributors
for the existing composer path, and Kevin Rajan for the experiment direction.
