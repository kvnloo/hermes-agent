# Surface recovery and protocol failures

`surface-protocol.ts` owns only presentation lifetime, never gateway session state.
It uses public `@stencil-hq/tern` 0.1.0 APIs. No new RPC, terminal event, or private
SDK field is assumed.

- **Visible:** normal credit-paced rendering. A one-shot five-second watchdog is
  armed only when the surface exhausts its negotiated credits. It reports the
  stall to stderr and the transcript, once; it does not acknowledge, close,
  recreate, or send an escape frame. Real ACKs resume the newest dirty model.
- **Hidden:** `visible: false` (including resize visibility). Rendering and the
  watchdog pause; no ACK is expected. Returning visible never manufactures credit.
- **Detached:** the whole surface is gone while hidden. Wait for an explicit
  visible edge before opening anything. The SDK has no distinct detach/attach
  event; hidden alone is not evidence of a missing document.
- **Failed:** malformed protocol events, terminal operation rejections, or local
  view-build failures are reported and stop that surface. Do not replay rejected
  operations or flush an untrusted queue. Reconnect the frontend if the terminal
  does not subsequently report the document gone.
- **Disposed:** shutdown cancels diagnostics and rejects further opens/events.

A whole-surface `gone` creates a fresh inline `omp.session` document, at most
three replacements per frontend lifetime. Each replacement has a unique surface
ID, so delayed ACKs and handlers from earlier epochs cannot credit or mutate it.
Restore the latest palette, current gateway transcript, composer draft/caret,
chrome and live overlay objects (including in-flight settings/approvals). Do not
reissue their gateway intents. Recreate the orb on the new document and retire
its old animation. No timer drives recovery. The SDK's pre-existing final
close/kept-scrollback behavior remains separate from recovery; no stall escape
is added.

Child eviction never consumes a surface recovery attempt. With retention enabled,
settled roots stay cold and use the existing explicit history reload. Active
roots and partial subtrees are rebuilt from the current projection. Without
retention, remember the last public View and switch to eviction-aware View.ops
when a child is gone. Forgetting preserves surviving sibling IDs, including
unkeyed children. Chrome uses the same eviction-aware public reconciler. Drop
pending raw controls on eviction; defer their ACK-triggered flush until gone
notifications from the same input read have been delivered. Never delete, edit,
settle or focus an absent target.

Tests: `src/__tests__/recover-missing-surfaces-report.test.ts` mounts App against
the real SDK and a strict peer, plus the existing frame/retention/settings/orb
suites. Native window-loss/reattach still needs an authenticated isolated Tern
window; passing tern-serve smoke/settings/retention is not that evidence.

Reference: OMP by Can Bölük / Stencil (MIT), pinned `eb74cf84`,
`packages/tui/src/native/backend.ts:611-635,825-837`. This implementation uses
SDK public primitives and deliberately does **not** port OMP's stalled-ACK
credit escape.
