# N11 isolated handoff candidate

This directory is a test payload, not an installed Hermes engine.

- `handoff_capsule.before.py` is the existing n11scratch plugin snapshot, SHA-256 `55bdea533f74b9575d8f3991570dd05a884601e53a76a33b0b3411ac301541f1`.
- `handoff_capsule.py` reserves space for clipping notices and aborts failed spill writes instead of discarding conversation details.
- `tests/plugins/test_handoff_capsule_acceptance.py` exercises the candidate, real engine discovery, config selection, and session persistence with synthetic data.
- Model summaries are stubbed. The tests do not prove next-turn model recall, actual token counts, or live chat delivery.
- The cap remains a 16,000-character heuristic. It is not a measured 4,000-token guarantee.
- `/autohandoff` still takes effect at the next session, not on an existing engine instance.

Do not replace the live ayo or clean engines with this snapshot. Their current `handoff_compactor` implementations contain newer behavior not included here, including family thresholds and bare-message handoff. Clean also has model-switch handoff and pruned-skill reload notices.

Logs and the Fleet rerun script are in:
`/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-N11/`.
