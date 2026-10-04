# Gateway attachment and model-aware pool rotation composition

Recorded 2026-10-04. Upstream main remained `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925`.
Delivered attachment-only commit: `40b59b21440c6e9c723c49e4f74dfbaf019b455d`.

## Result

The **same two-case synthetic consumer** fails on attachment-only code after successful
gateway resolution: the attached pool exists, but a usage-limit rotation returns `None`.
Adding banozz0's unchanged PR132231 commit makes both cases pass and hands back the second
synthetic account. The unrelated-model bench remains enforced, and provider/key/endpoint
identity survive attachment. Cases cover `_resolve_session_agent_runtime` and
`_apply_session_model_override`; the latter is an override application call, not a real
warm-cache turn.

This adds a composition proof across gateway session attachment and real pool bookkeeping.
It is not another implementation of the already owned rotation fix.

## Owner and source identity

- **banozz0 / banozz**, [PR132231](https://github.com/NousResearch/hermes-agent/pull/132231),
  open at inspected head `2a91d03d81a4962ca6f159fdb06b3feaf5c4223a`, updated
  2026-10-03T14:42:46Z, no comments/reviews. One selected commit, parent
  `44533f11e397b78f2569c41dc0eba9502304dd74`; PR's current base metadata points to
  `7533bd2756b9526b52f527f737420a19e57331d7`.
- Cherry-picked with `-x` onto delivered attachment code as
  `a39e56cfdc7616da0dcdfd759efcfd4ba3f8e021`; original author and author date preserved.
  Stable patch ID of original and cherry-pick both
  `5b55d8699c939efa57bdc80ea3c8086978c44983`. No conflict edits.
- **skyeyesec333 / BALEXANDROS**, overlapping [PR130423](https://github.com/NousResearch/hermes-agent/pull/130423),
  open head `c3f7067fa1d26785b17d71b1277f05d34e164a12`, updated
  2026-10-01T12:45:04Z. Owns the one-line normal rotation reselect fix. PR132231 explicitly
  identifies that overlap and additionally changes initial default-model, unmatched, and
  identity-less rotation. This proof does not adjudicate which carrier should land.
- [Issue132232](https://github.com/NousResearch/hermes-agent/issues/132232) still has no
  comments; its broader acceptance includes actual rotation before provider fallback,
  which this direct-pool probe does not establish.

## Exact verification

Both runs used the same unmodified test file:

```sh
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python scripts/run_tests.sh -j 2 tests/gateway/test_override_pool_rotation_composition.py --file-retries 0
```

Sandbox write grant `/var/tmp`, installed interpreter only; no dependency installation.

- On `40b59b2144`: **2 failed**, both specifically `assert replacement is not None`.
  Workspace log: `/workspace/receipts/batch2-h2-attachment-only-red.log`.
- On `a39e56cfdc`: **2 passed**, 0 failed, 0.9s. Workspace log:
  `/workspace/receipts/batch2-h2-composed-green.log`.
- Probe copy: [composition test](../../tests/gateway/test_override_pool_rotation_composition.py).
- `git diff --check` passed. Hosted CI **NOT RUN**. No unchanged suite reruns.

Synthetic temporary config/auth stores only. `Path.home`, `HOME`, and `HERMES_HOME` are
isolated; profile path deliberately differs from the guarded HOME/.hermes shape. Runtime
auth protections are unchanged. Real provider resolvers and pool persistence execute;
manual fixture rows do not refresh external OAuth accounts. No requests to live providers.

## Remaining composition contracts

1. An actual gateway agent turn must classify a synthetic usage-limit response, swap to the
   replacement credential, and issue its retry before activating provider fallback. This
   probe calls the pool directly after attachment; it cannot establish those steps.
2. Real cache reuse, cached client identity refresh, persisted session restoration and
   profile A→B→A isolation remain untested here. Both owner/source tests and this probe are
   scoped synthetic consumers, not live Discord qualification.
3. Stale/unmatched and identity-less rotation are changed by132231 but not re-proven by
   this test; its exact owner tests cover those separately. Provider endpoint mismatch and
   single-use OAuth refresh retain their existing ownership and guards.

Next useful action: owner-reviewed synthetic whole-turn composition at these exact heads,
or wait for upstream integration and fresh qualification. Do not publish a duplicate
rotation PR or infer issue132232 fully resolved from two green direct-pool cases.

## Workspace/delivery

Isolated branch `evidence/batch2-pool-composition` in `/workspace/lanes/h1`.
Prior published evidence branch remains `a21142e9815e6ea94d58e24a006f44d7af08292e`.
The read-only fetch added upstream auto-followed tags; no existing refs were overwritten
or cleaned up. No upstream writes, PRs, push, merge, deployment, config or secret changes.
Independent H3 review completed: no blocking finding within the declared direct-pool
contract. Reviewer checked exact red/green logs, author preservation, patch identity, and
main recovery forwarding of agent.model. No duplicate reviewer rerun; limitations above
remain. Review receipt: /workspace/receipts/batch2-h3.md.
