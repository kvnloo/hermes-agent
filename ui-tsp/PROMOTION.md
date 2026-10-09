# RFC #134833 — bounded promotion contract

This is a **downstream-only** activation/launcher change. It does not make the
full `base/tern-frontend` implementation ready to merge upstream.

## Scope and provenance

- Review: https://github.com/NousResearch/hermes-agent/issues/134833#issuecomment-6069406758
- Reviewed downstream head: `9180555a3376b4b61bccab26269981a0c511c2e2`
- Full native product: `base/tern-frontend`, separate `ui-tsp/`
- Narrower original Ink integration: `feat/tern-tsp-surface`, historical closed/unmerged PR #431
- Tern/TSP and mature OMP reference: Can Bölük (@can1357) / Stencil Labs
- Hermes runtime/gateway authority: existing Hermes TUI contributors
- Review and scope clarification: @yagizkaterli (Zhengwei)

The two scanner warnings for "error-handling-removed" in
`hermes_cli/main.py` were false positives: one docstring change and
one fallback tuple-assignment change. This patch does not alter that
exception handler to satisfy an invalid static warning.

## Actual downstream activation contract

1. TSP is **disabled by default** (`display.tern: false`).
2. `display.tern: true` opts in to TSP when `TERM_PROGRAM=tern`.
3. `HERMES_TERN=1` explicitly forces a probe (including SSH), even
   if config disables TSP; `HERMES_TERN=0` always disables it.
4. `--cli` wins, and no ambient preference hijacks non-TTY commands.
5. Multiplexers prevent probing, even if forced.
6. Exit 75 (no handshake) falls back to Ink. Other frontend exit codes
   remain failures. Backend tools, sessions, approvals, and model state
   stay authoritative in Hermes.
7. `--native` is Ink's primary-buffer mode, **not** TSP permission.

## Proposed first upstream diff — fresh branch from current upstream main

Include **only**:

- `ui-tui/packages/hermes-ink/`: generic APC terminal-response routing
  with tests proving no APC leaks into keyboard input
- `ui-tui/src/tern/`: TSP hello/DA1 negotiation, timeout/no-reply
  fallback, close/drain, and capability validation
- Minimal pause/resume paint seam that keeps React and stdin live
- Scoped tests for these invariants, running against updated upstream main

Exclude the standalone `ui-tsp/` product, build/update integration,
native transcript/composer/tool/subagent projections, attention variants,
OpenUI generator and previews. They are separate future decisions,
not prerequisites for accepting a small adapter seam.

## Evidence owed before promotion

| Required gate | Test evidence needed | Status |
| --- | --- | --- |
| Plain terminal/no handshake | TSP probe times out; Ink stays interactive | Not executed here |
| Busy/modal/current-state | Hermes rejects prohibited native submissions | Not executed here |
| Buffered multiline | Full buffer atomically submitted | Not executed here |
| Stale event | Reject previous surface/session events | Not executed here |
| Frame credits/ACK | Never overrun negotiated window | Not executed here |
| Runtime authority | Surface only projects gateway-owned facts | Needs review |
| Real Tern | Capture/replay and actual-terminal E2E | Not executed here |
| Upstream rebase | Small slice compiles and passes current-main CI | Not executed here |

The activation/fallback unit tests added on this branch do **not**
substitute for the protocol or real-terminal conformance evidence.
