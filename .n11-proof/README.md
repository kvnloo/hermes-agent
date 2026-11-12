# N11 isolated handoff candidate

This directory is a test payload, not an installed Hermes engine.

- `handoff_capsule.before.py` is the existing n11scratch plugin snapshot, SHA-256 `55bdea533f74b9575d8f3991570dd05a884601e53a76a33b0b3411ac301541f1`.
- `handoff_capsule.py` reserves space for clipping notices and aborts failed spill writes instead of discarding conversation details.
- The framed capsule, including the host's end marker, is capped at 4,000 UTF-8 bytes. Byte-level tokenizers emit at most one text token per byte, so this is a conservative bound, not a measured provider token count. Ordinary prose uses much less than the available 4,000 tokens. Full detail stays in the spill file.
- `tests/plugins/test_handoff_capsule_acceptance.py` exercises the candidate, real engine discovery, config selection, and session persistence with synthetic data. The multilingual cases cover both structured and unstructured summaries, including clipping without broken UTF-8.
- Model summaries are stubbed. The tests do not prove next-turn model recall, provider-specific tokenization, or live chat delivery.
- `/autohandoff` still takes effect at the next session, not on an existing engine instance.

Do not replace the live ayo or clean engines with this snapshot. Their current `handoff_compactor` implementations contain newer behavior not included here, including family thresholds and bare-message handoff. Clean also has model-switch handoff and pruned-skill reload notices.

Logs and the Fleet rerun script are in:
`/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-N11/`.
