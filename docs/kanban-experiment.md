# Check an opt-in Kanban throughput experiment

Use the checker to evaluate one predeclared baseline/candidate comparison. It does not execute workloads, rank tasks, change board state, or approve deployment. Its only output is an advisory JSON decision. See `hermes_cli/kanban_experiment.py`.

## Prepare a receipt

Schema 1 supports positive throughput values only. Put latency gates and raw correctness logs in separate attachments. Declare required metric names before execution. Freeze baseline and candidate source SHA-256 digests and one host/workload/toolchain cohort. Record at least three distinct executions on each side. Each execution must have the following fields:

```json
{
  "receipt_id": "independent-execution-identity",
  "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "cohort": {"host": "mbp-cohort-v1", "workload": "fixed-workload-digest", "toolchain": "fixed-toolchain-digest"},
  "correctness_passed": true,
  "metrics": {"claim_ops_per_second": 100}
}
```

The enclosing document has this shape. Replace the empty lists with execution receipts:

```json
{
  "schema": 1,
  "required_metrics": ["claim_ops_per_second"],
  "sources": {
    "baseline": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "candidate": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "cohort": {"host": "mbp-cohort-v1", "workload": "fixed-workload-digest", "toolchain": "fixed-toolchain-digest"},
  "baseline": [],
  "candidate": []
}
```

The parser rejects missing required metrics, duplicate execution IDs across both sides, source/cohort mismatches, failed correctness declarations, and nonpositive or nonfinite measurements. Extra metrics do not contribute to the decision. The checker does not authenticate declarations or prove that different IDs represent independent runs. Preserve raw logs so the reviewer can check that claim. See `_parse` in `hermes_cli/kanban_experiment.py`.

## Evaluate and attach

Run the checker in the checkout that contains it. Preserve the result even when it exits nonzero:

```sh
python -m hermes_cli.kanban_experiment experiment.json > decision.json
```

| Exit | Outcome | Meaning |
|---|---|---|
| 0 | accepted | Required metrics meet the deterministic comparison rule |
| 1 | rejected | Evidence is complete, but the candidate does not meet the rule |
| 2 | invalid | Receipt violates the contract or input cannot be read |
| 2 | insufficient-evidence | Either side has fewer than three distinct runs |

The rule requires at least 1% aggregate gain and permits at most 3% regression in each required metric. It also requires the candidate's worst whole-run composite to beat the baseline's best. Calculations stay in log space. For even run counts, the median log measurement is used. The rule does not supply a statistical guarantee for repeated adaptive comparisons. See `evaluate` in `hermes_cli/kanban_experiment.py`.

Use the existing PM commands to attach the contract, decision, and raw logs. Keep your board selection explicit:

```sh
hermes kanban --board PROJECT attach TASK experiment.json
hermes kanban --board PROJECT attach TASK decision.json
hermes kanban --board PROJECT attach TASK raw-measurements.log
hermes kanban --board PROJECT request-review TASK --summary 'Measured experiment; review attached evidence'
```

These commands already exist in `hermes_cli/kanban.py:575-588,2418-2469`. A worker must retain its existing run ownership for review. The checker does not bypass that check. A correctly executed losing experiment can complete without promoting its candidate, using the existing review/completion lifecycle in `hermes_cli/kanban_db.py:5408-5434,6546-6574`.

## Reproduce the evidence-safety replay

Run this through the existing fleet route. Supply the pinned public `_pm` evaluator as a read-only input:

```sh
python3 scripts/replay_kanban_experiment.py --pm-evaluator pm-autoresearch.py --out NEW-REPLAY-DIRECTORY
```

The replay uses synthetic throughput values and a fresh isolated Hermes home. It invokes the pinned `_pm` comparator, checks the same incomplete receipt with the new checker, and persists both results through actual Kanban task, claim, attachment, review, and completion APIs. It refuses to reuse an output directory. This is an evidence-safety measurement, not a product benchmark or live dispatcher qualification. See `scripts/replay_kanban_experiment.py`.

The transferred ideas come from [`_pm` at 5fa71547](https://github.com/kvnloo/_pm/blob/5fa71547ac5bb0af4e669ef219dc67ea5c7bccd7/bench/autoresearch.py#L25-L98). The module is a local opt-in adaptation, not a replacement for `_pm` or Hermes PM ownership.
