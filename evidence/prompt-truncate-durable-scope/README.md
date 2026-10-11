# Post-merge prompt.submit durable-cut commit window — 2026-10-11

Classification: LIMITED native RPC/SQLite acceptance; enforcing-mode safety regression, no production fix. AI authored by OpenAI Codex at Kevin's instruction; no DCO signoff or human authorship asserted.

## Requirement, ownership and refresh

Fresh upstream main before editing and final refresh: b30f95ac4a80d2f6dbe3aa01001b0524314f6d74. #133748 merged at0faf0938ebdc4420e11070822cf4f9db09eb4260; its first/only parent is10cf19374542c7a9bf0a8b5b144c9105adf09162. New isolated worktree /workspace/hermes-prompt-b4, branch test/prompt-truncate-durable-scope-20261011. Existing worktrees/branches preserved.

Requirement: current website/docs/developer-guide/programmatic-integration.md lines72–78 documents deep-confirm rollout: current release logs/allows an unconfirmed deep cut, next enforcing release refuses4033 with archived-message/user-turn data and writes nothing. This probe scopes server.DEEP_TRUNCATE_ENFORCED=True to the fixture. It does not mislabel the default False/warn-only behavior as a refusal violation, nor invent a rollback policy.

Implementation credit: kshitijk4poor #133748. Original B4 discovery/review and requested read/write-window coverage: JoaoMarcos44, https://github.com/NousResearch/hermes-agent/pull/133748#pullrequestreview-5479952381 . That review already executed append before RPC entry; it requests a concurrent append between read and write. This new deterministic ordering complements that discovery, not an original B4 discovery claim. Kevin's complementary fork459 B1-B3 remains open at a9825f5f1f65930d82497559fe212d857b0e3030, based on134612abbd414bf68fc1f6eb2f24ab568e5f6be2; actual four-file delta/two Desktop production-file scope inspected. No backend scope transfer or competing implementation. The separately owned admitted-provider-error classifier claim at https://github.com/kvnloo/hermes-agent/issues/447#issuecomment-6092414639 is excluded; no UI classifier/ACK work resumed.

Ownership scope: refreshed all26 #447 comments, fork459 metadata/diff and complete original review. No new claim in returned #447 comments owns this exact commit-window probe. This is bounded coordination/known-owner refresh, not an exhaustive all-PR absence claim. Prior task publication leases closed and unused here. Parent granted a single downstream-only publication lease after qualification. No upstream write or production fix is authorized.

Root AGENTS.md, tests/AGENTS.md, tui_gateway/AGENTS.md and CONTRIBUTING.md development setup/test guidance read. Canonical oss-factory AGENTS/control/HITL/registry refreshed. Checkout and workspace .agents contain no applicable skill file. Public requirement and functional review justify bounded evidence, not an upstream promotion decision.

## New executed boundary

Real public server.handle_request dispatches prompt.submit, validates contract/target and runs real depth/admission/persistence paths. Fixture creates the full canonical SessionDB schema in disposable HOME/HERMES_HOME/runtime; two real SessionDB handles share one SQLite file. Seed u0,a0,u1,a1; warm conversation loaded with real row IDs. No extra turn exists at RPC entry.

Only the first handle's bound real replace_messages is wrapped for injection. At its entry, warm history/version remains unchanged, target rowu1 is valid, outgoing kept prefix is u0,a0, and flags remain active_only/archive_dropped/reject_active_turn_lease allTrue. The real depth gate has already permitted one warm user turn. Second handle now really commitsu2,a2 before the original writer runs; both handles see identical physical post-append snapshot/counters. Wrapper does not alter writer arguments, disable lease checks or intercept rollback. Original replace_messages executes its real transaction against the current durable suffix.

Only compute/provider execution is replaced with a no-network dispatch recorder at _run_after_agent_ready; session agent is a minimal already-present placeholder, no agent build starts. No alternate RPC handler, target/depth resolver, admission/ownership guard, config loader, _session_db or SessionDB implementation is substituted. server._db points to the real disposable first handle. Socket connect is forbidden throughout the fixture. Real worker thread is joined before observation/teardown. This proves reaching the compute boundary, not running an actual AIAgent/provider turn.

## Exact results

Final canonical new-file execution: **1PASSED shallow control / 1FAILED commit window**, exit1,1.6s runner wall/1.02s pytest (see exact log for timing). No collection errors/skips or file retries. The RED assertion expects response.error.code4033; actual response is streaming, survivor_user_row_ids[1], user_row_id7.

Postappend: physical IDs1–6 all active1/compacted0; counters(message_count,tool_call_count,rewind_count)=(6,0,0). After actual RPC: u0/a0 remainactive; u1/a1/u2/a2 areinactive0/compacted0; new replacementu1 row7 active1. Counters=(3,0,0), warm history shortened to u0,a0,history_version1, compute recorder reached once. Thus refusal/no-dispatch/no-mutation expectations fail; these measurements are printed before the first RED assertion. Later safety assertions are not falsely counted as executed passes. Archived rows remain physically present; no permanent erasure, rollback, live tool effect or deployed user incident proven.

Same-route noappend positive control: streaming, user_row5, one recorder dispatch; onlyu1/a1 archived, warmu0/a0/version1, counters(3,0,0). This rejects a setup that refuses all rewinds for unrelated reasons.

Adjacent unchanged tests:3files34PASSED0FAILED,11.6s runner wall. Includes test_tui_gateway_server_deep_truncate.py (enforcing4033 and documented warn-only rollout) plus tui_gateway/hermes_state composite_carrier_rewind suites (separate guarded rewind_to_message/slash retry ordering). Those guarded paths do not qualify prompt.submit→replace_messages commit window. No counts are summed across different qualification claims.

Scoped Ruff and whitespace checks pass. Initial fixture run was1PASS1FAIL with same behavior but teardown warning: fixture left its session registered and _db pointing to a closed handle, so tests/conftest.py finalizer read/reopened it. Final cleanup joins worker, releases slot, removes only this session and restores saved _db before closing both handles; final run has no warning. Initial log retained separately; final logs below supersede it. No product failure attributed to that cleanup artifact.

## Inherited mechanism and limits

hermes_state_messages.py is byte-identical between premerge parent10cf1937 and current main (SHA below); git diff for that file is empty. This is SOURCE comparison, not a baseline runtime rerun. Joao's existing review independently identifies inherited destructive suffix archival. New gate misses the window; the old writer mechanism is not claimed newly introduced by #133748. No production fix is provided.

The injection is deterministic sequential commits via two real handles inside the write seam, not a probabilistic simultaneous-thread stress test, SQLite lock contention or ambiguous commit error. In-process history_lock cannot block an independent handle. No watcher, cron producer, mounted Desktop/Electron, WebSocket or external provider exercised; those explain source-supported architecture possibilities only. Profile default disposable DB context, not multiplex-profile qualification. DEEP_TRUNCATE_ENFORCED=True is fixture-only; default production rollout remains False. No full suite/hostedCI/cross-platform acceptance. No disabled persistence/ownership guard. No #92140 object reads, plugin-consumer403 workaround, real credentials, live install or destructive cleanup.

## Environment and reproduce

Official PM build from current pinned checkout's committed manifests, Linux Python3.14.7, pytest9.1.1, OpenAI SDK2.24.0 (SDK not invoked). No raw pip/uv or dependency substitutions.

```sh
# Fresh disposable worktree at exact main; copy probe.py into tests/tui_gateway/test_prompt_truncate_durable_scope.py in an isolated replay worktree.
HERMES_HOME=/workspace/b4-build-home HERMES_RUNTIME_DIR=/workspace/b4-build-runtime /workspace/title-pool-test-env/bin/python -m pm.build_env --source /workspace/hermes-prompt-b4 --out /workspace/b4-test-env --group dev --group test
cd /workspace/hermes-prompt-b4
HERMES_PYTHON=/workspace/b4-test-env/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/tui_gateway/test_prompt_truncate_durable_scope.py -v -s
HERMES_PYTHON=/workspace/b4-test-env/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 2 tests/tui_gateway/test_tui_gateway_server_deep_truncate.py tests/tui_gateway/test_composite_carrier_rewind.py tests/hermes_state/test_composite_carrier_rewind.py -v
/workspace/b4-test-env/bin/ruff check tests/tui_gateway/test_prompt_truncate_durable_scope.py
git diff --check
```

The first test command intentionally exits1 for RED; adjacent exits0. Restricted executor granted scratch writes only to /var/tmp/hermes-pytest-1000. No provider acceptance or production configuration changed. Independent xhigh critique accompanies the packet. Publication uses the parent-granted downstream-only evidence lease.

## SHA256

- tests/tui_gateway/test_prompt_truncate_durable_scope.py: `e92109f213737970c82f29d9aaecf8fe7b04f1c2a679e27502240890e64068ca`
- tui_gateway/methods_prompt.py: `7307dba5aa1df597c99c551b4f344d0e292141e0e6c45f3c3fa2daddb0dbeee9`
- hermes_state_messages.py: `5d81a781e61650d04e7d239fae5a59d1aa65632a029b1e14ad9ccb113de93a62`
- hermes_state.py: `b76fc6af3b7f37ee1de1be62379acb08d56069796eaf3bdf253a480be704e578`
- tui_gateway/server.py: `5e51f2b4ad33af95044be68a001d0ae66948d8c116fe8ff28a8e70b378ca3be1`
- tui_gateway/session_workdir.py: `8a3e8ea9382f69105d3b58d265e226544372e5b6672a0c9f105f22b77f54ebd1`
- website/docs/developer-guide/programmatic-integration.md: `54d851cd7aab742409cd908bf488ae75d1a6c3edce0dd1ec744bccae38c98318`
- pyproject.toml: `865992a77dd7be18ce8b2e63c87d2c6bd66a76cb0babaa84ad3de061f5bb5af8`
- uv.lock: `95a3082629ffecdabb1bad0880ccf5a237d47cd8fb67d86094f6d3d331f4eeac`

Premerge parent hermes_state_messages.py has the same5d81a781e61650d04e7d239fae5a59d1aa65632a029b1e14ad9ccb113de93a62 hash.

Independent /root/prompt_b4_critic (GPT-6.1-sol,xhigh) verdict: no substantive fixture blocker; reviewed ordering/guards/requirement/cleanup and final logs, did not independently rerun. Nonblocking maintenance limits: exact writer kwargs assertion pins current seam and may need relaxing for a future CAS argument; proposed4033 error.data counts are not asserted. This is a diagnostic packet, not complete acceptance for a future atomic-scope fix. Full critique is supplied in review.md and the Library packet.

## Published layout and portable replay

Current upstream main and fork459 were refreshed immediately before publication and remain at the tested main and the ownership head above; no code drift. All26 coordination comments refreshed; no competing B4 commit-window claim found in this bounded refresh. The admitted-provider-error classifier remains excluded.

The diagnostic probe resides outside tests/, so its intentionally RED acceptance assertion is not discovered by ordinary CI. Execute only in an isolated replay worktree. Starting with an official PM-managed Python3.14 interpreter:

```sh
HERMES_PYTHON=/absolute/path/to/pm-managed/python bash evidence/prompt-truncate-durable-scope/replay.sh
```

The script creates a new disposable detached worktree at the exact tested commit and an official PM test environment, copies the frozen probe to the sanctioned tests/tui_gateway location (thereby loading its canonical fixtures), then invokes the canonical runner with retries0. It preserves the replay worktree/artifacts and returns the expected1 for the RED gate. It never modifies the caller's ordinary tests/, installs globally, pushes or cleans up another worktree. If the required interpreter is unavailable, stop rather than treating missing setup as native test failure.

Exact final test output: probe.log. Adjacent unchanged output: adjacent.log. Independent source/log critique: review.md (not a separate rerun). The new contribution is prepared by OpenAI Codex; commits must not assert human authorship or DCO certification.

Published probe.log has trailing whitespace stripped only; raw original log SHA256 `01df600eea208c31d72bf48e8d3859663036971584a205c07ab99ffaba4c3a7c`, normalized published SHA256 `4a9f7b95ea43199a3201918ccdbe3bb5c77c5b1b669313ec7874680c5748839b`. Assertions, outputs and receipt data are unchanged. Replay script received shell-syntax validation only; completed native tests were not rerun merely for packaging.
