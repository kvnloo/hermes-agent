# Track 1 — NanoJev as a shadow per-turn decider

RFC: kvnloo/hermes-agent#309. Branch: `lab/track1/nanojev-spike`.

## The seam

Every user turn implicitly asks **"what should this turn do?"** z0int answers it
with a DecisionOpportunity over ACT / ASK / ESCALATE
(`kvnloo/z0intelligence` `src/z0int/decision_opportunity.py ::
deterministic_gate` — first legal action by fixed priority, the #55
falsification baseline). Hermes core makes no such decision today: every turn
goes to the frontier model. The z0int-decisions plugin
(`harness-adapters/hermes-z0int-decisions`) already records these
opportunities in shadow, keyed by turn.

This spike wires z0int's **NanoJev** local decision backend (0.6B parameters,
CPU-capable, fp32) as the decider for that exact question — in shadow mode.
Nothing is rerouted; the module only logs `{gate, nanojev}` verdicts per turn
for agreement analysis.

## Why this seam

- It is the smallest real per-turn decision in the Hermes/z0int system with an
  existing baseline (the deterministic gate) and an existing observation rig
  (`z0int hermes decisions` joins gate vs observed outcome by trace_id).
- NanoJev's contract (boolean/choice/score questions → probability
  distributions) matches it exactly: one 3-way choice per turn.
- If a local model can match the gate — or beat it against observed outcomes —
  the turn-triage decision stops costing anything, and a future step can use
  it to route (cheap local answer vs ASK vs frontier).

## Layout

- `agent/nanojev_shadow.py` — the spike. Stdlib-only. Classifies the turn
  (port of `z0int.hermes_decisions.classify`), builds the DecisionRequest,
  shells out to the z0int child (`python -m z0int.cli backends eval
  --backend nanojev`), appends a JSONL record. `hook_entry()` is the
  `pre_llm_call`-shaped integration point (not wired yet).
- `lab/track1/turns.jsonl` — 12 sample turns with hand labels (the spike
  author's judgment, not ground truth).
- `lab/track1/bench_nanojev.py` — baseline (deterministic gate) vs spike
  (NanoJev) vs hand labels. Writes `bench_results.json`.
- `lab/track1/shadow_records/` — JSONL output (git-ignored scratch).

## Run the bench

```bash
# one-time: z0int venv with torch + the NanoJev checkpoint
python3 -m venv z0int-venv
z0int-venv/bin/pip install torch transformers safetensors tokenizers huggingface-hub numpy
# checkpoint -> ~/.z0int/models/nanojev_06b/ (best.safetensors, config.json,
#   tokenizer/, backbone_config/) or set Z0INT_NANOJEV_CHECKPOINT

Z0INT_PYTHON=z0int-venv/bin/python z0int-venv/bin/python lab/track1/bench_nanojev.py
```

## Unit tests

```bash
python3 -m pytest tests/agent/test_nanojev_shadow.py -q   # stdlib-only, no torch
```

## What "done" looks like for the spike

`bench_results.json` shows N/N decisions produced, gate-vs-label and
nanojev-vs-label agreement, and per-turn latency. The follow-up experiment
(RFC #309) promotes this to a fixed task set with tokens/turn, task success,
and decision-agreement against observed turn outcomes from real sessions.
