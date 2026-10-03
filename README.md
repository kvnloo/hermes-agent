# Reviewed downstream lifecycle and integration evidence — 2026-10-03

Four bounded candidates from five independent work lanes. This receipt records local evidence, not whole-PR qualification, upstream approval, ownership transfer or hosted CI success. Exact publication commits, trees, parents and new branch names are in publication-map.json. Original refs and human history are preserved. No installations, live model/provider requests, upstream messages, PR creation, canceled workflow reruns or deployment were performed.

## Rejected hot-profile retirement

Candidate `b45fe7c21c89a8b46911df7c86afc68023025d2f`, parent `cb8d6920549ebe9d31f69f187d30b356b5639eed`.

Addresses [keeltrace's unresolved runtime-retirement review](https://github.com/NousResearch/hermes-agent/pull/106742#discussion_r4123365771) on Teknium's open #106742. A configuration-rejected hot-added/changed profile now retires through existing `_unserve_profile`, removes current/added/signature bookkeeping, parks, and refreshes surviving resource claims. Healthy profiles remain served. Credits: keeltrace, Teknium; Codex authored this bounded correction and tests under Kevin Rajan direction.

Exact whole-source parent plus the identical two new test cases: **2 FAIL**, both because expected parked state was absent. Candidate two new cases plus eight existing hot-serve cases: **10 PASS**, independently **10 PASS** (repeated evidence, not twenty cases). One real-control-socket case excluded. Root independently reviewed the diff and runtime-backed tests; no scoped blocker. Later cleanup assertions are positive-side evidence, not separately proven old-source failures.

Canonical selection: `scripts/run_tests.sh tests/gateway/test_multiplex_config_error_retirement.py tests/gateway/test_multiplex_hot_serve.py -k 'not lifecycle_over_real_control_socket' -q --tb=short`, existing PM interpreter, retries disabled. Real GatewayRunner, SQLite, registry/reservation/runtime retirement; finite adapter configuration failure and stubbed external discovery. No native listener, credentials, ticket use, routing/auth changes, or full hosted lifecycle claim.

## Local interrupt marker ownership

Candidate `71910cd9f6dc5b7381c23da4070c792177dea0c3`, parent `681e4cae5d3828586940fa029d62aa165b75fd20` (published cancellation-fanout correction). Original protocol work: [Liuzikaii / KaiKai, #125419](https://github.com/NousResearch/hermes-agent/pull/125419).

Actual local `session.interrupt` now opts into recovery-marker retirement after successful agent interruption and before cancellation notifications. A notification write failure remains visible but cannot leave this stopped turn recovery-eligible. Independent review caught the wider shared-helper caller scope: default-false opt-in preserves shutdown, lease-takeover and compute callers. No blanket cleanup in a finally block.

Identical four new cases on exact parent: **1 FAIL, 3 PASS**; failing arm schedules recovery from a stale marker after interruption and notification error. Candidate complete auto-continue/protocol selection: **105 PASS**, including four new cases. Independent reviewer reran the four new cases: **4 PASS**, no blocker; did not repeat negative control. Preservation cases cover failed hard interruption and default helper ownership. Actual StdioTransport, pending registry, owned-profile marker files and recovery eligibility; inert agent and scheduling boundary. No actual process restart/model run, every-callback-error guarantee, native compute proof or successful stop-ack claim after transport failure.

## Composed voice lifecycle

Candidate `00df1a838c40badf77cfb6b6ed11f2e9682bcfd8`, parent `b9bf6f84f3f464c38a9c09056ada0d1d1ff0a1d2`, the author-preserving cherry-pick of [Detail app #58](https://github.com/kvnloo/hermes-agent/pull/58), source `8c7c49403574f045429bc50086fdd7ccd528d584`, onto published deadline fix `531610fcbdae54dcc526cb44a68f34a26457ebb8`. Credits also Julien Talbot and Teknium for [upstream STT #118788](https://github.com/NousResearch/hermes-agent/pull/118788), Kevin Rajan for [carrier #406](https://github.com/kvnloo/hermes-agent/pull/406), and Teknium for shared lease infrastructure. Codex added one test; no new production logic.

Actual composer/conversation hooks, direct response-body reader and shared lease queue: start, fake microphone clip, stalled real Response/ReadableStream body, idle sibling mount/unmount, deadline failure, notification/listening rearm, End release. Finite fake hardware/IPC/fetch forwards abort to the stream. It connects the transcription callback directly, not a mounted full ChatBar.

Six-file selection: **54 PASS (one new, 53 existing)**; Desktop canonical typecheck all four steps PASS. Independent final integration: **1 PASS**, no blocker. Exact carrier `8cc0f9541c49bd9b83830dd0979a38dc872ae047` direct-module control: **1 FAIL**, missing abort. Exact `531610` composer-hook control with fixed reader: **1 FAIL**, premature lease release. These module-substitution controls stop at distinct prerequisites; later recovery assertions are positive evidence only. No latest-main, full native audio, real-network abort, backend warmup, live handoff or multiple-active-profile qualification. Broader [Froraut #129826](https://github.com/NousResearch/hermes-agent/pull/129826) remains separate.

## Current model picker integration

Candidate `261a2b16094a40fb2b2c61e4bd52640d701432be`, parents reviewed `e03ca28af7d027adb8e8a4ab5c9187434762d349` and pinned main `bd0affe5e5f723579df8902852f5d0c47795f355`; exact automatic merge tree `d22de7021952c88dc169313051dbc5b7fb3714b4`. Preserves Kevin Rajan's four authored commits in [#126847](https://github.com/NousResearch/hermes-agent/pull/126847). No new production logic/tests. Credit andrexibiza for review already addressed by Kevin. [Current RFC #110124](https://github.com/NousResearch/hermes-agent/issues/110124) favors this narrower existing-picker design over older fork #400; older #111470 is parked by its owner.

Reviewed source four-file selection: **86 PASS**. Integration same selection: **88 PASS**, independently **88 PASS**, typecheck PASS, i18n key check fresh (1259 keys). The two extra tests already existed on main for browser slash handling; they are not new picker coverage. Exact main modelPicker.tsx substituted under unchanged authored search tests: **1 FAIL, 2 PASS**, missing selectable model row; restored **3 PASS**. Control uses an extended harness deadline to reach the existing assertion, not a timeout failure. Audit compares the candidate against pinned main (20 files), not the first-parent main-history import.

Tests exercise existing picker and slash handlers separately. No end-to-end backend model-switch proof, full TUI/PTY, latest-main beyond this snapshot, hosted CI or overlap resolution with #110134 is claimed. Owner decides whether to refresh the existing review path.

## Fifth lane: owner disposition, no speculative patch

Fork #178 / [Wenfengcheng's upstream #123578](https://github.com/NousResearch/hermes-agent/pull/123578) remains open at `e5b3bbb37ff6dab8ecdefff9b66b007368033fd8`. [Enough1122's review](https://github.com/NousResearch/hermes-agent/pull/123578#issuecomment-5861217260) asks for behavior conflicting with the current explicit non-timeout reconnect contract and committed preservation test. **HOLD: owner/maintainer contract decision required.** No probe, policy change or reproduction was performed. Superseded #125364 and already-proven #125507 were not recycled as new work. This lane independently reviewed interrupt correctness and all four publication trees instead.

## Verification and standing limits

Final read-only source-status refresh confirms cited candidate heads remain open and unchanged. Independent publication audit compared all 205 workflow blobs/events across the four exact heads: no create events or push filters matching these new reviewed branches; no secret/local identifying data found in the publication changes. A separate remote verification binds exact refs/trees and checks Actions/check/status presence; empty results mean CI NOT_RUN, never PASS.

This evidence does not lift #417's owner-disposition hold (NOT_MET_AS_WORDED), the Library authorization block, or any prior restricted execution boundary. Existing Gemini assessment is complete and was not repeated. Weather lint/formatter availability remains a limitation; no tools were installed. Raw local logs and full reports were retained privately; this root receipt contains only sanitized results and public provenance.
