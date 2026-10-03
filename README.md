# Reviewed downstream test evidence and hypothetical backup composition

Prepared 2026-10-03 for Kevin Rajan. This receipt contains only public source identifiers, synthetic fixture data, reproducible test/control materials and bounded result summaries. No real configuration, credentials, private machine files or raw environment logs are included. No upstream acceptance or whole-PR qualification is implied.

## Published code identities and credit

| Test-only result | Exact commit | Exact original author parent | Tree |
|---|---|---|---|
| Persisted pins and successful-only install selection | `50cd9cf35ad010c59cd0f993c442127d2b949c16` | dskwe, `894dd2fdac907836878ccaa8ad0a08bca41d41d0`, [#125400](https://github.com/NousResearch/hermes-agent/pull/125400) | `eb6c665411491fe67b31d2d2f39fe282dbf0cefc` |
| Google parameter fallback consumer | `4856223841c1bf2f981982291818b35bbf47aca8` | KazTradez, `dda144216abe74c759834d0e8cd30fa9d61934de`, [#125497](https://github.com/NousResearch/hermes-agent/pull/125497) | `45a225ad668ce7f03938f47c4d4f9dfc0fe3c1dc` |

Codex authored the test-only descendants under Kevin's direction. Both retain the original implementation and author history unchanged. Kevin's earlier exact-head evidence is preserved; these receipts add only the stated consumer assertions. The new commits each change one test file, no production files.

## Pin evidence

Three existing dskwe cases are strengthened, **zero new cases**. Actual temporary Lockfile publication is read through a fresh Lockfile; healthy version/artifacts persist and failed prior artifacts remain. Inert installer and sync captures assert successful-only selection and no calls on all-failed input. Known hashes avoid downloads; unexpected hashing, CLI update or process execution fails the fixture.

Canonical result: 3 PASS. Separate identical-test source controls: omitted save gives 2 PASS / 1 FAIL at fresh disk version; selecting all changed names gives 2 PASS / 1 FAIL at exact captured names. Restored production: 3 PASS. Independent reviewer reran final commit: 3 PASS, no blocker; read-reviewed the two control failures without rerunning them. These are repeats of three cases, not cumulative unique coverage.

Reproduction: in an isolated worktree at the test commit, with an existing suitable Python environment, run `HERMES_PYTHON=<existing-python> HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_WORKERS=1 bash scripts/run_tests.sh tests/pm/test_update_pin_isolation.py -q --tb=short`. For each negative, use a separate disposable worktree at that same commit, apply one patch from `pin/`, and run the identical command. Do not combine controls. No actual installation, update, sync, package fetch or full CLI execution is needed. Source and test hashes: [pin bindings](pin/source-bindings.json).

## Google fallback evidence

One new case traverses the real synchronous already-resolved fallback planner, recovery ladder, classifier, parameter removal and response validation. Only completion transport is a finite fake. A synthetic400 contains both `Unknown name` and `Cannot find field`; exactly two attempts occur, with only folded reasoning removed and all other sent arguments preserved. Typed destination avoids provider/credential discovery.

Canonical final selection: **7 PASS (1 new + 6 existing)**. The identical new test on whole parent `6f7a7991bb069db07ae74a479823ce8310f8c7e0` yields **1 FAIL**, the original synthetic GooglePayloadError instead of recovery. Independent reviewer reran the new case on final commit: **1 PASS**, no blocker, and verified identical control bytes/read-reviewed the negative. No live Google, auth, asynchronous or current-main qualification.

Reproduction: in the test-commit worktree run `HERMES_PYTHON=<existing-python> HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_WORKERS=1 bash scripts/run_tests.sh tests/agent/test_auxiliary_google_parameter_consumer.py tests/agent/test_auxiliary_parameter_rung_chaining.py -q --tb=short`. For the negative, create a disposable worktree at the exact whole parent, copy only the new test file byte-for-byte from the test commit, then run only that new file with the same canonical runner. [Bindings](google/source-bindings.json) prove identical test/client/recovery source bytes; the author's classifier is the differing production file. A discarded draft assumed an unrelated generic-route token cap; final comparable runs use the corrected identical test bytes and make no cap-policy claim.

## Hypothetical backup composition — diagnostic only

This is **not a production fix, completed integration or defect claim against unchanged main or the unchanged author branch**. Main is `bd0affe5e5f723579df8902852f5d0c47795f355`; donor is ciaomrgrey's [#124710](https://github.com/NousResearch/hermes-agent/pull/124710) at `5ef448a688b9cf47c382c372798b854a85982c1d` (Git author metadata Fork Sync Probe). Main failed-member cleanup credits JoaoMarcos44; salvage/publication/retention credits kshitijk4poor. Donor history is neither replaced nor promoted here.

The builder copies four existing donor classifiers and its writer, retains main's failed-member cleanup, and connects only automatic vanished accounting. Main publication/retention stays unchanged. [Complete hypothetical delta](backup/composition.diff). The fixture uses only owned ordinary text and synthetic existing archives, actual scan/delete/write/atomic publication/retention, and a finite injected read error after a partial member. It never creates real configuration, secrets, databases or provider connections.

| Variant | New archive | Older useful salvage | Existing complete archives |
|---|---|---|---|
| Exact main, vanished + failed | None | Preserved | Byte-identical |
| Hypothetical composition, vanished + failed | **22-byte ZIP, zero members** | **Pruned** | Byte-identical |
| Either source, plus surviving file | Incomplete ZIP with only survivor.txt | Replaced with useful new salvage | Byte-identical |

Original and independent canonical matrices each returned **3 PASS / 1 diagnostic FAIL, exit 1**. Failure is the hypothetical zero-member publication assertion, not setup; recorded inventory separately confirms useful salvage deletion. All calls return None, failed partial members are removed, and no hidden partial remains. JSON files in `backup/` record actual members/content and retention; canonical cleanup removed temporary ZIP artifacts. The mechanism is scan-count minus error-count treating vanished entries as successes despite zero archived members. No missing-critical-file, database or all-vanished policy is decided.

Reproduction: first ensure both exact commits are available in a local repository; use an isolated worktree at main. Run `python <receipts>/backup/build_overlay.py --repo <repository>` to emit exact source snapshots and the hypothetical module beside the harness. The published builder only parameterizes the original private workspace path; output hash must match [bindings](backup/source-bindings.json). From the main worktree run `HERMES_PYTHON=<existing-python> HERMES_TEST_FILE_RETRIES=0 HERMES_TEST_WORKERS=1 bash scripts/run_tests.sh <receipts>/backup/test_backup_composition_evidence.py -q --tb=short`. Expected exit is 1. Use writable canonical scratch and owned disposable fixture directories. No production patch is applied.

## Boundaries and queue

[Ten-candidate ledger](LEDGER.md). Original setup attempts that collected zero tests are excluded from counts. Existing environments were reused; no dependencies installed. Independent review denotes separate agent execution/review, not human-maintainer acceptance. Hosted CI is checked read-only after publication; absent runs/checks/statuses mean **NOT_RUN**, never PASS. All counts are local narrow evidence, not full release/PR approval.

TUI after-landing and owner-policy/environment holds remain unchanged, including #123578, #417 NOT_MET_AS_WORDED and #131689 needs-decision. Separate CUA/Bend work is excluded. No automatic upstream post, merge, workflow rerun, installation or model call is authorized by this receipt.
