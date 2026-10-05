# HOLD: model-only channel selection in the parked pool composition

Current main: `802e0b1daebad8a60da496db1a070fe13ddc45bd`.
Composition before this evidence commit: `8641ba0d9972b55fcdc5a589af374af92f426769`.
This integrates the parked gateway attachment `40b59b21440c6e9c723c49e4f74dfbaf019b455d`
and banozz0's unchanged PR [#132231](https://github.com/NousResearch/hermes-agent/pull/132231)
head `2a91d03d81a4962ca6f159fdb06b3feaf5c4223a`, preserving author metadata and cherry-pick provenance.
The original PR remains open at that head when checked on 2026-10-05.
Credit: Enough1122's October 4 review identified default-model selection preceding channel overrides;
this is a consumer qualification of that concern, not a competing implementation.

Run the same test on either source with the existing test interpreter:

```sh
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python scripts/run_tests.sh -j 2 tests/gateway/test_channel_override_pool_selection.py --file-retries 0
```

| Source | Model-only channel | Explicit-provider channel |
| --- | --- | --- |
| Current main plus this test | PASS | PASS |
| Parked composition plus this test | FAIL | PASS |

The synthetic first seat is cooled for `channel-model` but available for `default-model`.
The second seat is eligible for both. The real gateway resolver returns `channel-model`
with the first seat's key for a model-only override on the composition. Real pool selection
for the returned model correctly chooses the second seat. The returned key string is
captured before the eligibility oracle calls `select`; that call cannot rewrite the witness.

`gateway/run_turn.py` resolves the runtime before applying the channel model. An explicit
channel provider triggers a second resolution with the target model; a model-only override
does not. The owner change makes the first resolution model-scoped to the configured default.
The parked attachment change covers named session overrides, not this later channel path.

Keep this composition parked until the owner establishes eligibility for the final channel
model. The failing test is intentional negative evidence and is not marked xfail.
Independent review by the CLI lane found no blocking concern in the proof. Existing direct
rotation/default-session turn proofs retain their narrow scope but do not cover this channel.

All config and credential values are synthetic temporary fixtures; external login adoption
is disabled and HTTP sends are rejected. This establishes runtime-selection mismatch only:
no live Discord ingress, HTTP/retry behavior, cache reuse, delegated lease, or provider claims.
Hosted CI was not run. No owner implementation or policy was changed for this proof.
