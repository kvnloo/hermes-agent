# CUA current adoption and merged docs-owner disposition

This additive evidence packet accompanies `d25bc9e3136b8c55c4ba0e749df31c1319e1265d`. Its 33 existing manifest blobs must remain unchanged. The mutable CUA ledger now contains **nine delivery records, not nine unique fixes**. This packet adds one current-source adoption record and updates the disposition of four historical documentation records; it does not rewrite their results.

## Held-key adoption on current source

[Published commit 754c9d71](https://github.com/kvnloo/cua/commit/754c9d71fdc6f2c7ceef40771975dcc5ac5e4705) adopts the previously qualified [owner follow-up 289a65f](https://github.com/kvnloo/cua/commit/289a65f653f1fb42eee8e0ce822979a19baed1b6) onto source `f68b806024170205c63f4c65501a11e61042fa38`. It is the same held-key fix integrated and qualified on the newer source, not another independent bug fix.

The actual SandboxComputerHandler consumer failed on the unchanged current handler with missing `key_down`, then passed on the exact final commit: **one focused test passed**. A fresh supported Python 3.12.14 environment used all 63 reviewed current-lock distributions, including urllib3 2.8.0 instead of the owner's 2.7.0. Ordinary package imports ran with offline cost-map and telemetry settings plus a process-local network audit guard. Ruff, formatting and diff checks passed. Independent review verified source, dependency closure, history and receipts without rerunning the test.

The test supplies an inert recording keyboard to the real handler. It checks ordered key-down, reverse key-up, intact strings and unchanged names. It does **not** qualify native keyboard behavior, actual Sandbox transport/services, model-loop reachability, lazy opening, VM behavior or the full package suite. Ordinary compiled Python dependencies were present; this is not a native-library-free claim.

Independent API and credential-free Git verification confirmed the exact commit, tree `5dcacddcc56bf7b09e947c5d0925eec3b052a327`, ancestry and both changed blobs. At **2026-10-05 17:28:26 UTC**, hosted inventory was **zero check runs, zero statuses and zero workflow runs: CI_NOT_RUN**. Local success is not hosted validation.

### Explicit history disposition

[Normal merge bdc0dee8](https://github.com/kvnloo/cua/commit/bdc0dee884f94756b93534fea78b03a8adae40f8) preserves the current source and original owner follow-up as parents. The separate final commit explicitly restores four unrelated #4537 custom-handler/history-replay files to the current-source state. The final delta contains only the two held-key files; pingu52's original ancestry and credit remain intact. Intermediate unrelated features were not qualified or delivered independently.

**Future adoption of those unrelated #4537 features requires deliberately reverting this selective removal or reapplying them. An ordinary merge will not restore them merely because the original commits are ancestors.** The original owner-branch qualification remains a separate historical record.

## Documentation owner #4665 has merged

[Upstream PR #4665](https://github.com/trycua/cua/pull/4665), owned by f-trycua at `aa4b0777e6c44d386af0673f5dfa05cdb85a1056`, merged on **2026-10-05 at 15:22:05 UTC** as [9842b060](https://github.com/trycua/cua/commit/9842b060537303f9ac2412e77f0e061daf8a2caf). That merge is an ancestor of the observed current source `f68b806`.

The SDK index at the merge and observed current source matches the reviewed owner index, including both previously missing package-version facts. This verifies source incorporation; it does not independently reproduce the owner's SDK metadata extraction or canonical generation.

The earlier “active owner” promotion gate for downstream records `5d1dd8ec`, `4bd270be`, `127ddc0a` and `d1f6fc94` is superseded by that merged carrier. Preserve them as historical subset/composition evidence, not competing unowned repairs. In particular, the historical partial composition retains its recorded **one failed, two passed** version-fact test result. No old result is changed to a pass.

`deliveries.json` contains the bounded machine-readable updates. Supporting local review receipts are retained outside this public packet. No private source, credentials, new tests, generation or runtime actions were included in preparing this addendum. Publication of this note does not broaden the stated qualification boundaries.
