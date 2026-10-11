<!-- oss-factory:v1
{"id":"20261011-hermes-133834-partial-claims","kind":"result","project":"hermes-agent","from":"chatgpt","to":["factory"],"status":"done","civ":{"city_id":"oss:hermes-agent"},"origin_url":"https://github.com/NousResearch/hermes-agent/pull/133834","dedupe_key":"NousResearch/hermes-agent#133834","branch":"evidence/hermes-133834-partial-claims-20261011"}
-->

# LIMITED: inherited partial sibling claim behavior

This is a downstream-only diagnostic packet for [PR #133834](https://github.com/NousResearch/hermes-agent/pull/133834), owned by Brian Le (0xble). OpenAI Codex prepared the new fixture, report and sanitization at Kevin's instruction; a separately delegated xhigh critic independently inspected and reran it. No invented DCO signoff or claim of human test authorship is made. No separate original reporter for this partial-claim behavior was found. The prior unavailable fixture/overlay was neither recovered nor rerun.

Classification: **LIMITED**. The synthetic desired-refund assertion is a newly proposed policy test, not evidence of a project requirement. This packet contains no production fix and belongs outside the ordinary test suite. The Python filename does not match ordinary pytest test discovery; manually copy it only into disposable checkouts when reproducing.

## Behavior evidence

Exact source revisions:

- Owner head: `985238fe8778dcfb05b2027a02490b11aa6ead78`.
- PR base: `fd74e718a078ce934c6172aef9bafd0067ca18a7`.

Refreshed before publication on 2026-10-11 at approximately 06:58 UTC: PR open/draft, unchanged owner head/base, complete discussion empty. A direct owner-branch ref read matched the head. All-state PR searches for `claim_siblings_off_loop`, `partial sibling`, and `claim_event_delivery` found no equivalent arbitrary-error sibling refund contribution among returned candidates. Earlier adjacent inspection covered #132827 (provenance/routing), #104235 (unroutable-origin terminal disposition), #103021 (readiness), and #105640 (individual state transitions). These are bounded searches, not proof that no competing work exists. The separate repeated-Retry ACK owner remains untouched.

The fixture creates full canonical schema through real SessionDB and inserts a primary and two completed pending siblings with result/event JSON. It calls the actual group caller, which reaches the exact owner helper. Injected RuntimeError occurs before the second sibling's real claim, after an independent SQLite connection verifies that the first real claim committed. No reduced schema, extracted helper or Python overlay is used.

| Run | Results | Exit | Pytest duration |
|---|---|---|---|
| Initial final owner-head run | 2 PASS / 1 FAIL | 1 | 0.78s |
| Initial final base run | 2 PASS / 1 FAIL | 1 | 0.71s |
| Independent owner-head rerun | 2 PASS / 1 FAIL | 1 | 1.07s |
| Independent base rerun | 2 PASS / 1 FAIL | 1 | 0.85s |

All runs used Linux Python 3.14.7, pytest 9.1.1, one file/worker, zero retries, no skips or collection errors. The failed case was solely `test_proposed_partial_claim_error_refunds_unadmitted_sibling`. Scoped Ruff and `git diff --check` passed for the measured fixture. No full-suite or platform-wide result is claimed.

Observed controls:

- Primary and second sibling remain pending, unclaimed, with zero attempts. First sibling remains pending with a committed lease, claimed_at=10000.0, attempts=1, and intact queryable result JSON. Delivery was never awaited.
- Immediate reclaim and reclaim at exactly 300 seconds fail. Reclaim at 300.001 seconds succeeds and increments attempts to two.
- Successful acquisition returns both sibling tokens to the mocked delivery seam. Explicit manual defer clears the lease and refunds the attempt; immediate fresh claim succeeds with one attempt.

This is inherited temporary lease delay and an extra spent attempt, reproduced on the base's synchronous loop too. It is not PR-introduced and does not demonstrate permanent result loss.

## Requirement evidence and semantic risks

**Arbitrary-error refund requirements remain unvalidated.** No documented contract, maintainer request/agreement, or live supported-path failure independently establishes that these acquisition exceptions must refund. Cancellation-refund tests alone do not establish arbitrary-error policy. Release (clear lease, keep attempt) and defer (clear lease, refund attempt) are distinct choices. The synthetic FAIL proves only that current code does not implement the proposed refund expectation.

The error characterization asserts retained ownership; the proposed-policy test asserts cleared ownership for the same trigger. These intentionally conflicting assertions form a diagnostic packet, not a future all-green suite. A maintained regression would need to select the validated contract. A future cleanup change would also need to retain each partial token, preserve profile/cancellation semantics, handle cleanup failures, and distinguish an ambiguous claim that commits then raises. None of that implementation is supplied here.

## Caller impact and boundaries

Owner helper: `gateway/run_notifications_ledger.py:101–114`; actual claim writes: `tools/async_delegation.py:438–451`; defer: `495–501`. Group caller awaits sibling acquisition at `gateway/run_notifications.py:1821`, before delivery cleanup at `1839–1852`. The fixture executes this actual caller and proves the exception escapes before delivery starts. The equivalent base loop begins around `1812`.

Watcher behavior is source-traced, not executed: owner lines `1936–1944` catch ordinary exceptions, requeue the group and log without deferring the acquired sibling. A later successful retry skips claim=None siblings at `1825–1827` and can omit the leased sibling's queue copy. The orphan sweep excludes live producers and IDs in `_offered` (`tools/async_delegation.py:391–393`); restored offers are tracked at `336–358`, and this gateway path does not return the skipped offer. Thus TTL expiry proves subsequent claim eligibility, not automatic notification recovery or a delivery guarantee within 300 seconds.

Formatting, identity/readiness and delivery are mocked at real caller seams. The successful control proves token handoff and manual defer, not adapter acceptance or acknowledgment. No deployed gateway, watcher execution, model turn, primary admission, live child spawn, profile multiplexing or concurrent cancellation is established. The process-wide wall-clock patch is broader than ideal but does not materially invalidate the bounded SQL/commit/TTL evidence; a future maintained fixture should narrow that seam.

See [independent critique](CRITIQUE.md) and the four [logs](logs/). These public logs replace private absolute paths, interpreter paths, object addresses and ephemeral runner/PID/UUID portions of generated claim IDs with named placeholders; trailing whitespace is stripped. Test outcomes, assertion values, counts, timestamps, durations and source identities are unchanged. The executable fixture is byte-identical to the measured fixture. Original hashes in the critique identify pre-sanitization provenance; [SHA256SUMS](SHA256SUMS) covers this public packet.

## Reproduce in disposable worktrees

From a clone containing this evidence branch, retain the packet path and create new sibling worktrees. Use fresh paths; do not overwrite existing worktrees or environments. The copy occurs only in those disposable worktrees, not on this evidence branch.

```sh
packet_dir="$PWD/evidence/hermes-133834-partial-claims"
git fetch https://github.com/0xble/hermes-agent.git 985238fe8778dcfb05b2027a02490b11aa6ead78
git fetch https://github.com/NousResearch/hermes-agent.git fd74e718a078ce934c6172aef9bafd0067ca18a7
git worktree add --detach ../partial-claims-owner 985238fe8778dcfb05b2027a02490b11aa6ead78
git worktree add --detach ../partial-claims-base fd74e718a078ce934c6172aef9bafd0067ca18a7
cp "$packet_dir/diagnostic_partial_sibling_claims.py" ../partial-claims-owner/tests/gateway/test_partial_sibling_claims.py
cp "$packet_dir/diagnostic_partial_sibling_claims.py" ../partial-claims-base/tests/gateway/test_partial_sibling_claims.py
cd ../partial-claims-owner
HERMES_HOME="$PWD/../partial-claims-home" HERMES_RUNTIME_DIR="$PWD/../partial-claims-runtime" python -m pm.build_env --source . --out "$PWD/../partial-claims-env" --group dev --group test
HERMES_PYTHON="$PWD/../partial-claims-env/bin/python" HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/gateway/test_partial_sibling_claims.py -v
# Expected exit 1: 2 passed, 1 proposed-policy failure.
cd ../partial-claims-base
HERMES_PYTHON="$PWD/../partial-claims-env/bin/python" HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/gateway/test_partial_sibling_claims.py -v
# Expected exit 1: same assertion and 2 passing controls.
```

A restricted executor may need write permission to the canonical runner's scratch directory. Official PM provisioned the measured isolated test environment without dependency-manifest changes. Read checkout contribution/setup instructions before reproducing; do not run this intentional policy failure as a required ordinary test gate.

The fork is evidence/coordination only. No upstream proposal, comment or PR is authorized by this packet, and no upstream action was taken. Project routing is `hermes-agent`, coordination repository `kvnloo/hermes-agent`, city `oss:hermes-agent`, as registered in the canonical factory control plane.
