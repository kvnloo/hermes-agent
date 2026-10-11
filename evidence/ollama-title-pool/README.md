# Ollama Cloud auto title-generation supplemental regression — 2026-10-11

AI authorship: OpenAI Codex created this supplemental test/report at Kevin's instruction. No DCO signoff is asserted. Implementation remains Dinkum's PR133565; original provider incident and explicit regression request are credited to vgm-agente-ia at https://github.com/NousResearch/hermes-agent/pull/133565#issuecomment-6106369908 . Preserve fangliquanflq's #117968 attribution work and devseunggwan's rotated-binding followup; no competing production fix.

## Exact ownership and requirement

Fresh PR read: open/draft, head18b23e18e49ffa4b3dd8afa9da8ad56613c7cbba, base8cdb91eecf59f6801e9f775fc430c73cc7d02081. One discussion comment, the explicit request above. Reporter describes Ollama Cloud HTTP429 prefix `You reached your Pro weekly limit.`, sync auto title_generation/model unset, named profile fill_first, manual A+B and env duplicateA. Production did not capture Authorization keys; wireA->A was source-supported inference. Our new synthetic transport directly captures wire keys.

All26 comments in fork coordination issue447 were refreshed; none mentioned this PR, Ollama,117968 or rotated binding. All-state cross-repo PR searches and fork branches were inspected. No equivalent real Ollama title/env-duplicate regression was identified in bounded returned candidates. Relevant fork branches:81dab36acb072e70453d1b14bf13e8cb76827904 main-runtime fallback;f6792ca7eadf6aac33df2215ecd90818c9189963 async progress;5b919d144517f70e28b59fd5bedce874a639abf6 Google wire fields;0d8d04fca1986cd62fe679ad9f97bb99cbbe63f7 and72f212b2d85bd91dc7c16b6c38deb55e4b9643ef gateway override/turn composition;95b3b67533463dd2a309823f119cfb513b9246a0 custom key-env seeding. These retain their owners.

#117968 refreshed at36109a509f992ec3841e7a55072c57ebd5cbf318; its complete diff carries failed-client attribution/auth matching and mocked ZAI retry tests. devseunggwan branch fix/pool-rotation-key-binding refreshed atcb23535332ba48ed5e5878ff5c78ad83982e0b86; full diff inspected, includes real main binding fixes and a constructed mocked Anthropic approval-ladder test, not this Ollama loopback combination. Dinkum's actual owner production diff binds returned pool entry via retry_pool and explicitly attributes replacement failures.

Root/tests/agent AGENTS.md and CONTRIBUTING.md consulted. Checkout/workspace .agents contain no relevant skill files. Original worktrees were inspected and preserved. Development branch test/ollama-title-pool-supplement-20261011, publication branch test/hermes-133565-ollama-title-pool-20261011, and baseline test/ollama-title-pool-baseline-20261011. Published contents are this report and the supplemental test change only. No production edits, upstream posts, global config/hooks or live installation changes. Parent granted a single normal new-fork-branch publication lease after independent review.

## Actual execution

Official PM-built isolated environment, Linux Python3.14.7, OpenAI SDK2.24.0. Canonical scripts/run_tests.sh only, retries0, scratch write grant restricted to /var/tmp/hermes-pytest-1000.

- Unchanged owner fixture:10passed,0failed,4.3s.
- Final owner fixture including2new sync cases:12passed,0failed,4.9s.
- Exact base with byte-identical final fixture, selected new cases:0passed,2failed,2.2s; both fail exact wire-key assertion, actualA,A instead ofA,B. Both base receipts show A,B,envA all persisted exhausted/status429, although B was never sent. This is inherited baseline behavior addressed by the owner's PR, not a regression introduced by the PR.
- Adjacent4files:17passed,0failed,2.1s: auxiliary_error_classification,auxiliary_client_cache_eviction,credential_pool_seed_existing_env_sources,credential_pool_key_rotation.
- Ruff scoped file and git diff--check passed.

New healthy-B case: real SDK sends exactlyA,B; response succeeds; manualA and rehydrated envduplicateA persist exhausted/code429, B remains healthy/selectable over two fresh auth-store load_pool reconstructions. Both-quota control: sends exactlyA,B, terminal APIStatusError429 with quota prefix, A/duplicateA/B exhausted429, no selectable entry. Main-runtime snapshot unchanged. No arbitrary credential, pool, route or transport functions mocked. Reuses owner's real ThreadingHTTPServer, DNS127.0.0.1-only guard, cache teardown and profile context. Synthetic auth/config rows, profile-scoped synthetic OLLAMA_API_KEY/BASE_URL.

## Limits and observed model difference

Direct public call_llm(task=title_generation), not generate_title, gateway startup, main streaming turn, real concurrency or deployed acceptance. Named profile directory/context supplied directly; no profile registry/launcher exercised. Fresh auth-store reloads occur within one process, not a new gateway process. Synthetic loopback HTTP quota response, not live account quota verification. DNS guard blocks non-loopback hostnames; not a general network sandbox. No external provider/real credential/paid calls. No async extension or larger-pool/quarantine redesign.

With model unset, owner head sends first model deepseek-v4.1-flash, replacement retry nemotron-3-nano:30b (registered default auxiliary model). Base sends deepseek-v4.1-flash twice. Initial overbroad same-model assertion failed on head; final test narrows to requested wire identity/persisted health and explicitly does not certify same-model retry. Server accepts either model. No production fix for this separately observed routing behavior is included.

Hosted workflows at owner head report action_required (CI,Nix,Docker,label reruns); this is an approval gate, not an executed test failure. Dinkum's reported282passes/macOS are author evidence, not our execution. No full suite or cross-platform qualification. Independent critique summarized below. Parent granted the publication lease after qualification; no upstream PR/comment is authorized.

## Reproduce

Create isolated worktrees at exact head/base. Copy the final test file from this branch into tests/agent/test_auxiliary_pool_retry_binding.py on both (file absent on base). PM build uses checkout source/dependency manifests unchanged:

```sh
HERMES_HOME=/workspace/title-pool-build-home HERMES_RUNTIME_DIR=/workspace/title-pool-build-runtime python -m pm.build_env --source /workspace/hermes-title-pool --out /workspace/title-pool-test-env --group dev --group test
cd /workspace/hermes-title-pool
HERMES_PYTHON=/workspace/title-pool-test-env/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/agent/test_auxiliary_pool_retry_binding.py -v
cd /workspace/hermes-title-pool-base
HERMES_PYTHON=/workspace/title-pool-test-env/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 1 tests/agent/test_auxiliary_pool_retry_binding.py -k ollama -v
cd /workspace/hermes-title-pool
HERMES_PYTHON=/workspace/title-pool-test-env/bin/python HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 2 tests/agent/test_auxiliary_error_classification.py tests/agent/test_auxiliary_client_cache_eviction.py tests/agent/test_credential_pool_seed_existing_env_sources.py tests/agent/test_credential_pool_key_rotation.py -v
```

Baseline intentionally exits1. Final head/adjacent exit0. PM environment build completed normally; no native test blockers.

## SHA256 exact source and fixture

- hermes-title-pool/agent/auxiliary_client.py: `546e89b2adac46d86fe9dfaa0d4f0a0fc3a090abe1994040b5aef38975d6ffe0`
- hermes-title-pool/agent/auxiliary_pool_recovery.py: `1621e3f0546f46d084b71be2980866cc6791b69a0dd1f29e268482544d3d5d30`
- hermes-title-pool/agent/credential_pool.py: `111d8e0d990630341a42dc2fa4a740f16746d5963e8d6900cfd25c54d109da66`
- hermes-title-pool/tests/agent/test_auxiliary_pool_retry_binding.py: `c6f1274920b88de5dab8547f5ba3ddc5d9f65d3d49242ee2f6b5d1be514ba456`
- hermes-title-pool-base/agent/auxiliary_client.py: `d3e33be71835dbe30a118e3c1b854057d6f6b724850e410e128ecf70b27edc76`
- hermes-title-pool-base/agent/credential_pool.py: `111d8e0d990630341a42dc2fa4a740f16746d5963e8d6900cfd25c54d109da66`
- hermes-title-pool-base/tests/agent/test_auxiliary_pool_retry_binding.py: `c6f1274920b88de5dab8547f5ba3ddc5d9f65d3d49242ee2f6b5d1be514ba456`


## Publication scope and review

Classification: **LIMITED native loopback acceptance**. Existing owner test functions are byte-for-byte unchanged; shared endpoint fixture has only necessary opt-in quota response parameterization, retaining default402 behavior. Two genuinely new parametrized cases are added. No production implementation is added.

Independent reviewer: /root/title_pool_critic, GPT-6.1-sol at requested xhigh. Inspected final fixture, real auth-store reload source, execution logs and actual interpreter/SDK; did not rerun completed tests. Verdict: no blocking defect for the narrow credential-binding/immediate saved-health contract. Both synthetic failures use identical error bodies: wire and persisted attribution are proven, but surfaced exception origin A versus B is not distinguished.

These gates overlap and must not be summed: unchanged owner10PASS; supplemented head12PASS; selected new baseline2FAIL; adjacent17PASS. This packet is not full generate_title/gateway/provider E2E.

## Receipt fingerprints

- title-owner-unchanged.log: SHA256 `e720d490a1edaca33c910aa903d9ea8b995a23c4df8dc02b2f46e5b30427bdc7`
- title-head.log: SHA256 `61f61f35a68600acb4de6685db886c6c9d9ef3fca8a654b2783770183aaf202d`
- title-base.log: SHA256 `966b95c641eb663df3c104fb3bb500070b0785154309738326326c4fe76f49e2`
- title-adjacent.log: SHA256 `23e526e8b1f89edce344d01f6e7ca2459be65f6c9c8812dbbc307015e3ab9e4c`

Sanitized baseline observation in both new cases: wire[A,A], models[deepseek-v4.1-flash,deepseek-v4.1-flash], saved A/B/env-A exhausted with code429. Owner head assertions require wire[A,B], healthyB selectable on both reloads, and duplicateA exhausted. Both-quota case requires terminal429 and no selectable entry after both real keys fail. Synthetic labels and temporary stores only.
