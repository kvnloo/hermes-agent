# Independent review of the downstream partial sibling claim packet

Reviewed 2026-10-11 by OpenAI Codex as the independently delegated critic. Brian Le (0xble) owns PR #133834 and its off-loop/cancellation implementation. This review contributes test/report evidence only; it does not claim that ownership, include a production fix, or establish a separate original reporter.

## Verdict

The packet correctly demonstrates an inherited partial-acquisition cleanup gap under an injected ordinary exception. Fresh canonical-runner executions at the exact head and base both produced **2 passed, 1 failed**, exit **1**, with the same proposed-refund assertion failing. The real first sibling claim commits, spends one attempt, and remains leased when the second claim raises before delivery starts. The packet is suitable as a bounded diagnostic contribution to the owner's work, with the qualifications below. It does not establish a PR-introduced regression, permanent loss of the stored result, an existing arbitrary-error refund contract, or guaranteed notification recovery when the lease expires.

The original unavailable fixture/overlay was neither recovered nor rerun. I did not independently refresh remote PR metadata, discussion, or duplicate-search results; those portions remain the parent report's bounded historical evidence.

## Independent execution

Verified checkout HEADs:

- `<owner-checkout>`: `985238fe8778dcfb05b2027a02490b11aa6ead78`.
- `<base-checkout>`: `fd74e718a078ce934c6172aef9bafd0067ca18a7`.

Read the applicable root, gateway, tests, and tools `AGENTS.md` files and the relevant contribution/setup/test sections of `CONTRIBUTING.md`. These instruction files and the canonical runner are byte-identical between the snapshots. Used the existing isolated PM-built interpreter without changing its packages or rebuilding an environment.

Historical commands below use redacted path placeholders; use the README for executable reproduction commands. Executed these commands sequentially, in the indicated working directories, with additional filesystem write permission limited to the runner scratch root `<runner-scratch>`:

```sh
# Working directory: <owner-checkout>
HERMES_PYTHON=<test-environment>/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/gateway/test_partial_sibling_claims.py -v > logs/critic-head.log 2>&1

# Working directory: <base-checkout>
HERMES_PYTHON=<test-environment>/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/gateway/test_partial_sibling_claims.py -v > logs/critic-base.log 2>&1
```

| Snapshot | Result | Exit | Pytest duration | Full log |
|---|---|---|---|---|
| Owner head | 2 passed, 1 failed; no collection errors/skips | 1 | 1.07s | `logs/critic-head.log` |
| Base | 2 passed, 1 failed; no collection errors/skips | 1 | 0.85s | `logs/critic-base.log` |

Both used Linux Python 3.14.7, pytest 9.1.1, one file/worker, retries disabled. Both failed only `test_proposed_partial_claim_error_refunds_unadmitted_sibling` at line 101, where the real committed row retained a nonempty gateway batch token and one attempt instead of `(None, None, 0, "pending")`. The characterization/strict-TTL test and successful-handoff/explicit-defer control passed. I also ran `git diff --check` on the head checkout; it passed. No further suite or cross-platform claim is made.

## Source assessment and contract challenge

At the head, `gateway/run_notifications_ledger.py:106–107` builds sibling results with a list comprehension. Each `tools/async_delegation.py:438–451` claim uses its own real transaction. If a later claim raises, the callable never returns the accumulated earlier tokens. `claim_off_loop` reaches neither its successful handoff nor `release(result)` because the exception escapes `result = claim()` at line 79; its exception handler handles cancellation, not an ordinary `RuntimeError`.

The real group caller awaits that helper at `gateway/run_notifications.py:1821`, before its delivery/cancellation-cleanup block at 1839. Thus this fixture exercises the actual caller and exact owner helper, rather than an extracted imitation. The base's synchronous sibling loop at `gateway/run_notifications.py:1812–1818` also permits a later exception to escape with the earlier committed sibling still held. The independent base result supports the report's inherited-behavior classification.

Refunding the first acquired sibling is a reasonable proposed policy because its notification was never handed to delivery. However, the failing assertion proposes both **lease cleanup** and **attempt refund**; these are distinct choices. `release_completion_delivery` clears the lease while retaining the attempt, whereas `defer_completion_delivery` clears the lease and subtracts one attempt. Existing documentation distinguishes refused admission/cancellation from actual delivery errors, whose attempts retain a bounded retry policy. The cancellation-focused history (`db7bc2497eebd04ed1bb760fc08f8e7d07c61cb9` and the exact head commit, both authored by Brian Le), docstrings, and owner cancellation tests do not by themselves require arbitrary acquisition errors to refund. The parent report labels this correctly as proposed hardening. The injected failure is deterministic fault injection before the second real claim; it does not reproduce a particular live SQLite outage or an ambiguous commit failure.

Any future fix would need to retain ownership of successful partial claims and decide their settlement policy. It should preserve the owner's worker-thread/profile-context and cancellation behavior. This review does not test concurrent cancellation plus an acquisition exception, failures while cleanup itself runs, or a second claim that commits and then raises before returning its token.

## TTL and watcher qualification

The TTL evidence is sound: `_CLAIM_LEASE_S` is 300.0, and reclaim requires `delivery_claimed_at < now - _CLAIM_LEASE_S`. At 10300.0 a claim made at 10000.0 is still ineligible; at 10300.001 it becomes eligible and the successful fresh claim raises attempts from one to two. Expiry changes eligibility when code next tries to claim; it does not automatically clear the row or schedule its notification.

The watcher was **source-traced, not executed**. At head `gateway/run_notifications.py:1936–1944`, its ordinary-exception path requeues the entire group and logs the error without deferring the leaked sibling. On a later successful retry, group code at 1825–1827 skips a sibling whose claim returns `None`; that omitted sibling is not included in the successful batch or the successful-sibling requeue path at 1853–1856. A retry can therefore consume the queue copy while omitting the abandoned leased row. This is a source inference, conditional on retry/admission behavior absent from the fixture.

Consequently, **the lease test does not prove automatic delivery after approximately 300 seconds**. The orphan sweep also excludes rows whose producer is still alive and delegation IDs still recorded in `_offered` (`tools/async_delegation.py:391–393`). Replay records offers at 336–358; this gateway path does not call `return_completion_offer` when skipping a leased sibling. Depending on provenance and later events, another offer/consumer or restart may be needed. Stored result preservation is demonstrated; notification recovery timing and eventual notification delivery are not.

## Fixture validity, self-containment, and corrections

The fixture uses the full canonical schema created by real `SessionDB`, real ledger writers, and an independent reader connection. It verifies the first committed claim before injecting the second-sibling error. Formatting, identity/readiness, and delivery mocks are disclosed and limit the successful control to token handoff plus explicit defer/reclaim. There is no actual adapter acceptance, acknowledgment, model turn, producer spawn, watcher loop, or profile multiplexing proof.

`monkeypatch.setattr(ad.time, "time", ...)` patches the shared standard-library `time` module's wall clock process-wide, not just this module. This can affect schema initialization, logging timestamps, and other imported wall-clock users. It is broader than needed. It does **not materially invalidate this bounded evidence**: the claim comparison uses the deliberately controlled wall clock, commits are independently observed, `asyncio` scheduling uses unmodified monotonic time, and each `asyncio.run` finishes its executor before fixture teardown. The runner isolates the file and `monkeypatch` restores the clock after each test. For a future maintained fixture, replace the `ad.time` binding with a forwarding clock proxy so only this module's wall-clock read changes. No such edit was made here.

The characterization test intentionally asserts the stranded lease/one attempt, while the proposed refund test asserts a cleared lease/zero attempts for the same trigger. They are mutually exclusive expectations. This is a useful diagnostic packet, but it cannot be merged unchanged as an all-green regression suite for a future refund fix; then the characterization would need to be revised or retained separately as historical evidence. The passing defer control is an explicit manual operation and must not be described as automatic cleanup by the caller.

The reviewed parent report is self-contained for the bounded repro: it embeds the exact runnable fixture, source SHAs, official environment/runner instructions, observed assertions, and full owner/base logs. I independently extracted its fixture block and confirmed byte equality with the on-disk file. Its absence-of-old-fixture, AI authorship, owner credit, inherited behavior, proposed-policy, and mocking limits are clear. The necessary editorial strengthening is to distinguish TTL eligibility from automatic notification recovery and identify the incompatible expectations as diagnostic. The parent has agreed to add these qualifications. The report is not a drop-in production fix or independently verified remote-search archive.

No production/fixture edits, commits, pushes, posts, installations, global Git/hook changes, or credential operations were performed. The only new deliverables from this review are this critique and the two fresh logs. No blocker remains for the bounded independent review; external publication remains the parent's responsibility.

## Pre-sanitization SHA-256 provenance

The parent report hash identifies the original pre-review report read at the start, before any parent amendment. Source and fixture hashes match the report's values.

```text
Original pre-review local report (not this public README)
ebfc53073f3043dcb32578a051776d235c0a4d61428e4b67949bca25dbd72561

Both tests/gateway/test_partial_sibling_claims.py, including embedded fixture
2228a9ad026b62d13be4963e5b0acdf5aeefe56dfe7d341b8ec7d4bff10c4007

Head gateway/run_notifications_ledger.py
fb02b4a0a577c98d348b0789bd3772a033dd564121bca220bc082bb65395f89b
Head gateway/run_notifications.py
df66437c59f61742e562868153c0883d2a6910ce1debffd81ee0a4f88faf4964
Base gateway/run_notifications.py
4ac67769b5c4483164117892f574e74c49a8174373a89c514593b0112f68a16f
Both tools/async_delegation.py
208adb7c7a162cf033d2a54b27536b719a4093f76ec4316fecebcfb08f485b9c
Both hermes_state.py
b76fc6af3b7f37ee1de1be62379acb08d56069796eaf3bdf253a480be704e578
Both hermes_state_common.py
b0f89a8b208f178a97057c820df8fa57689826e006fb9345a38320587b0b2bde
Both scripts/run_tests.sh
5d81d729ca0b98f89d5c944d2231eaf2a6190817b099a45f924de0af24ec3aac

logs/critic-head.log
6580533fc1fc8a906d190f1b5c38d0bf7a5f14bfca5937f6c68266e3f6e16c00
logs/critic-base.log
80d84f9d7a12284cca3ef4fc15bd1e24179bb168cf342ae3b868deb4e0be6850
```
