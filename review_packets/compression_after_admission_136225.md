# Independent admission-loss regression for PR #136225

This branch is intentional RED evidence, not a production fix or a merge-ready
candidate. Source base: `ab11062e1e9d0f04dbb7794c6d6456f6af60e1b1`.

Credit: helix4u reported the compression-after-admission ordering and confirmed
the receiving-turn resolver failure. Yoniebans owns PR #136225 and its repair;
that carrier retains stepanov1975 and wodesiku's contributions. Kevin requested
this independent qualification. The test and review were prepared by dot.

Reports:
- https://github.com/NousResearch/hermes-agent/pull/136225#issuecomment-6102209591
- https://github.com/NousResearch/hermes-agent/pull/136225#issuecomment-6102787415

## Executed result

Python 3.12.14, Linux. The repository test runner executes real SessionStore,
SQLite durable delegation records, BasePlatformAdapter busy-queue admission,
and `_hmwa_resolve_session`. External transport is replaced by a no-I/O adapter;
one asynchronous owner-row read is fault-injected after admission.

The accepted completion is marked delivered, then session A compresses to B.
A transient owner-row read failure causes the receiving resolver to return
None while the durable record remains delivered. Pending-only recovery cannot
automatically replay that row. The stored result remains queryable; this is
automatic receiving-turn delivery loss, not deletion of stored data.

Independent result: 12 PASS / 1 intentional FAIL, file retries disabled.
- Seven existing owner-retry tests pass.
- Five new controls pass: healthy compression, reset boundary, switched-session
  boundary, and unchanged route with and without the injected read failure.
- Only compression after admission plus the owner-row fault fails the no-loss
  assertion.

Portable reproduction from this branch, using the repository's configured test
interpreter (the executed run selected an existing Python 3.12.14 environment):

```sh
HERMES_TEST_WORKERS=1 HERMES_TEST_FILE_RETRIES=0 \
  scripts/run_tests.sh tests/gateway/test_completion_owner_retry.py \
  tests/gateway/test_completion_admission_compression_race.py -q
```

Expected exit code on this unfixed source: 1. An initial independent run took
4.9 seconds. This is a test receipt, not a latency benchmark.

Final test SHA-256:
`d6c9f6fc6f430dcaa71346be289f45cfc3f80abc2b20a19e4e957919c8f2df15`.
Retained private runner-log SHA-256:
`93faff106e7bd1a705e2345e9af4d2f27b729f0c783d9a609b5d8a9fcdff85c7`.
Raw environment-specific logs are not included in this public packet.

## Scope and limitations

No model invocation, live Telegram service, full gateway startup, or full
background-drain end-to-end test was run. Reset and switch controls use the
actual SessionStore transition APIs, not slash-command parsing. The separate
unchanged stale-parent P versus proven tip T scenario is not this reproduction.

The injected read fault spans one resolver invocation and the test observes
exactly one failed read. A future bounded-retry implementation may require
changing the injection to fail once; this test does not prescribe a repair.
Do not weaken user reset/resume boundaries to accept unrelated completions.

The original local test commit `95fc8b144d201adba23a82f0e3093778b241b1b5`
is preserved. Independent review removed one unused import; no production
source changed. Pinned Ruff 0.15.10 and code-health checks passed on the cleaned
test. Hosted CI and full-suite acceptance are not claimed.
