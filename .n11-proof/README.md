# HN11 isolated acceptance fix

This is a private test payload, not an installed engine. Hermes HEAD does not contain the owner's `handoff_capsule` plugin.

- `handoff_capsule.before.py` preserves the original N11 snapshot, SHA-256 `55bdea533f74b9575d8f3991570dd05a884601e53a76a33b0b3411ac301541f1`.
- `handoff_capsule.py` is the candidate under test.
- `tests/plugins/test_handoff_capsule_acceptance.py` preserves the original six acceptance checks without changes.
- `tests/plugins/test_handoff_capsule_regression.py` reuses seven N11 checks for clipping boundaries, abort safety, real discovery, and synthetic session rotation.
- Source and tests come from `data/operations/intent-analyzer-20261104/ayo-runs/exec-N11/evidence/` in `/mnt/zer0models/workspace/zer0`.
- The fix reuses N11 commit `1a133934eb7a149819cfeb1322cd5b5ba0ad5c6a`. It reserves space for clipping notices and aborts a failed spill without replacing the conversation.

Run `python3 .n11-proof/verify_acceptance.py --out /absolute/evidence/directory --label branch` from the worktree. The script runs only the six targeted tests through `venv/bin/python -m pytest <file-or-node> -q`. It records the aggregate summary and each test's actual process exit code. Each subprocess receives an isolated home and no inherited credentials. Use a fresh output directory for each rerun.

The existing Hermes `venv` is used read-only via an untracked symlink. These targeted local runs are explicitly permitted by contract HN11. Any full suite must use `fleet-build`.

The original cap is 16,000 characters, not a measured 4,000-token guarantee. Summaries are synthetic. No test proves live model recall or same-chat delivery. Do not replace the live `handoff_compactor` copies with this snapshot. They contain newer behavior absent here, and their rollout is outside HN11.

Evidence: `/mnt/zer0models/workspace/zer0/data/operations/intent-analyzer-20261104/ayo-runs/exec-HN11/`.
