# First bounded z0 shadow question

This slice turns the observer spool into an independently labeled z0
DecisionBackend dataset.

Question: **will this physical main-loop provider attempt fail?**

The label comes only from Hermes lifecycle facts:

- `post_api_request` → false
- `api_request_error` → true

No model/judge labels itself.

Generate examples without loading a backend:

```bash
python lab/z0_hermes_observer/shadow_api_failure.py \
  ~/.hermes/plugin-data/z0-hermes-observer/events.jsonl \
  --output "$TMPDIR/api-failure-examples.jsonl"
```

Score the same frozen examples with a real z0int backend:

```bash
python lab/z0_hermes_observer/shadow_api_failure.py events.jsonl \
  --output scored.jsonl \
  --z0int-root ../z0intelligence \
  --backend laya_421m
```

Repeat with deterministic/rules, Laya, Decider, NanoJev/OpenJev where available.
Preserve complete probability distributions.  This is shadow-only: predictions
must not alter retries, provider routing, or model choice.

Next measurement: Brier/log loss, calibration, latency, coverage, and paired
comparison against a trivial base-rate predictor.

## Phase 1 join fields

Every joined example includes:

- `request.questions[0].legal_actions`: deterministic `[false, true]`
- `execution_completed`: Hermes finished the attempt lifecycle (`post_api_request` or `api_request_error`)
- `verified_outcome`: independent will_fail label (`api_request_error` → true)
- `verified_success`: always false in this offline join (lifecycle completion is not task/agent success verification); **never** an alias of `execution_completed`

Do not collapse execution completion into verified success.
