# IRC / Telegram target-policy composition

Evidence-only follow-up for [liuhao1024's PR #135952](https://github.com/NousResearch/hermes-agent/pull/135952), addressing [clckmedia's issue #135942](https://github.com/NousResearch/hermes-agent/issues/135942). Implementation ownership remains with liuhao1024. No production change or upstream message is included.

## Smallest owner recommendation

Keep the owner's strict create/update validation and Telegram rejection. Give the IRC plugin native target authority through its existing `parse_target_ref_fn` and `validate_target_ref_fn` registration seams. Cover channel **and nick/DM** forms, and share the adapter's target checks instead of changing the shared resolver's fallback default. A channel-only parser can make existing nick fallback strict because a plugin with a parser no longer receives unresolved pass-through.

The isolated experiment below proves these existing seams can compose the required outcomes. It is **not a production parser**: its nonempty single-token check mirrors one existing standalone preflight, without establishing complete IRC grammar, server acceptance, destination existence or successful delivery. A shipping implementation still needs authoritative native syntax and adapter tests.

## Immutable source inputs

- Owner: `d310978d039e479d1df5f0de8752adf6e64adea2`
- Reviewed base: `dce1e9b37581dd62e480a9064dc04a709c2940d3`
- Current-main snapshot fetched for this review: `f925b01791fe052e7d55dc975750c0bd985aff91`
- Prior published evidence: `e114b0cf78802d11131e0cb44a831dbbe2a4ae6f`

[source-matrix.json](source-matrix.json) records SHA-256 for 14 relevant production, test, fixture and runner files at all four pins. Current main is byte-identical to the reviewed base for every listed file; the new evidence checkout's tracked source matches the owner. Current-main composition was inspected statically, not tested. The owner's unrelated source-release changes are outside this review.

Source anchors at the owner pin:

- `tools/cronjob_job_args.py:285-309`: upfront resolver call uses the strict default
- `tools/cronjob_tools.py:667-679,830-852`: both create/update delivery fields use the guard
- `cron/scheduler_delivery.py:650-653`: fire-time resolver explicitly permits unresolved references
- `tools/send_message_targets.py:140-214`: plugin parser authority, final validator and directory resolution; parser-bearing plugins remain strict under fallback
- `plugins/platforms/irc/adapter.py:216-226,440-441,537-542,566-568,585-617`: channel/nick native targets; standalone single-token preflight; no target callbacks in IRC registration
- `tools/send_message_targets.py:61-67` and `plugins/platforms/telegram/telegram_ids.py:10-30`: explicit Telegram numeric/topic and username syntax
- `gateway/platform_registry.py:99-103`: the existing plugin parser/validator seams

## Fresh unsupported-runtime results

These runs used existing Linux CPython **3.12.14** and its dependency-only diagnostic venv. Hermes requires `>=3.14,<3.15`. This is a new narrow diagnostic, not a fresh supported-runtime qualification; the separately published CPython 3.14.7 receipt remains historical evidence. The former supported interpreter was unavailable here. No installation or dependency change was attempted.

| Frozen boundary | Cases | Unchanged owner | IRC-only callback experiment |
| --- | ---: | --- | --- |
| Native `irc:#future-room` scheduling | 4 | 4 fail | 4 pass |
| Native `irc:future-nick` scheduling | 4 | 4 fail | 4 pass |
| Explicit Telegram numeric/topic scheduling | 4 | 4 pass | 4 pass |
| Malformed IRC second element: embedded space or NUL | 8 | 8 atomic rejections | 8 atomic rejections |
| Unresolved Telegram second element | 4 | 4 atomic rejections | 4 atomic rejections |
| Strict plugin malformed parser syntax / validator rejection | 8 | 8 atomic rejections | 8 atomic rejections |
| Valid IRC first, unresolved Telegram second | 4 | Stops at valid IRC; 4 diagnostic failures | Reaches Telegram; 4 atomic rejections |
| Owner's existing Telegram-negative test | 1 | 1 pass | 1 pass |
| **Total** | **37** | **25 pass / 12 fail** | **37 pass** |

Every four-case row covers create/update in both `deliver` and `failure_deliver`. Negative tests assert error attribution and byte-identical `jobs.json`, including a valid first element followed by the rejected element. Jobs remain paused in temporary homes. Discovery is through the existing frozen on-disk plugin fixture. Network connection attempts fail the tests; the control also refuses IRC adapter construction. No live transport is used.

No focused test skipped. The unchanged owner’s eight native failures and four first-element attribution failures are intentional review reproductions, not an overall passing run. The control leaves the shared resolver, owner guard, Telegram registration and original Telegram-negative test untouched. It changes only the discovered IRC `PlatformEntry` parser, final validator and transport guard for the new composition file.

The initial control attempt had a harness fixture-ordering defect: canonical per-test isolation reset the registration after the seam was installed. That attempt produced 6 failures, 12 passes and 18 setup errors in the new file; the owner's negative still passed. The final harness explicitly depends on `_hermetic_environment`. Frozen test bytes did not change. The failed attempt remains in [its classified log](logs/control-fixture-order-attempt.log), not counted as a product result.

## Portable reproduction

Use a disposable checkout at the prior evidence pin, with the new test and final diagnostic module present. Do not replace any production source. Prepare an isolated test interpreter through `CONTRIBUTING.md` for a supported replay; explicitly label any focused dependency-only alternative. The versions actually used here are in [dependencies-frozen.txt](dependencies-frozen.txt).

```sh
export HERMES_PYTHON=/path/to/isolated/test-interpreter
export HERMES_TEST_FILE_RETRIES=0
selection='native_and_explicit_targets or invalid_second_target or native_irc_first or unresolvable_target_is_rejected_upfront'

# Unchanged owner; expected exit 1, 25 pass / 12 fail.
scripts/run_tests.sh -j 1 --file-retries 0 \
  tests/tools/test_cron_target_boundary.py tests/tools/test_cronjob_job_args.py \
  -k "$selection" --basetemp=/tmp/cron-boundary-owner

# Unshipping IRC-only registry experiment; expected exit 0, 37 pass.
cp reviews/cron-native-irc/irc_native_parser_control.py ./irc_native_parser_control.py
scripts/run_tests.sh -j 1 --file-retries 0 \
  tests/tools/test_cron_target_boundary.py tests/tools/test_cronjob_job_args.py \
  -k "$selection" -p irc_native_parser_control --basetemp=/tmp/cron-boundary-control
```

Recorded runs used the canonical runner with one worker, zero retries and unique basetemp paths. A disposable interpreter launcher bounded its `compileall -j0` prepass to one worker; pytest behavior and subprocess isolation were unchanged. The launcher's local interpreter path is not a portable installation contract.

Frozen SHA-256:

- New test: `3c3ad6d81715f3251c4120c2cf2f98d635c3d61440340616775b706007f419d8`
- Final IRC-only control: `22814fe951f6086a35202dc191892bdfe859ea417763437974c4dcafcdb77d10`
- Unchanged reused supplement: `d247b3bbc75b5bbc12c9a949ac34ae7e7b743ea69ba6ac90b99ba7fbf4c2dc95`

[receipt.json](receipt.json) records exact counts, pins, hashes, classified harness attempt and unchanged old-tree status. Logs retain assertions, errors, counts and warnings while replacing absolute local paths and normalizing trailing whitespace. The new test reuses the published frozen plugin fixture; that fixture and all owner production files are unchanged.

## Limits

Full suite, full PM installation, complete dependency/distribution parity, supported-runtime replay of this new composition, real IRC/Telegram transport, credentials, provider execution and complete native/server grammar remain unverified. Missing `requests` warnings from unrelated optional plugins remain in failed-run output; IRC and the strict contract fixture load. `croniter` is absent from this existing diagnostic environment; these selected tests use the supported fallback for `every hour`, not natural weekday schedules.

This is ordinary compatibility/input-validation review under `SECURITY.md` §3.2. No unauthorized access, exfiltration, isolation escape or other §3.1 security finding is asserted. Prior global fallback experiment results are preserved separately and do not qualify as a fix.
