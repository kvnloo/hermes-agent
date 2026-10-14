# Hermes replay admission: independent execution receipt

Classification: FAIL_GAP for the two scoped replay-admission contracts at the tested PR head. This is supplemental test evidence, not a production repair or an origin-readiness statement.

## Provenance and requirement

- Owner PR: [NousResearch/hermes-agent #137566](https://github.com/NousResearch/hermes-agent/pull/137566), implementation by KoNit-K.
- Requirement and reported Telegram incident: [jess-vancap's #137565](https://github.com/NousResearch/hermes-agent/issues/137565). The requested recovery must refuse replay after user-visible streamed output and run only after successful reset into a fresh session.
- Prior source findings: [Kevin's review 5513193633](https://github.com/NousResearch/hermes-agent/pull/137566#pullrequestreview-5513193633). This receipt independently executes the two boundaries rather than reposting the source finding as new.
- Downstream claim: [#499 comment 6167236222](https://github.com/kvnloo/hermes-agent/issues/499#issuecomment-6167236222).
- Tested code: `ca47f821e7f3d308068e7dd807b387dae4f670a6`; PR API base `427d605d4985c2d49a795493ef6c5d66413057d1`. Current origin main at initial qualification was `0e427d788d253630d38a3a51cd76849e73cd6925`; this is not a current-main regression claim.

## Results

Canonical Linux execution on Python 3.14.7, pytest 9.1.1:

- Supplemental suite: 2 failed, 2 passed.
- Three unchanged owner suites: 9 passed.
- Combined: 11 passed, 2 failed. No file retries.
- All 12 `scripts/check --staged --base ca47f821e7f3d308068e7dd807b387dae4f670a6` checks passed; code health reported 0 blocking and 0 advisory findings for the supplemental test delta.

F1: a deterministic model double emitted a partial delta through the real gateway worker/stream consumer. The recording adapter confirmed a send before the model returned a failed, compression-exhausted result without tool messages. The production delivery classifier left `already_sent` unset. The real outer handler then staged the original event for replay. The no-replay assertion failed.

F2: when the reset facade returned `None`, the handler retained the original session entry but still staged the original event for replay. The no-replay assertion failed. The real store's `None` case represents an absent routing entry. This shows staging without a confirmed new session; it does not establish a live lease race, repeated execution against the same context, generic reset-exception replay, or an infinite loop.

Positive controls: clean pre-response exhaustion with a fresh session stages the same event once, preserves the prepared text and captured image path, and keeps later queued input behind it. A second exhaustion on the same event is not queued again. Deferred compression neither resets nor queues. The actual first model input includes a temporary image through production image routing.

## Test boundary

The fixture imports production code and executes `_handle_message_with_agent`, `_run_agent`, the worker, stream consumer, failed-result delivery classification, compression-reset helper and replay gate. Model/platform I/O are deterministic doubles. Preparation, persistence, final response delivery and reset datastore I/O are stubbed. The FIFO arrival is injected after the worker's pending-input drain.

Not proven: live Telegram, actual provider behavior, outer adapter drain, turn-lease release, durable recovery, real reset-store races, end-to-end retry reattachment, or released behavior. Retained staged media paths are not a claim that the next turn's full preparation reattaches them. No production code was changed; no fix or RED-to-GREEN result is claimed.

The actual source also has a supported producer path for F1: `agent/chat_completion_helpers.py` classifies context-overflow after partial delivery into an overflow-terminal stub, and `agent/turn_truncation.py` ends that turn with `failed=True` and `compression_exhausted=True`.

## Reproduction

Use an isolated checkout of the tested owner head plus the frozen supplemental test. Prepare its canonical PM test environment with a disposable HOME/HERMES_HOME/runtime store. Run:

    scripts/run_tests.sh tests/gateway/test_compression_replay_delivery_safety.py tests/gateway/test_compression_exhaustion_replay.py tests/gateway/test_auto_reset_clean_context.py tests/gateway/test_duplicate_user_message.py --file-retries 0 -j 1

Frozen test SHA-256: `837fbb5dd80b5a873da452262d48961608ff3b0caa80214b7ca0c40f0f4644f4`.

Initial bootstrap needed the disposable cache paths made explicit because an inherited uv cache pointed at a read-only home. The canonical setup then completed the Python/application/test environments. Optional Chromium download failed its HTTP Range check; no browser is used by these tests. The first lint invocation could not infer a main merge-base in the shallow owner-branch checkout; the explicit tested-head base above resolved it without changing code or weakening checks.

## Independent verification

An independent canonical rerun of the frozen supplemental test and owner controls reproduced 11 passed / 2 failed. A separate clean detached checkout of the same owner head, without the new test, passed all 9 owner controls plus the 3 existing `tests/agent/test_overflow_partial_terminal.py` cases (12 passed). It remained clean before and after.

The independent review accepted these two scoped admission-gap findings, verified the concrete partial-overflow producer path, and confirmed the fixture does not replace the worker, stream consumer, delivery classifier, reset helper or replay gate. Its limitations are reflected above. This is qualified acceptance of evidence, not approval of a production patch.

See `replay.sh`, `verification.json`, and the adjacent logs. Logs normalize disposable paths and trailing whitespace, and replace the runner's bare-pytest diagnostic with a canonical-runner reminder; unnormalized logs were retained locally and their SHA-256 values are recorded in `verification.json`.

Implementation/report credit remains with KoNit-K and jess-vancap; prior guard findings with Kevin. Supplemental tests and independent execution: OpenAI Codex.
