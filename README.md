# Hermes downstream qualification receipts — 2026-10-03

Five reviewed works, preserved on their original source ancestry. These are narrow results, not whole-PR approval, current-main integration, ownership transfer, or authorization to promote/merge. Repeated runs are not additional unique tests. Counts below were independently compared with retained execution receipts. This sanitized dossier excludes raw logs, local machine paths and private diagnostics.

## Publication strategy and exact identities

Implementation branches retain the complete original upstream source ancestry. Two generated test commits were copied with sanitized Codex author/committer metadata to avoid publishing a personal email; their trees and original source parents are byte-for-byte identical to the reviewed originals. Existing local refs were not rewritten. The logging branch retains both reviewed test commits. The separate receipts branch is an evidence-only root commit with no implementation history or workflows; source ancestry remains in the five implementation branches below.

| Work | Reviewed local SHA | Publication SHA | New fork branch |
|---|---|---|---|
| symlink-consumers | `ce4a9ee961c2555f20cf6b1082d435343c457593` | `fc7d63d271247d4e200442b95bd9f8e6134c2dc7` | [`downstream/20261003-reviewed-symlink-consumers`](https://github.com/kvnloo/hermes-agent/tree/downstream/20261003-reviewed-symlink-consumers) |
| logging-consumers | `4cc3d275dffb239034563d5234e524634df11f8a` | `4cc3d275dffb239034563d5234e524634df11f8a` | [`downstream/20261003-reviewed-logging-consumers`](https://github.com/kvnloo/hermes-agent/tree/downstream/20261003-reviewed-logging-consumers) |
| caption-transitions | `af39055645bca4614e9cd0cfea1e3383cab842ea` | `af39055645bca4614e9cd0cfea1e3383cab842ea` | [`downstream/20261003-reviewed-caption-transitions`](https://github.com/kvnloo/hermes-agent/tree/downstream/20261003-reviewed-caption-transitions) |
| hosted-consumers | `696aeaa968354ab629faf8c15daace7fe65db9b8` | `89cbd9a93c4f27453f0697524069b13bb0b2b2ec` | [`downstream/20261003-reviewed-hosted-consumers`](https://github.com/kvnloo/hermes-agent/tree/downstream/20261003-reviewed-hosted-consumers) |
| hosted-activity-fix | `8208ce0ac70431ce4fecad42421d0e7b1ce65e17` | `8208ce0ac70431ce4fecad42421d0e7b1ce65e17` | [`downstream/20261003-reviewed-hosted-activity-fix`](https://github.com/kvnloo/hermes-agent/tree/downstream/20261003-reviewed-hosted-activity-fix) |

Use the publication SHA for reproduction. Each published tree equals the reviewed tree listed below. No held/canceled ref, upstream branch, or existing workflow is modified. These receipts record local observed tests; they do not assert remote CI success. Exact-head remote checks are inspected separately after publication.

## Immutable identities

| Work | Preservation commit | Tree | Source ancestry |
|---|---|---|---|
| Skill consumers | `ce4a9ee961c2555f20cf6b1082d435343c457593` | `2a9b5b41f8381e27297d377161cb616c0bfd5bd7` | Direct child of S |
| Logging consumers, final | `4cc3d275dffb239034563d5234e524634df11f8a` | `58b0e63db968017b40b0ef1b34079d687ef90ca4` | Child of logging checkpoint below |
| Logging consumers, initial checkpoint | `6ffbfb2933dbe7286c87cd6a1dfe1180e397b306` | `5c1cdf090713d8dfd6491e024a9d20329062e3e1` | Direct child of L |
| Caption consumers | `af39055645bca4614e9cd0cfea1e3383cab842ea` | `8621c67441cf823b6d80362559ccaa11505d61d3` | Direct child of V |
| Hosted settled-retry consumers | `696aeaa968354ab629faf8c15daace7fe65db9b8` | `815bd85b6577e39bb9c457c99e7fdc4f1c87683e` | Direct child of H |
| Hosted stale-activity correction | `8208ce0ac70431ce4fecad42421d0e7b1ce65e17` | `aefd551fd56f9f83ea3fd6bfafc84a4da89d3f22` | Separate direct child of H |

| Source | Exact commit | Tree | Human credit |
|---|---|---|---|
| S, [upstream #125423](https://github.com/NousResearch/hermes-agent/pull/125423) | `e01284d328bf8da8f669a108dfc37fbaea2260c5` | `78b8a5234fbbfd06ba5f25c091d833964e290bfd` | plough (@529349029), original fix and correction; Git author string is Administrator |
| L, [upstream #125464](https://github.com/NousResearch/hermes-agent/pull/125464) | `673b2e15e583b46f2f3591d2631567d4b55a3a0b` | `13ac4e719a2cf76832d983d038b317866ca1350f` | strzhao (赵桂雄), logging implementation and precedence correction |
| V, [upstream #111520](https://github.com/NousResearch/hermes-agent/pull/111520) | `ad13ef7e78df3b20139bc25aca2d0855d0c78804` | `abe7d2f74c99c7c0058f40f20ea3a9de6399fdc6` | Kevin Rajan; source commit records AI assistance under his direction |
| H, [upstream #106742](https://github.com/NousResearch/hermes-agent/pull/106742) | `cb8d6920549ebe9d31f69f187d30b356b5639eed` | `3f9291bed8144a2367462e4c670c0ef6429d63d5` | Teknium; late-retry implementation credits Halldrix as co-author |

Original upstream source commits remain ancestors; the two reviewed local metadata variants remain preserved separately. Human implementation authorship is not reattributed. The stale-activity patch records Codex as its new author. Its underlying checkpoint history [93c7089f709f661b4ded75451b5953acbff8e02b](https://github.com/NousResearch/hermes-agent/commit/93c7089f709f661b4ded75451b5953acbff8e02b) credits David Dudok de Wit as author and Teknium as committer. [Late-retry work 80b3346eee356858257f518dce5d6783e0c9ffaf](https://github.com/NousResearch/hermes-agent/commit/80b3346eee356858257f518dce5d6783e0c9ffaf) retains Teknium/Halldrix credit. Evidence/test work does not claim their implementations.

## Reproduction conventions

Use a separate detached checkout of each listed publication commit. Export `HERMES_PYTHON` as an absolute path to a prepared test interpreter; `TEST_TMP` is a disposable directory chosen by the operator. Commands below run from repository root except Desktop commands. Source manifests/lockfiles remain unchanged. Canonical runner commands require a writable configured scratch area; direct pytest commands are explicitly identified.

Observed environments: skill/logging checks used Linux Python 3.12.14 with minimal test dependencies, not the fully locked supported production runtime. Hosted checks used the repository PM-built dev/test environment, CPython 3.14.7. Caption checks used Node 24.19.0/npm 11.9.0 with `npm ci --ignore-scripts`; no native Electron installation or execution is claimed.

### 1. Skill support-directory consumers

```sh
HERMES_TEST_WORKERS=2 HERMES_TEST_FILE_RETRIES=0 bash scripts/run_tests.sh \
  tests/tools/test_skill_manager_tool.py tests/tools/test_skills_tool.py \
  tests/tools/test_skill_support_consumer_qualification.py
```

Observed **132 PASS** = 76 existing manager + 51 existing view + **5 new parameter-expanded consumer cases**. Independent repeat of new cases: **5 PASS**. Real create/view APIs, files and profile A→B→A demonstrate support documents do not falsely block creation, genuine duplicates still reject, support bytes remain intact, and a legitimate support-named category stays discoverable.

Whole-source controls: overlay only the new test onto each negative checkout below and run that file. Both give **4 FAIL / 1 PASS**: four false-duplicate assertions fail; legitimate category control passes. The two commits have the same tree, so these are equivalent-source repeats, not two distinct defect classes.

| Negative commit | Tree |
|---|---|
| `1b5cbfd09744b8624e32b6d33831ab23ccfb3f60` | `d752b745d1ffe7900da5247d55926a5d4fd0f47c` |
| `f4d53c63773431399b51c29e2df37da141330a55` | `d752b745d1ffe7900da5247d55926a5d4fd0f47c` |

The tested negative file included an unused `Path` import removed before preservation; assertions are unchanged. Limits: no current-main integration, locked Python 3.14 or cross-platform qualification; these five added cases use directories, while separate existing tests cover symlink traversal.

### 2. Real logging rollover and precedence

```sh
"$HERMES_PYTHON" -m pytest tests/test_hermes_logging.py -q --show-capture=no
```

Final observed **46 PASS / 4 SKIP**, including **12 new cases**. Original eight exercise actual queued rollover/retention and launch-to-profile routing; four additional cases distinguish explicit 2 MiB from configured 1 MiB using two records that fit only the larger limit. Real queue, formatter, configuration and file handlers; no handler stubs. Independently repeated original eight and added four both pass (same cases, not extra coverage).

Exact-source controls replace only `hermes_logging.py`, retaining the tests and other files of the selected logging candidate:

| Replacement source | Tree | Selection and observed result |
|---|---|---|
| `6f7a7991bb069db07ae74a479823ce8310f8c7e0` | `b1ca8c34aa01410cf5bea6af50557ac0f39ffca7` | `-k component_rotation_reaches_real_files`: **8 FAIL** |
| `a3ee629737e3b512b3e5b6d56a9e17125fe9cff4` | `11509e2288a625591c53f16aa884979dda6cdd2c` | `-k explicit_rotation_size_wins_at_real_threshold`: **4 FAIL** |

Reproduce replacement in an isolated checkout with `git show SOURCE_COMMIT:hermes_logging.py > hermes_logging.py`; restore with `git restore --source=HEAD -- hermes_logging.py`. First control fails four errors.log assertions and four gateway/gui assertions. Second fails because errors.log unexpectedly rotates at 1 MiB. Restored production blob is `c95cb2df893740bda68c30fbb20d6a03c1b75861`. Limits: no Windows, full A→B→A multiplex isolation, concurrent-writer or whole-PR qualification.

### 3. Caption rerender and label precedence

From `apps/desktop`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm run test:ui -- src/app/chat/composer/controls.test.tsx
```

Observed typecheck PASS and **18 PASS** = 16 existing + **2 new tests**; independent repeat18 PASS. Same-mounted real controls/i18n consumer changes labels across turn states, removes the caption on inactive props, and verifies muted fallback versus active-state precedence. Loop iterations are not separate cases.

Exact-parent component control: replace only `controls.tsx` with its blob from `1ad89ac018f26a4f21817ebf37bb09f508656d63` (tree `b9d1fad2f29a429a2cd601fd5d22e74ca645a54d`) while keeping the new tests: **15 PASS / 3 FAIL**, all visibility-class assertions. This is a parent-file substitution on source V, not a new whole-parent checkout run. V changes only component and test, so production is equivalent to its parent after that substitution.

Two synthetic controls on V, separately restored: replace the complete label conditional with `const label = c.listening` → **16 PASS / 2 FAIL**; prepend muted-first precedence (`muted ? c.muted :` before the speaking condition) → **17 PASS / 1 FAIL**. These demonstrate new mapping-assertion sensitivity, not historical defects. Test SHA256 `0ffac733935eec537f3978ba9db15d60fc0b7f711b915c50804c42f63de34745`; restored component blob `d0291bee8375897e9f8ee5837ed5d2f8d452728e`.

Limits: supplied props and jsdom only; no hook/audio transition generation, actual End/Mute clicks, native layout, clipping or screen-reader behavior. Historical candidate `e33a1541de458e8409615a62cd62b6266e58f389` is not reconstructed or qualified.

### 4. Hosted retry after original-discussion completion

```sh
HERMES_TEST_WORKERS=1 HERMES_TEST_FILE_RETRIES=0 bash scripts/run_tests.sh \
  tests/gateway/test_hosted_room_retry_consumer.py
```

Observed **2 PASS** in each of three direct-process repeats and an independent canonical run: **2 unique cases**. Final test SHA256 `f32220f65828454493f236b4bf22daa8c9bc06970a70510d97b2c0f136daba68`.

Real in-process group dispatch, service/runtime, authority admission, SQLite settlement and publication; one pre-admission transport fault produces real recovery/deferral without overwriting task status. After original discussion completion, later input executes while the original remains deferred. Retry advances original execution to generation2 with frozen prompt preserved. Different-thread reply publishes once; same-thread newer input suppresses stale publication. The entire finite-model executor is substituted; no real model/tool execution or native WebSocket service is proven. Repeated preparation proves same-service idempotence, not restart replay.

Synthetic controls on H, selected `-k thread-b`, each give **1 FAIL / 1 deselected**:

- In `HostedControls.retry_room_task`, replace the final `_requeue(...)` return with `return task`: receipt remains deferred rather than queued.
- Coupled two-file mutation: remove the latest-user query's thread filter/parameter in `HostedRoomPolicyCheckpoint.events_for_task` AND remove thread matching from `plan_publication`'s newer-user check: original reply is cancelled rather than settled. This proves sensitivity to the combined mutation, not either edit independently.

Original source hashes restored after controls. Earlier exploratory concurrent same-thread input exposed a separate ordering race; the final test explicitly waits for original discussion activity and does not claim to cover that window. Historical recovery-packet identity remains unavailable; these are newly authored current-source tests.

### 5. Stale activity must not erase a newer discussion

```sh
env -i PATH="$PATH" HOME="$HOME" TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0 \
  HERMES_TEST_ISOLATION=1 "$HERMES_PYTHON" -m pytest --basetemp="$TEST_TMP" \
  tests/gateway/test_hosted_room_activity_checkpoint.py \
  tests/gateway/test_hosted_rooms.py tests/gateway/test_hosted_room_discussion.py \
  tests/tui_gateway/test_hosted_room_policy_upgrade.py -q
```

Observed direct **104 PASS**, including **2 new deterministic tests**; independent new-test repeat **2 PASS**. Real durable event log, checkpoint and planner compare old-user → newer-same-thread-user → old-discussion activity. Full replay selects the newer task; matching cleanup and other-thread isolation remain covered.

Exact H production plus the unchanged new test gives **1 FAIL / 1 PASS**: checkpoint falsely reports idle despite full replay selecting the newer task. Fix adds only `AND discussion_event_id=?` to the existing room/thread DELETE. Production blob changes from `9f73c57443bb50934918def639a4d8c7d928866a` to `03c8d810240db4c127c379e8051d88b480efcf3d`; regression blob remains `656b514d21c274dfa756c19a4dd3aad9da335f4b`.

Integration overlay, not part of the fix commit:

```sh
git show 89cbd9a93c4f27453f0697524069b13bb0b2b2ec:tests/gateway/test_hosted_room_retry_consumer.py \
  > tests/gateway/test_hosted_room_retry_consumer.py
"$HERMES_PYTHON" -m pytest tests/gateway/test_hosted_room_retry_consumer.py -q
```

Identical hosted consumer hash above; observed **2 PASS** on fixed source. This is bounded in-process compatibility, not full native reproduction of the concurrent race. **No schema bump or rebuild exists: already-lost checkpoint rows are not repaired.** The correction prevents subsequent stale cleanup during indexing. No whole-PR, current-main integration or deployment qualification follows.
