# Preserving-turn renderer reuse: evidence only

Reviewed source: `6e3282b24700582123d15eecda334db1bd9add1e` in
[NousResearch/hermes-agent#126167](https://github.com/NousResearch/hermes-agent/pull/126167).
This branch contains a stronger test and its receipts, **not a production repair**.
Its two sentinel failures are intentional evidence of the unchanged source.
JoaoMarcos44 retains implementation ownership. Coordination:
[existing card #485](https://github.com/kvnloo/hermes-agent/issues/485#issuecomment-6170432053).

## Result

The real handler invokes the renderer again on an unchanged-config preserving turn.
Cumulative renderer calls across human → synthetic → human are **[1, 2, 2]**,
versus the documented reuse contract **[1, 1, 1]**.

The normal renderer's output stays equal in this fixture, explaining why the existing
equality-only control passes. An explicitly injected per-render marker demonstrates
that renderer-independent byte stability is lost: context bytes, combined ephemeral
prompt bytes and the snapshot passed to the mocked store follow **A → B → B**.
This is not evidence of naturally nondeterministic production output.

| Canonical run | Result | Interpretation |
|---|---|---|
| Original unchanged-config + changed-home controls | 2 passed, 0 failed | Existing controls pass at the source head |
| Stronger unchanged-config spy and injected-marker cases + unchanged changed-home control | 1 passed, 2 failed, 28 deselected | Both reuse sentinels fail; changed-home behavior remains green |

These are two runs with overlapping coverage, not five distinct passing/failing tests.
Each used one worker and zero file retries. No production file was edited, no repair
was applied, and no RED-to-GREEN repair result is claimed.

## Requirement, mechanism and reachability

- [Root contract](https://github.com/NousResearch/hermes-agent/blob/6e3282b24700582123d15eecda334db1bd9add1e/AGENTS.md): per-conversation prompt-cache stability is an invariant.
- [Pin helper contract and defect](https://github.com/NousResearch/hermes-agent/blob/6e3282b24700582123d15eecda334db1bd9add1e/gateway/run_agent_cache.py#L713-L752): verbatim reuse on a key hit is explicitly intended to tolerate renderer nondeterminism. Line 743 clears the existing pin before the key-hit comparison.
- [Existing identity test](https://github.com/NousResearch/hermes-agent/blob/6e3282b24700582123d15eecda334db1bd9add1e/tests/gateway/test_prompt_tail_freeze.py#L180-L188): ordinary key hits already assert identical string object reuse for this purpose.
- [Handler wiring](https://github.com/NousResearch/hermes-agent/blob/6e3282b24700582123d15eecda334db1bd9add1e/gateway/run_turn.py#L2056-L2073): real `_handle_message_with_agent` calls `_hmwa_prepare_turn`, which invokes the pin helper with the effective preservation decision and authoritative origin.

The sentinel extends the existing unchanged-config test. It wraps the actual module-global
renderer read in `gateway.run_agent_cache`, retaining the real renderer underneath. All
three events traverse the real handler before assertions. The initial snapshot is deep-copied.
The existing changed-home test is untouched.

The source fix was not attempted in this pass. In particular, neither privacy-policy
invalidation nor the legitimate `/sethome` refresh was removed to obtain a green result.

## Evidence boundary

Observed: renderer invocation counts; context input delivered to the captured `_run_agent`;
the real `TurnRunner` ephemeral combiner; snapshots submitted through the real pin-persistence
method to the harness's mocked store. The Python audit guard observed **0 socket/DNS attempts**
in the sentinel run. The model/turn executor is stubbed by the existing harness.

Not established: actual database writes or store no-op behavior; live delivery; provider cache
hits, billing or performance; naturally varying production renderer bytes; eviction/cold-start
closure; privacy-policy transitions; queued-drain coverage; a full-suite or hosted-CI pass.
The audit guard is Python-level instrumentation, not OS-wide network capture.

Preserve Austin Pickett's separate [243-pass report](https://github.com/NousResearch/hermes-agent/pull/126167#issuecomment-6169880649), including independent re-verification of JoaoMarcos44's admission-order and stop-generation fixes. This narrow finding does not retract those origin-supplied positives. Hosted CI approval and maintainer review remain separate gates. No origin comment, review or implementation change was made by this pass.

## Reproduce

Use Python 3.14 and the repository's documented PM-built dev/test environment. From this
evidence checkout, set `HERMES_PYTHON` to that interpreter and run:

```bash
bash evidence/pin_reuse_20261014/replay.sh
```

Expected result at the reviewed source: exit 1, 1 passed / 2 failed. The generated runner
output includes a bare-pytest hint; use the canonical replay script instead.

To reproduce the original controls, use a separate pristine checkout of the exact source head,
with the same guard plugin, and run the same two test-name selectors through
`scripts/run_tests.sh`. The original controls passed before the test modification recorded here.

## Runtime and provenance

A fresh PM dev/test environment was built offline from the exact source lock, using already
present verified Python 3.14.7 and uv 0.12.3 artifacts and a copied package cache. The supported
offline sequence was `pm.build_env --manager-runtime --source ./pm --offline` followed by
the resulting manager interpreter running `pm.build_env --source . --group dev --group test
--offline`, each with fresh output directories and explicit interpreter/cache paths.

The first fresh-runtime setup failed while attempting a Python download because DNS could
not resolve the official URLs. That failed log is retained. There was no policy denial and
the failed network setup was not invoked again after its built-in retries completed. The subsequent offline manager and test builds
succeeded without raw pip/uv installation or protection bypasses.

`provenance.json` records manifest hashes, interpreter version, installed package/version
inventory and exact-checkout import/editable binding. Every installed distribution/version
matches the lock after standard package-name normalization. A metadata-check helper initially
selected the checkout's egg-info instead of site-packages and then failed to normalize
`ruamel.yaml` to `ruamel-yaml`; both bookkeeping issues were corrected without altering the
environment. The final provenance check passed.

Production files remained byte-identical to the reviewed source. Pinned Ruff 0.15.10 and
`git diff --check` passed. Peak measured task disk use before packaging was about 1.23 GiB,
within the 3 GiB allowance. Logs replace the sandbox's absolute root with `<SANDBOX>`;
no secrets, user data or provider responses are included.

AI assistance: prepared by ayo using OpenAI tools; a separate read-only reviewer critically
examined the test, source, provenance and receipts. See `independent-review.md`.
