# Gateway override selection through whole-turn pool recovery

Source parent: composed `0d8d04fca1986cd62fe679ad9f97bb99cbbe63f7`.
Upstream advanced from24b9f0f8 to `20bd00439cfc2e8d6d296f28fba0cdeeb6cdda49`;
the delta is five WhatsApp adapter/bridge/tests/docs files, unrelated to this consumer.
No rebase or production edit is needed to qualify the recorded composed source.

## New evidence

One synthetic consumer now reaches beyond the earlier direct pool call:

1. Real gateway `_resolve_session_agent_runtime` attaches the selected override's pool.
2. Its runtime constructs a real `AIAgent`, which runs a complete conversation.
3. Actual SDK request headers/body at `httpx.Client.send` show synthetic key0 and the
   override model. A synthetic HTTP429 usage-limit response enters normal recovery.
4. Real pool rotation and client rebuilding cause the next successful request to use
   synthetic key1 with the same model and endpoint. A valid Codex SSE response completes.
5. No provider fallback activates, no inference request uses another model/endpoint, and
   the unrelated-model bench remains enforced.

This is **runtime selection → manually constructed AIAgent → whole conversation**.
It does not drive gateway message ingress, real cache leases/reuse, profile A→B→A,
persisted-session restoration, or live Codex/Discord. It is not a live-provider guarantee.

## Why this is distinct

PR132231's tests resolve providers and call the pool directly. Existing
`test_codex_soft_failure_pool_rotation.py` uses a fake agent and mocked credential swap.
The previous batch2 consumer ends at direct pool rotation. This test keeps actual request
assembly, SDK serialization, error classification, pool mutation, client swap and retry
active; only tool enumeration and HTTP transport are synthetic.

All sync HTTP, including metadata/fallback clients, is intercepted before gateway
resolution and AIAgent construction. Async HTTP explicitly raises. The fixture home and
auth rows are synthetic, external login adoption is disabled, and no auth guard is changed.
No provider requests, package installation or paid calls occurred.

## Meaningful negative control

The unchanged consumer passes on the composed source: **1 passed in3.77s**.
Log `/workspace/receipts/batch3-h2-green.log`.

Temporarily replacing only `agent/credential_pool.py` with its pre132231 version from
`40b59b21440c6e9c723c49e4f74dfbaf019b455d` makes it fail: **1 failed in2.76s**.
Pool attachment still succeeds; quota rotation finds no available entry and activates
the fallback. The valid synthetic fallback SSE completes the turn with `Fallback answered`,
so the failure is the desired response/route contract, not a parser crash.
Log `/workspace/receipts/batch3-h2-negative.log`; exact mutation
`/workspace/receipts/batch3-h2-negative.patch` (retained locally).

The negative-control source was restored in a `finally` block. `git diff --exit-code HEAD
-- agent/credential_pool.py` confirms original composed production source is unchanged.

Both used the canonical runner, installed interpreter, whole `/var/tmp` write grant:

```sh
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python scripts/run_tests.sh -j 2 tests/gateway/test_override_pool_turn_recovery.py --file-retries 0 --file-timeout 45
```

Initial fixture attempt failed after a successful real rotation because its Codex SSE
omitted `response.output_item.done` and its fallback supplied JSON to a streaming client.
That is **fixture failure, not product evidence**. It was corrected before the green and
negative-control pair above. Initial log retained as `/workspace/receipts/batch3-h2-first.log`.

## Ownership and review

No new production implementation. Rotation remains **banozz0** PR132231 original
`2a91d03d81a4962ca6f159fdb06b3feaf5c4223a`, preserved ancestor
`a39e56cfdc7616da0dcdfd759efcfd4ba3f8e021`; PR remains open at that exact original head.
The normal rotation line also overlaps **skyeyesec333** PR130423
`c3f7067fa1d26785b17d71b1277f05d34e164a12`. This consumer does not choose which carrier lands
or claim issue132232's entire acceptance complete.

H4 independently reviewed test, corrected green, negative control and restored source:
no blocking finding within declared scope. Receipt `/workspace/receipts/batch3-h4-review.md`.
Fatal-error Ruff and whitespace checks pass. Hosted CI **NOT RUN**. No upstream writes or
publication. Final committed-source test result is recorded in the parent delivery receipt after the exact final gate.

Consumer: [test_override_pool_turn_recovery.py](../../tests/gateway/test_override_pool_turn_recovery.py).
Execution logs referenced above are retained locally and not bundled.
