# Hermes downstream integration and consumer receipts — 2026-10-03

This wave preserves one combined implementation branch, three test-only branches and one test-fixture repair. **No new production logic was authored.** Each result received independent review and execution. All original refs and [wave3 receipts](https://github.com/kvnloo/hermes-agent/tree/downstream/20261003-reviewed-wave3-receipts) remain held. The integration below qualifies a specified source union and six-suite matrix, not current main or the entire PR.

Five new exact downstream heads were verified by remote commit and tree. Exact-head CI observations have zero workflow runs, check runs and commit statuses: **CI NOT_RUN**, not PASS. All workflow YAML was parsed at each head; no push trigger matches these new reviewed branches. No upstream PR/comment, merge, deployment, authentication implementation change, paid provider call or canceled-workflow rerun occurred.

## Deliverables and source ownership

| Lane | Exact downstream head | Existing source | Evidence |
|---|---|---|---|
| Combined hosted integration | [d87b5611fa7ac87e05cacdc1e7024a72a3a08470](https://github.com/kvnloo/hermes-agent/commit/d87b5611fa7ac87e05cacdc1e7024a72a3a08470) | Teknium, [upstream106742](https://github.com/NousResearch/hermes-agent/pull/106742), cb8d6920549ebe9d31f69f187d30b356b5639eed | Combined143PASS; matched baseline142PASS/1FAIL; independent143PASS |
| Gemini active-read assessment | [1d14c6a926812d421b579560207a6c192ce1bf5a](https://github.com/kvnloo/hermes-agent/commit/1d14c6a926812d421b579560207a6c192ce1bf5a) | Liuzikaii/KaiKai, [upstream125416](https://github.com/NousResearch/hermes-agent/pull/125416), 091ad151caaac29930cfeedfd85e33e1d548c14f; downstream parent20392f057d2a10624ed65e8fa758f93f4b78c0db | Same1 case PASS on both sources; independent1PASS; no defect established |
| Actual TTS hook consumer | [180f79282bd6bafe62f9654c85b68dd1522b0b84](https://github.com/kvnloo/hermes-agent/commit/180f79282bd6bafe62f9654c85b68dd1522b0b84) | Detail app correction, [fork58](https://github.com/kvnloo/hermes-agent/pull/58), 8c7c49403574f045429bc50086fdd7ccd528d584 | 17PASS including2 new; independent10PASS including those2; typecheck PASS |
| Weather fixture repair | [1c4098c6327bce57cb99be29b4a1edc35f7868ef](https://github.com/kvnloo/hermes-agent/commit/1c4098c6327bce57cb99be29b4a1edc35f7868ef) | Detail app correction, [fork66](https://github.com/kvnloo/hermes-agent/pull/66), 9bfd2958edea8e24970e4e0de187592f0c3149a3 | 7PASS independently;2 existing cases repaired; typecheck PASS |
| Modal cleanup consumer | [f30fb396055d5410eccda4d2cebaa44b1200dd75](https://github.com/kvnloo/hermes-agent/commit/f30fb396055d5410eccda4d2cebaa44b1200dd75) | Liuzikaii/KaiKai, [upstream125354](https://github.com/NousResearch/hermes-agent/pull/125354), 00cf303ca5fca3f353d27b47284c52072d577cf0 | New1PASS, exact parent1FAIL, independent1PASS |

Source PRs/carriers were refreshed OPEN at these exact heads before publication. Original human credit is preserved: **Teknium and David Dudok de Wit** for hosted/checkpoint work; **Liuzikaii and kshitijk4poor** for Gemini source/wrapper work; **Teknium and ishuowang** for underlying lease/voice infrastructure; **Vitor Cepeda Lopes** for the weather API migration; **Liuzikaii** for Modal cancellation. Detail app authored the existing fork58/fork66 corrections. Codex authored the new tests/fixture edits and preserved the existing Codex-authored hosted changes in a combined tree. No ownership takeover is implied.

## Combined integration matrix

Published siblings89cbd9a93c4f27453f0697524069b13bb0b2b2ec and8208ce0ac70431ce4fecad42421d0e7b1ce65e17 share cb8d692 as source. The combined head is a clean cherry-pick of8208 onto89, not a merge or rewrite of either original ref. The entire three-path diff from source was verified byte-for-byte against the published siblings: checkpoint production, activity checkpoint tests, retry consumer tests. No conflict resolution or new implementation was needed.

Both sources used identical final test bytes. Baseline is the whole cb8d692 source with only the two published test files overlaid.

| Suite | Baseline | Combined |
|---|---:|---:|
| hosted_room_discussion |46PASS|46PASS|
| hosted_room_driver |44PASS|44PASS|
| hosted_room_driver_runtime |41PASS|41PASS|
| hosted_room_policy_upgrade |8PASS|8PASS|
| hosted_room_retry_consumer |2PASS|2PASS|
| hosted_room_activity_checkpoint |1PASS/1FAIL|2PASS|

The single baseline failure is the already-known stale same-thread activity removing a newer pending discussion. **139 inherited cases plus4 previously published cases; zero new unique tests.** Independent canonical execution repeated all143 on the committed union. The earlier two-case overlay is not relabeled as this broader matrix. This proves bounded compatibility at in-process SQLite/runtime/fake-RPC boundaries, not native providers, cross-process restart, current-main integration, whole-PR readiness or repair of already-erased current-schema checkpoint rows.

## Consumer findings and controls

**Gemini assessment.** The actual auxiliary aggregate task is canceled while an event confirms that a synchronous HTTPX body read is active on a worker. Consumer cancellation returns first; the body remains open and reading. Explicit finite read release then closes it exactly once, outside the active read, and the client remains reusable. The same test passes on whole original091ad151 and on20392f/new test head. There is no RED result or demonstrated contract violation: existing cleanup is best-effort and does not promise synchronous-thread interruption. This does not qualify permanently stalled reads, forced thread termination, wall-clock resource bounds or other Python implementations. MockTransport uses no network; the finite read and cleanup release are bounded.

**TTS actual hook.** Two added React consumers mount real useComposerVoice under main/tile contexts and use the real serialized/deduplicating syncTtsLease queue. They exercise owner start, idle sibling mount/unmount, main-owner End and tile-owner unmount. Existing eight cross-composer tests copied the ownership effects; these new cases reach the production hook. Audio engines and setTtsLease IPC are substituted. Exact parent54bc5e509c985f37265c3d416bd2c64b10fc77ba hook-file substitution makes both fail on an unwanted idle-sibling lease=false. This is a parent-file control; failures precede final owner-End/unmount assertions, which are positive evidence only. Restored17 includes2 new plus15 existing; independent10 includes2 new plus8 existing. No backend model eviction, microphone/native audio, real IPC, simultaneous active-owner or broader profile-handoff claim.

**Weather fixtures.** The two committed race tests still modeled wttr.in, while source uses Open-Meteo geocoding then forecast. At unchanged source the old fixtures give2FAIL/5PASS. Repaired fixtures follow both actual fetch phases through real launchWidget, report parsing and store updates. The same seven cases then pass. Substituting the exact pre-epoch parent54bc5e5 weather.tsx gives2FAIL/5PASS for intended stale-Paris result and stale rejection; restoring source gives7PASS. This is a production-file control, not whole-parent qualification. Production is unchanged; no new cases or network requests. Typecheck passed; lint/formatter executables were unavailable, so those checks are NOT_RUN. This qualifies store/host consumer races, not rendered cards, live API compatibility or the entire TUI.

**Modal cleanup.** A finite fake SDK holds stdout reading inside real _modal_bulk_download. The real worker timeout is shortened for the test; the existing destination remains unchanged. Actual ModalEnvironment.cleanup terminates the fake sandbox, observes the canceled local read released by return, clears references and stops the worker with no pending continuation. Whole exact parent8c9fe964009096e46f44292d036c1e0ac33c3026 plus identical new test fails because the local read remains unreleased after cleanup. Test-finally drains leftover baseline tasks only after assertions. This adds one consumer case for the existing cancellation fix; the five historical upload tests were not relabeled as new evidence. No Modal cloud call, remote-operation rollback, persistent snapshot, cancellation-resistant coroutine, generic worker-shutdown or whole-PR guarantee.

## Reproduction

Use each exact head in an isolated checkout with its matching repository dependencies. Python checks used the prepared PM CPython3.14.7 interpreter via HERMES_PYTHON and HERMES_TEST_FILE_RETRIES=0. No provider credentials are needed.

- Combined: `bash scripts/run_tests.sh tests/gateway/test_hosted_room_discussion.py tests/gateway/test_hosted_room_driver.py tests/tui_gateway/test_hosted_room_driver_runtime.py tests/tui_gateway/test_hosted_room_policy_upgrade.py tests/gateway/test_hosted_room_retry_consumer.py tests/gateway/test_hosted_room_activity_checkpoint.py`.
- Gemini: `bash scripts/run_tests.sh tests/agent/test_gemini_pending_read_cancellation.py`.
- TTS, from apps/desktop: `npm run test:ui -- src/app/chat/composer/hooks/use-composer-voice.lease.test.tsx src/lib/tts-lease-cross-composer.test.tsx src/lib/tts-lease.test.ts`; `npm run typecheck`.
- Weather, from ui-tui: `npm test -- src/__tests__/weatherApp.test.ts`; `npm run typecheck`.
- Modal: `bash scripts/run_tests.sh tests/tools/test_modal_timeout_cleanup_consumer.py`.

Detailed source/test bindings and independent logs remain in the local evidence package. This public receipt contains no raw logs, credentials or private findings. publication-map.json records exact branch/parent/tree identities and observed CI. #417's owner-disposition decision and Library authorization hold remain unchanged; no retries or blanket promotion authority are inferred.
