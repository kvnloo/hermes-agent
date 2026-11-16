# Experimental Tern composer seam (fork draft)

This is the bounded candidate for [RFC #134833](https://github.com/NousResearch/hermes-agent/issues/134833),
not the downstream `ui-tsp/` frontend. It adds one native composer to the existing Ink client.
Ink continues to render the transcript, tools, approvals, settings and all other UI. Python and
the existing submission pipeline keep session, command, history, queue and execution authority.
No gateway contracts, runtime handlers, desktop code, OpenUI, parity features or second frontend
are imported. This document is a review receipt, not upstream approval.

## Activation policy

- Default `display.tern: false`: no TSP detection, handshake or surface; ordinary Hermes is unchanged.
- Select Ink explicitly with `hermes --tui` (or the existing `display.interface: tui` setting),
  and opt into its experimental composer with `hermes config set display.tern true`.
- Configuration opt-in probes only when `TERM_PROGRAM=tern`.
- The SDK's existing `TERN_TSP=1` per-launch override permits an explicit SSH probe;
  `TERN_TSP=0` vetoes it. No new `HERMES_*` environment setting is introduced.
- `--cli` wins. Bare classic Hermes and noninteractive ambient preferences retain upstream routing.
  `--dev` always uses Ink without probing.
- tmux, screen and zellij block probing even with a forced SDK override.
- Missing/unreadable/non-boolean configuration fails closed. Detection alone is never consent.

The entrypoint completes its 700 ms SDK probe **before starting the gateway**. No hello or an
incompatible hello exits 75 after SDK cleanup, and the Python launcher runs the same Ink argv
without the internal `--tern-composer` switch. Other exits, including errors and update requests,
are not hidden by fallback. Disable with `hermes config set display.tern false` or `TERN_TSP=0`.

## Input and transport contract

- A small binding presents the real composer refs, including **all buffered lines**, and invokes
  `dispatchSubmission` directly with the atomic send text. Existing history, slash commands,
  attachments, durable admission and Python RPC semantics remain authoritative.
- Every event rechecks live session/profile/execution identity, draft revision, gateway readiness,
  busy and modal state immediately before dispatch, not a captured React render. Busy native
  submissions are refused (the ordinary Ink queue/steer behavior is unchanged).
- Draft identities rotate on changes. Old node ids and retained handler closures are rejected,
  including same-length replacement drafts. A send invalidates itself before dispatch.
- Native drafts are limited to 256 Ki UTF-16 units; oversized native edits/sends are refused.
  Edit ranges, lengths and cursor bounds are validated. Native undo is **not advertised**.
- Protocol input is filtered out before Ink's keyboard parser; ordinary bytes are preserved.
- `@stencil-hq/tern` is pinned to 0.1.0, with the registry integrity in the lockfile. Its negotiated
  credit/ACK renderer holds one replaceable view, not a per-update queue. The adapter only calls
  `render` (no raw operation queue or polling). Compatible hello credits are bounded to 1–8.
- `gone`, hidden surfaces and cleanup reject further native actions. Modal contents are never
  copied into the native composer. Ambient SDK protocol recording is disabled.

## Review-ask evidence

| Ask | Evidence |
|---|---|
| Exact bounded patch / activation policy | This scope + launcher module; no downstream preview merge |
| No-handshake + exit-75 Ink fallback | SDK timeout/raw-mode cleanup test, real child fallback test, built-entry pseudo-TTY probe |
| Current-state / busy / modal guards | `ternComposer.test.ts` and React bridge test; mutation before event invocation |
| Full buffered multiline send | React bridge uses real `useComposerState`, `useSubmission`, history and prompt RPC stub; full buffer dispatched once |
| Stale-event rejection | Old node and retained-handler tests, owner/revision changes, cleanup/gone |
| Negotiated ACK/credit backpressure | Real SDK hello fixture negotiates credits=1; 1000 refreshes coalesce until ACK, duplicate ACK adds no frame |
| Runtime authority | No new RPCs or runtime code; bridge tests existing dispatcher/history |

The Python precedence/fallback cases are adapted from `review/134833-tsp-optin-gates`
(`573b88c575`). Deliberate differences: opt-in does not reroute bare classic Hermes, the SDK's
`TERN_TSP` override replaces downstream `HERMES_TERN`, and only a composer adapter is included.

## Qualification limits

Fixture-terminal tests are **not real Tern E2E**. Native focus/caret continuity, terminal/grid
coexistence, suspend/external-editor behavior, host close/reattach, and real inference/tool journeys
remain promotion gates. Do not merge upstream or into fork main on unit evidence alone.

The full Ink suite currently has five failures in three existing files (markdown OSC8 delimiters,
cold pending recovery, submission destination receipt removal). Each failure was reproduced on an
unmodified archive of the pinned upstream base using the same dependency donor and Node binary;
they are not silently waived as green. Local focused seam, build, type and lint receipts belong in
the fork draft PR. No upstream PR or comment is authorized by this preparation.

## Provenance

Can Bölük / Stencil authored the Tern SDK and downstream ui-tsp foundation; NousResearch authored
Hermes runtime, Ink and gateway; @thefullctx contributed native UX requirements and reference
checks. This candidate adapts the downstream activation/test lessons rather than copying the full
frontend. The new integration and qualification work is on the fork-only seam branch.
