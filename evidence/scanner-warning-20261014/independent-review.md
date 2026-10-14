# Independent scanner-warning evidence review

Reviewed 2026-10-14 at approximately 13:27 UTC.

## Verdict

The evidence is valid for the narrowly claimed scanner-warning defect on owner head `dafb54035dff5a6670e87b057bfd9a1d4a1d4094`. A real filesystem scan still emits a recommendation to use `/skill handoff`, while the real built-in command resolver has no `skill` command and the owner's collision-note helper has already removed that recommendation. This is an assertion failure, not an import, collection, dependency, or fixture-setup failure.

The finding is suitable for the downstream evidence card. It does not establish that the entire owner PR is invalid or reproduce the original desktop dispatch failure end to end. Production repair remains with KoNit-K; the original report remains credited to deadczarvc.

## Independent reproduction

- Checkout: `repo`, local branch `evidence/scanner-collision-warning-20261014`.
- Source: exact owner head above, also freshly confirmed through PR metadata at https://github.com/NousResearch/hermes-agent/pull/138353. At review time the PR was open and draft.
- Runtime: `/workspace/shared/hermes-skill-warning-evidence-20261014/test-venv/bin/python`; actual run reported CPython 3.14.7, pytest 9.1.1 and pluggy 1.6.0. The runtime build log completed successfully and its venv metadata identifies Python 3.14.7, without system site packages. The reviewer reused this freshly supplied runtime, rather than independently rebuilding it.
- Independent invocation used `env -i`, a new disposable HOME, explicit `HERMES_PYTHON`, `HERMES_TEST_FILE_RETRIES=0`, and `bash scripts/run_tests.sh tests/agent/test_skill_collision_warning_contract.py tests/agent/test_skill_cache_thrash.py -j 1`.
- Result: **7 passed, 1 failed across 2 files; canonical runner exit 1**. New evidence file: 2 passed, 1 failed. Existing cache-thrash file: 5 passed. No skips or collection/setup errors were reported.
- Independent receipt: `independent-execution.log`. The first run's `execution.log` independently reports the same counts and failed assertion.
- Failure: `test_skill_collision_warning_contract.py:61`. The captured record is `WARNING agent.skill_commands:skill_commands.py:494`, ending with `Use '/skill handoff' instead.`

The runner's approximate discovery/progress count says about seven tests, but the per-file outcomes and final summary establish eight executed cases: seven passes and one failure. Do not report this as seven total cases.

## Validity and isolation

I read the root and relevant area guidance and inspected scanner, registry, discovery and fixture behavior. The evidence calls the real scanner and command resolver. It creates a real SKILL.md and temporary configuration; its only explicit behavioral patch is changing the working directory. It does not replace the scanner, collision predicate, catalog, registry or logger with fakes, and it does not read source text in a test assertion.

The canonical fixtures bind a fresh HERMES_HOME under each test's temporary directory. The evidence verifies that containment, writes `external_dirs: []`, and changes to an empty temporary workspace. The runner strips the ambient environment and isolates each test file in a subprocess. Thus the observed warning is not explained by the preceding cache-thrash file's patched state or a user's installed skill.

The controls establish that the `handoff` built-in name is recognized, that its colliding skill is not auto-registered, and that an ordinary `tidy-notes` skill is auto-registered without an agent.skill_commands warning. Before failing, the regression case also establishes that the collision warning exists, `resolve_command('skill') is None`, and the collision-note helper no longer includes `/skill handoff`.

Production remained identical to HEAD before and after the rerun. The only staged addition was the supplied 61-line test file. Relevant SHA-256 hashes were unchanged:

- `agent/skill_commands.py`: `219c4318f8bc0d85b389c3716ab64be6be8562ae30ddede12bf71bd5c7af8a13`
- `hermes_cli/commands.py`: `ea8a8ff56486c7a6006d592c3c1f12a36f8d42a2fc9d418ade6a9bd6a495c475`
- Evidence test: `6efa0fca282a6e894655ae2f550b3741c040e6525857a23fdb029cea176527f0`

## Critical caveats

1. **Exact requirement:** this proves stale scanner guidance while the built-in loader is unregistered on the pinned owner head. The original report permits either implementing a real loader or correcting the advice. The test's unconditional `resolve_command('skill') is None` is appropriate as this head's characterization, but would reject a legitimate future implementation of the alternative loader. Do not treat that assertion as a permanent product requirement.
2. **No GUI/dispatch proof:** no desktop composer, gateway command.dispatch, slash-exec path, Windows host, or GUI error was exercised. Absence from the built-in registry is not a comprehensive proof that no plugin or quick-command route could ever exist. The directly demonstrated defect is the scanner's advice in this isolated configuration.
3. **Warning-test precision:** the controls use the presence of any WARNING-or-higher record from agent.skill_commands rather than matching a collision record. A future unrelated warning could satisfy that broad visibility check. Here the actual records are explicit collision warnings for the created skill, so this does not invalidate the reproduction. For a durable regression test, tighten the record attribution without snapshotting all wording.
4. **Bounded coverage:** the five passing cache tests are controls, not certification of all freshness, deletion, timing, concurrency or cross-platform behavior. No full suite, owner listing-surface suite, i18n IPC path or production repair was run. No upstream/public writes were made by this reviewer.
5. **History limit:** this is a shallow owner checkout. GitHub issue and PR descriptions verify the requirement and intended owner fix, but no full historical `git log -S` investigation or independent base-red comparison was performed.

## References

- Original report and accepted alternative directions: https://github.com/NousResearch/hermes-agent/issues/138349
- Owner PR and exact head: https://github.com/NousResearch/hermes-agent/pull/138353
- Bounded downstream acceptance: https://github.com/kvnloo/hermes-agent/issues/501

No blocker remains to publishing the narrowly scoped evidence. The reproduced scanner assertion remains red and must not be described as a passing repair validation.
