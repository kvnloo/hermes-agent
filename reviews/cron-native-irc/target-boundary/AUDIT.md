# Independent Hermes target-boundary audit

## Verdict: PROMOTE evidence-only

The new evidence supports the smallest recommendation in the target-boundary README: keep the owner's strict upfront guard and Telegram rejection, and give IRC native channel **and nick/DM** target authority through its existing plugin parser/validator callbacks. Do not widen the shared fallback. The registry experiment genuinely exercises the owner dispatch/resolution composition; it does not bypass the shared resolver or final validators.

Independent canonical replay matched the recorded result:

| Run | Exit | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Unchanged owner | 1 | 25 | 12 | 0 |
| Frozen IRC-only callback experiment | 0 | 37 | 0 | 0 |

No blocking evidence defect found. This verdict promotes a diagnostic review and narrowly scoped recommendation, not a production parser/fix or supported-runtime qualification. Implementation ownership remains with liuhao1024. No upstream communication, publication or installation occurred.

## Scope and identity

Audited source checkout: `review-hermes-cron-target-boundary`, HEAD `e114b0cf78802d11131e0cb44a831dbbe2a4ae6f`.

- Owner: `d310978d039e479d1df5f0de8752adf6e64adea2`
- Reviewed base: `dce1e9b37581dd62e480a9064dc04a709c2940d3`
- Current-main snapshot: `f925b01791fe052e7d55dc975750c0bd985aff91`
- Prior published evidence: `e114b0cf78802d11131e0cb44a831dbbe2a4ae6f`
- Frozen composition test: `3c3ad6d81715f3251c4120c2cf2f98d635c3d61440340616775b706007f419d8`
- Frozen final control: `22814fe951f6086a35202dc191892bdfe859ea417763437974c4dcafcdb77d10`
- Reused supplement: `d247b3bbc75b5bbc12c9a949ac34ae7e7b743ea69ba6ac90b99ba7fbf4c2dc95`

Verified all 9 hashes in the supplied artifact manifest. Independently read each of the 14 source-matrix paths at all four Git pins and compared the working bytes: all 70 checks match. All 14 current-main files equal base. The supplement matches the prior evidence pin. This only establishes the listed files, not complete current-main dependency/import parity or a current-main replay.

A separate import preflight with the existing diagnostic interpreter resolves the owner guard, cron tool, shared resolver, send facade, scheduler delivery, registry, IRC adapter and Telegram ID helper to this checkout. Their source hashes match the owner. The facade's `resolve_send_target` is the same function object as the shared resolver. The frozen control imports directly from its review file. This is direct preflight import provenance, not per-test runtime instrumentation of every discovery alias.

No tracked source diff was present before or after the replay. New test/control/evidence remain untracked as supplied. No old worktree was operated on. The unrelated Hermes eviction review was outside this audit.

## Why the composition is real

1. The tests dispatch through `tools.cronjob_tools.registry.dispatch("cronjob_manage", ...)`. Create calls the owner's `_validate_platform_deliver_targets` before job creation; update validates before persisting pending fields. Both `deliver` and `failure_deliver` are covered.
2. The owner guard still calls the real `prepare_send_message_platforms()` and shared `resolve_send_target()` with its strict default. Neither callable is replaced by the control.
3. The reused fixture enables the actual bundled IRC plugin and an on-disk strict-contract plugin under a new temporary Hermes home. The control discovers the real IRC entry and patches only its `parse_target_ref_fn`, `validate_target_ref_fn`, and an adapter-construction refusal guard. It leaves Telegram and the strict-contract registration unchanged.
4. The shared resolver calls a plugin parser first, validates any parsed ID, and also validates generic/directory/fallback results. The strict-contract `stream:13/daily` case parses successfully to channel `13` and is rejected by its real final validator. The malformed `stream:5:daily` case fails parser/directory resolution and cannot use permissive fallback once a parser exists. These cases distinguish parser refusal from final-validator refusal.
5. IRC's existing adapter sends `PRIVMSG` to its provided target. The standalone path recognizes channel prefixes `#&+!`, joins channel targets, and explicitly avoids joining bare nicks/DM targets. The experiment accepts both the representative native `#future-room` and `future-nick`; a channel-only callback would make an unresolved nick strict and lose current fallback behavior.
6. Fire-time resolution still uses the existing permissive flag. The experiment adds IRC authority so upfront and fire-time resolution agree for the two tested native forms; it does not alter that flag or make it global.

The IRC parser and validator use the same deliberately broad helper. The eight malformed IRC cases principally exercise parser rejection, so they do not separately prove IRC-specific validator refusal after a successful parse or directory resolution. Final-validator refusal is behaviorally established through the strict-contract plugin; the shared implementation's application of the IRC callback to every returned ID was inspected statically. This is a limit, not evidence of a bypass.

## Case attribution and atomicity

The frozen 37 cases comprise 12 positive scheduling cases, 20 invalid-second-target cases, 4 IRC-first/invalid-Telegram-second cases, and the owner's original Telegram-negative test.

- The unchanged owner fails all 8 representative IRC scheduling positives: channel/nick × create/update × deliver/failure_deliver. Fire-time resolution succeeds, then upfront dispatch rejects IRC as unresolved. The control makes all 8 pass and retains the 4 explicit numeric/topic Telegram positives.
- In the 4 IRC-first/invalid-Telegram-second cases, unchanged owner rejects the first IRC element. Those diagnostic failures are error-attribution failures, not evidence that Telegram was accepted. The control reaches and rejects the Telegram element.
- Negative cases start with valid explicit Telegram syntax and reject an embedded-space IRC target, NUL IRC target, unresolved Telegram target, strict-plugin parser refusal or strict-plugin final-validator refusal. Each spans both actions and both lanes.
- Every successful negative assertion names the offending element and compares `jobs.json` byte-for-byte with a previously seeded paused local job. The shared owner code performs rejection before create persistence and before update persistence. This supports the claimed job-store atomicity for the tested inputs; it is not a general proof of every possible filesystem or scheduler side effect.
- The original owner's Telegram-negative test is unchanged and passed in its separately isolated test-file subprocess. The control's fixture returns immediately for that file.

No skipped case was used to obtain the green control. The frozen expected count is 37, and both terminal summaries account for all 37.

## Fixture isolation and retained failed attempt

The final control explicitly depends on `_hermetic_environment`, then obtains `delivery_home`, then discovers/patches the IRC entry. Canonical isolation first removes credential-shaped and behavioral environment values, redirects Hermes state, and resets per-home plugin managers/modules. `monkeypatch` restores callback edits, and the canonical runner gives each test file its own interpreter process.

The retained initial control log shows the earlier autouse seam lacked that dependency. Its 6 failures, 12 passes and 18 setup errors are consistent with discovery/reset ordering, including later `entry is None` assertions. It is correctly excluded from product counts. The final frozen composition test is unchanged. The independent final replay passed all 36 new cases plus the isolated original negative.

Fixture guards fail `asyncio.open_connection`; the control also fails any IRC adapter construction, and the strict fixture's factory refuses transport. The tested paths only resolve/schedule paused jobs. No transport/provider execution was performed. The fixture is a focused transport guard, not a blanket instrumentation of every possible networking API.

## Replay receipt

After the parent released the exclusive OMP window and granted one team job slot, both runs used the canonical runner with one worker, zero retries and separate temporary roots. The slot was released after terminal results.

Runtime: existing Linux CPython **3.12.14**, dependency-only diagnostic venv. It is unsupported for project qualification. `pyproject.toml` intentionally permits older versions for updater bootstrapping but explicitly documents 3.14-only support; `CONTRIBUTING.md` requires `>=3.14,<3.15`. No install or venv modification was performed. The absent prior supported runtime was not substituted or counted.

The existing disposable launcher changes only canonical `compileall -j 0` to `-j 1`. The actual runner and pytest subprocesses use the real interpreter. The control was loaded with `-p reviews.cron-native-irc.irc_native_parser_control`, which preserves the frozen bytes and avoids a checkout-root copy.

Selection:

`native_and_explicit_targets or invalid_second_target or native_irc_first or unresolvable_target_is_rejected_upfront`

Files: `tests/tools/test_cron_target_boundary.py` and `tests/tools/test_cronjob_job_args.py`.

Both canonical invocations were bounded by `timeout 100s`; neither timed out. Raw independent receipts are `owner-replay.log`, `control-replay.log`, `replay-exitcodes.txt`, `import-preflight.json`, and `static-identity-verification.json` beside this audit. The original-named audit logs and identity receipts are bundled in audit-receipts.json. Absolute checkout and temporary-root paths are normalized for this public packet; assertions and diagnostic content are preserved.

## Promotion limits and owner recommendation

Retain all README limitations. In particular, this evidence does not establish:

- Supported Python 3.14 replay of this new composition
- Full PM installation, locked distribution/dependency parity, aggregate checks or full suite
- Complete IRC nickname/channel grammar, server-specific limits, target existence or acceptance
- All channel prefixes, nickname variants, CR/LF cases, resolved directory aliases or every invalid control/delimiter form
- Actual IRC/Telegram connection, delivery, credentials or provider execution
- A production edit, accepted owner implementation, upstream approval, or current-main runtime result

Optional-plugin missing-`requests` warnings and absent `croniter` remain disclosed. The selected `every hour` schedule uses the existing fallback and does not exercise natural weekday scheduling.

Recommended owner wording: Keep strict create/update validation and the Telegram negative. Register IRC-native parsing and final validation through the existing plugin callbacks, preserving channels and nick/DMs, and share authoritative target checks with the IRC adapter. Add adapter/native-syntax tests before shipping. Do not relax the shared resolver fallback globally, and do not present this broad single-token diagnostic as a complete grammar or a production repair.

Observed official UTC: 2026-10-10T13:04:16Z. The sandbox system clock differs; the static receipt keeps its raw system-clock value separately.
