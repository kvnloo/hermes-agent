# Batch 4 H2: existing-owner systemd integration + startup consumer proof

## Exact candidate

- Fresh upstream base: `ea81748579ee1732d214ccb75f91d22208ed623d`.
- Integration branch: `integration/batch4-systemd-124082` in `/workspace/lanes/h2`.
- Exact tested head: `fba7a46a454a004e8fc1966d3bde1dbb2c3c5588`.
- Prior published H2 branch `lane/h2-gateway` remains at `40b59b21440c6e9c723c49e4f74dfbaf019b455d`.

## Existing ownership preserved

Owner https://github.com/NousResearch/hermes-agent/pull/124082 by happy5318 remains at `fad747a451c27ecddfe77fb3e9e707160a6a7464`. Current comments retain prior Kevin review and the owner's fix for the earlier too-restrictive LoadState predicate. No owner branch was changed, no competing implementation created, no upstream communication.

Original authored commits applied cleanly with `git cherry-pick -x`:

| Original | Integrated |
| --- | --- |
| 799edfd165a916f50f5452e7982134c127ddf587 | 7d0c2982a539347af3416aec0e68410b8abb325a |
| c315d15c9b50ca4232598919ccbf485e65c02a67 | 02b01e4631aece86c6bb6fcaaf060906cd33543a |
| fad747a451c27ecddfe77fb3e9e707160a6a7464 | 085db941e7b35784c0dbbb8a97459b31716c0179 |

Original names/emails/dates retained, including literal `happy5318 <>` on the third commit. No email was invented. Production file and owner test file are byte-identical to the selected owner head after integration.

## New consumer coverage and negative control

New 33-line `tests/gateway/test_systemd_timing_alignment_consumer.py` has one parameterized behavior test, two cases. It exercises real `check_systemd_timing_alignment`, including synthetic cgroup unit resolution, actual stop-budget calculation, real owner scope probing and final `mismatch` decision. It supplies only synthetic subprocess output:

- Absent user-manager unit offers its phantom 90s default; actual system unit equals required 210s -> `mismatch=False`.
- Same absent user unit, actual system unit 209s -> `mismatch=True`.

This is distinct from the owner's existing helper-only assertions. It proves suppressing the false warning does not suppress a real short-budget decision. Report credit: Borisov-Hermes #132565. All inputs are temporary/env fixtures and module-local mocks; no real systemctl, service changes, process inspection or provider calls.

On unpatched fresh base, both cases fail with 90s instead of 210s/209s. Evidence `/workspace/receipts/batch4-systemd/base-red.log`. No base production mutation was required.

## Exact final validation

```
HERMES_PYTHON=/workspace/.onboarding/hermes-tests/bin/python scripts/run_tests.sh -j 2 tests/gateway/test_shutdown_forensics.py tests/gateway/test_systemd_timing_alignment_consumer.py -k 'manager or present_load_states or missing_loadstate or absent_load_state or alignment_uses_loaded_system_unit'
```

Exact committed head: **15 passed, 0 failed** (13 existing owner cases + 2 new consumer cases), `/workspace/receipts/batch4-systemd/final-tests.log`. Selection excludes existing live shutdown diagnostic tests. Canonical runner used explicit `/var/tmp` write grant, no runner changes. Fatal-error Ruff on the three changed Python files and `git diff --check` pass. Worktree clean.

## Delivery/review

Independent H1 reviewer approved exact candidate with no blocking findings; independently verified stable patch IDs and author metadata for all three cherry-picks, consumer distinctness, and red/green logs. No push yet. Hosted CI **NOT RUN**. No live systemd qualification claimed. Parent to handle downstream publication while preserving original authored metadata; REST reconstruction may reject the original empty author email, which must not be silently replaced.

## Parent delivery update

Published and remotely verified: `kvnloo/hermes-agent:evidence/systemd-owner-integration-20261004` at exact tested `fba7a46a454a004e8fc1966d3bde1dbb2c3c5588`. REST Git commit creation rejected the original empty author email with HTTP422. A normal Git push using the existing command-scoped credential helper then succeeded, preserving all original metadata. No author identity or stored credential configuration was changed. A verified8.3KB backup bundle remains local; remote branch delivery succeeded, so no bundle workaround is required.
