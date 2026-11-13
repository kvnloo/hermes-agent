---
name: hermes-memory-combined-substrate
description: Use when composing Hermes memory study substrates.
---

# Combined memory substrate studies

- Fetch and pin current upstream main and every contributor input by full SHA. Compose in an owned worktree; preserve authorship and publish only the explicitly authorized downstream draft branch.
- Preserve newer main behavior when historical memory patches conflict: single-item add overflow echoes, remove-only batch exemptions, drift backups and deletion safeguards, lock permissions and retry caps. Sanitize echoed entry lists rather than removing the upstream overflow contract.
- Re-cut chain-document reads onto the lock-held stateless read implementation. Compute usage from local parsed entries, support an uncapped limit, sanitize document contents, and name the actual document in removal guidance.
- Revalidate chain references with the anchor lock held through document commit; acquire anchor before document locks. A speculative preflight is not authorization. Preserve orphan readability without granting writes.
- Wire document arguments through the real inline agent executor, not just registry handlers. Keep writes in operations[] and advertise read separately without forbidden schema combinators; qualify the rendered prompt snapshot.
- Execute immutable falsifiers from their own pinned checkout against the published combined SHA. Do not edit a falsifier to turn it green. Verify encoding fixtures write actual bytes, not backslash-escaped byte notation.
- Use the repository CI-faithful toolchain setup on Avrea, including uv on PATH and test extras. Reconcile any saved setup script against the exact candidate's `.github/workflows/tests.yml`: optional extras deliberately excluded from `all` (such as `keychain`) can be added to current CI after the saved script. A plain runtime environment or stale extras list creates false failures.
- For canonical per-file test runners, a single shared --junitxml path overwrites evidence. Inject an untracked pytest plugin with a tryfirst pytest_configure hook that sets config.option.xmlpath to a unique path derived from config.args. Smoke-test reporting separately and retain the plugin source with the request.
- Pass the reporting plugin as `-prfc_out_junit`, never `-p rfc_out_junit`: Hermes CLI imports pre-parse the separated `-p` as a profile selector, causing SystemExit and cascaded fixture errors throughout full-suite runs. A tiny pytest-only smoke does not expose that collision; include a CLI-importing file in harness qualification.
- Parse every actual JUnit testcase; preserve failures, errors, skips, duplicate identities and missing reports. Do not certify an author-selected test-count gate without its exact manifest. Keep exploratory response-size thresholds separate from accepted API contracts.
- Retain exact request JSON, run identity, checkout SHA, unchanged runner/probe hashes, raw XML and per-case summaries. Read back the downstream PR and remote head after publication. Poll hosted runs no more often than once per minute.
