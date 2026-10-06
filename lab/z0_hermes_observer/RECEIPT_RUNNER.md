# Hermes integration receipt + failure-injection runner

Tracking: #322 (parent #318). Shadow observability only.

## Role

Thin experiment envelope that **joins** existing Hermes/z0int receipts by stable
trace identity. It does **not** invent a competing receipt format.

Canonical inputs already owned elsewhere:

- `z0int.hermes_observer_event.v1` (#385)
- `z0int.hermes_shadow_example.v1` (#386)
- `z0int.hermes_shadow_eval.v1` (#387)

Envelope schema id: `z0eval.hermes_stack_experiment.v0` (same as
`lab/evals/hermes-stack-receipts-v0` experiment schema).

## Hard rules

- `execution_completed` never upgrades `verified_success`
- unknown verification stays unknown (`verified_success: null`)
- no observer self-credit (`verified_success=true` requires `verifier_id`)
- replay of the same receipt cannot mint a second physical side effect
- `promotion_ready` stays **false**
- failure injection is offline/attributable; Hermes behavior is unchanged (fail-open unless catalog says fail-closed)

## CLI

```bash
python lab/z0_hermes_observer/receipt_runner.py list-failures

python lab/z0_hermes_observer/receipt_runner.py join \
  ~/.hermes/plugin-data/z0-hermes-observer/events.jsonl \
  --experiment-id exp-1 --arm Z --task-family api.attempt_will_fail \
  --hermes-rev "$(git rev-parse HEAD)" \
  --verified-success unknown \
  --output "$TMPDIR/experiment-receipt.json"

python lab/z0_hermes_observer/receipt_runner.py fail z0int_backend_unavailable
```
