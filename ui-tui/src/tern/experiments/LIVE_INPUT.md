# Live-input integration and replay verification

This follow-up started by repairing the inherited native composer listener.
While #441 was open, the A worker integrated its input handler and four tests
alongside the first live prose transcript projection (`d887d2fe`, `0ce4632e`).
The merge here preserves that exact A implementation and its ancestry instead
of replacing it with the earlier composer-only file.

The integrated path now reads current Hermes busy/modal/completion state on
every input event. A pending modal prevents both edits and submissions before
listener cleanup; unresolved completions disable native send. The same existing
Hermes submit callback receives unchanged multiline text, and its native
snapshot is invalidated synchronously before a duplicate event can land.

This PR's remaining delta is verification:

- Joint input/transcript tests use the real input handler, inline-session owner,
  prose projection and transport with a captured writer and synthetic ACKs.
  One-credit backpressure must coalesce to the newest transcript and draft.
  Returning the composer to its previous text must not discard new prose.
- CI also exports the current native fixture at all three target dimensions,
  checks checkpoint/manifest identity, refuses a second write to the same files,
  and verifies that their hashes stay unchanged.

These tests do not mount the entire React/Ink application and do not prove
native GUI focus, cursor, keyboard or scroll behavior. The fake-peer PTY tests
exercise the fixture process, not a model-backed live session. Scoped fixture
TypeScript checks are not a full-repository typecheck.

Live prose projection is present on the parent, but full tool/agent/status
visibility, stable streaming-to-history handoff, native cursor/Ink input handoff
and real Tern captures remain separate gates. Do not describe the inherited
`hermes --tui --native` path as production-ready merely because the fixture
passes. Native approval authority and the Python gateway are unchanged.

Refs #432, #436, #437, #441. Credit: Can Bölük / Stencil Labs for OMP/Tern
reference patterns; Hermes contributors for application behavior; Kevin Rajan
for the experiment brief. Concurrent integration commits are retained intact.
