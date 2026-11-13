---
name: dsh-source-diagnostic-runner
description: Use when testing source-only DSH study runners.
version: 0.1.0
---

# Source-only DSH diagnostic runners

- Run Bun `-e` from the source checkout when its tsconfig aliases own first-party resolution; pass the study program as bytes, not a module rooted in another checkout.
- Keep a narrow Bun onLoad rejection guard for installed first-party paths. Bun 1.3.14 requires an object from a matching onLoad callback: a catch-all observational callback returning undefined blocks imports. Do not rewrite loaded contents to work around it.
- Avoid recursively calling Bun.resolveSync from a matching onResolve callback; it can crash the process. Disable core dumps before exploratory bootstrap.
- Observe Bun's require.cache after evaluated imports to record actual ESM/CJS paths and hashes without changing loader semantics. Include borrowed native objects from process maps where needed, package manifest versions, and the Bun binary pin. Label this explicitly non-lockfile-parity; OS libraries are not covered merely by a Bun pin.
- Default-deny both agent/pre-step and fetch for source seam checks. A real Agent must reach scoped system-prompt/assemble before rejection, with zero neutral/native requests and an authoritative blocked turn/end.
- Append one stable uninterpolated evidence section after next() exactly once and preserve every assembly field. Verify final assembly to catch complete-prompt suppression before a real driver turn.
- Distinguish same-retained-Agent no-op replay, real projection decisions over its retained Session, and actual second model delivery. Do not call the first two proof of a second request or cross-process resume.
- Test native request/response streaming capture with local HTTP, and adapter/Agent settlement with clearly labeled offline UNIT protocol fixtures. Never present those responses as source-backed cohort answers.
- Combine the real source adapter/Agent with native loopback SSE whose HTTP EOF is delayed after message_stop; separate tests of native fetch and buffered fixture Responses miss adapter cleanup aborting the clone reader after a complete protocol response. Verify complete-frame hashes, authoritative settlement, and true early-cancellation rejection separately before qualifying the tee.
- Classify cleanup-aborted captures with the actual source protocol parser and independent authoritative settlement. When terminal protocol frames are complete but HTTP EOF was not observed, retain the abort/read-error flags, hash only saved bytes, leave the full-response hash null, and mark trailing HTTP bytes unknown. Reject truncated/fake terminal frames, non-abort read failures, and user cancellation even if another signal suggests success.
- Validate saved capture bytes with the pinned source adapter's parseSse plus translate; do not synthesize delimiters or accept a message_stop substring. Keep protocol completion, HTTP EOF, read failure, and authoritative Agent settlement as independent facts. A terminal-complete cleanup-aborted prefix may be usable, but label its trailing HTTP body unknown and leave the full-body hash null; hash only bytes actually saved.
- Fault-inject the clone independently of a successful native source turn. A completed Agent answer must not mask a truncated terminal capture or a non-AbortError read failure; likewise a valid terminal capture must not mask Agent cancellation, error, empty answer, or max-tokens settlement.
