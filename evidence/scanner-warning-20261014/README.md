# Scanner collision-warning evidence

## Result: FAIL_GAP, bounded to the scanner warning

At owner head `dafb54035dff5a6670e87b057bfd9a1d4a1d4094`, the real scanner still emits:

> Skill 'handoff' generates slash command '/handoff' which collides with a core Hermes command; skipping auto-registration. Use '/skill handoff' instead.

The listing-note helper has the corrected guidance, while `resolve_command("skill")` returns `None`. The regression fails on that emitted warning, not during setup or imports. Built-in collision exclusion and ordinary skill discovery remain intact.

The canonical run and a separate independent rerun each report **7 passed, 1 failed** across two files: the new test has **2 passed, 1 failed**, and the unchanged owner cache tests have **5 passed**. These are the same eight cases rerun, not sixteen distinct tests. Retries were disabled; one worker was used.

## Source and credit

- Report and requirement: [NousResearch/hermes-agent#138349](https://github.com/NousResearch/hermes-agent/issues/138349), deadczarvc.
- Production repair: [NousResearch/hermes-agent#138353](https://github.com/NousResearch/hermes-agent/pull/138353), KoNit-K. The author commit remains the evidence commit's parent.
- Tracking: [kvnloo/hermes-agent#501](https://github.com/kvnloo/hermes-agent/issues/501).
- Warning deduplication in RerankerGuo's #127985 and completion latency in downstream #259 are outside this task.

## Reproduction and runtime

The exact owner tree was cloned independently. A fresh isolated environment was built from its committed lock using `python -m pm.build_env --source . --out <fresh-output> --group dev --group test`. Build and dependency consistency checks succeeded. Runtime: Python 3.14.7, pytest 9.1.1, Linux x86_64. No existing environment was modified.

Set `HERMES_PYTHON` to that environment's interpreter and run `bash evidence/scanner-warning-20261014/replay.sh`. Exit 1 is the recorded failing warning contract. The test uses real source imports, real temporary skill files and configuration, real scanning and the command registry, with captured logging. Only the test workspace directory is redirected explicitly; the canonical fixtures isolate Hermes state.

## Limits

This is test-only evidence, not a production fix. It does not execute GUI or messaging command dispatch, prove every possible plugin-provided command route absent, test actual user profiles, measure completion latency, or validate the entire owner PR. The existing listing-surface test file, full suite and desktop E2E were not run. No origin changes or warning-deduplication changes were made.

Exact file hashes, runtime package versions and logs accompany this result. Independent review is in `independent-review.md`; the raw rerun is `independent-execution.log`.
