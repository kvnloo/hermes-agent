# Shadow evaluation gate

`evaluate_shadow.py` evaluates complete z0 DecisionBackend probability
distributions against the independent Hermes lifecycle outcome.

Reported today:

- Brier score;
- base-rate Brier;
- Brier improvement;
- log loss;
- accuracy at 0.5 (diagnostic only);
- simple calibration bins;
- mean backend latency.

It deliberately emits `promotion_ready: false`.  Promotion requires a later
frozen/grouped evaluation with enough evidence, safety gates and a canary.

Example:

```bash
python lab/z0_hermes_observer/evaluate_shadow.py scored.jsonl \
  --output report.json
```

The first useful comparison is deterministic base rate vs each available
DecisionBackend on the exact same frozen receipt cohort.
