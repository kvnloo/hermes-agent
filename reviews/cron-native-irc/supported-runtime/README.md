# Focused CPython 3.14.7 qualification

The unchanged cron review reproduces on actual CPython 3.14.7, Hermes' supported Python series and PM-pinned CPython release. Independent audit promotes this **evidence-only update**. It closes the focused interpreter gap; it does not certify a full PM/Astral standalone installation, complete dependency environment or full Hermes suite.

The narrow P2 finding remains: valid native IRC channel destinations fail create/update in both delivery fields on the unchanged owner implementation. The global shared-resolver experiment is **not a ready fix**: it reverses the owner's intended Telegram upfront rejection. No production or frozen-test change is included.

Implementation credit: liuhao1024 ([PR #135952](https://github.com/NousResearch/hermes-agent/pull/135952)); original report: clckmedia ([issue #135942](https://github.com/NousResearch/hermes-agent/issues/135942)); independent partial-target corroboration: aron-intframe.

## Immutable inputs and outcomes

- Tested main: `dce1e9b37581dd62e480a9064dc04a709c2940d3`
- Owner implementation: `d310978d039e479d1df5f0de8752adf6e64adea2`
- Prior published tests/evidence: `b1f8cbc58c11c82c30c4e812e4943b5ae628460e`
- Owner archive came from local metadata-only commit `34b17471f946e3fb34e1e2e51481da9de1181d20`, with exactly the same tree `1640a58f040bf4c0573e6c548e74a58eb6a65d37` as the published evidence; production files match the owner implementation
- Frozen twelve-case test SHA-256: `d247b3bbc75b5bbc12c9a949ac34ae7e7b743ea69ba6ac90b99ba7fbf4c2dc95`
- Unshipping global experiment SHA-256: `0342a38cff2c8a29577b277fd153906f5da280b89a73a2cdf8032833e9912c50`

| State | Frozen supplement | Adjacent cron argument/tool files | Resolver controls |
| --- | --- | --- | --- |
| Main | 4 passed, 8 failed | 76 passed | — |
| Unchanged owner | 8 passed, 4 failed | 79 passed | 2 passed |
| Owner + global flag experiment | 12 passed | 78 passed, 1 failed | — |

No focused tests skipped. Main's eight failures are strict-plugin malformed/parser-rejected or validator-rejected acceptance. Owner's four failures are valid native IRC create/update in both `deliver` and `failure_deliver`. The experiment's adjacent failure remains `TestValidatePlatformDeliverTargets.test_unresolvable_target_is_rejected_upfront` for `telegram:not-a-chat`.

The three twelve-case matrices match the original Python 3.12 diagnostics. Adjacent counts rise by two because exact declared `croniter==6.0.0` is present: `TestUnifiedCronjobTool.test_create_with_natural_weekday_schedule` and `test_update_to_natural_weekday_schedule` now execute successfully. The original 3.12 counts remain archived, including their two skips; they were not overwritten.

## Provenance and limits

- [Official CPython source archive](https://www.python.org/ftp/python/3.14.7/Python-3.14.7.tar.xz), verified against published SHA-256 `3b48dac8fb59f62eaa67ac83c1eb12bda1b7a08406dd286e252c11a66be27f81`; [release metadata](https://www.python.org/downloads/release/python-3147/)
- Private standard default-GIL, non-PGO/non-LTO source build at GCC 14.2.0's normal `-O3`; no experimental JIT; build and install-bytecode jobs bounded to two
- Linux x86_64, glibc 2.41, system OpenSSL 3.5.7
- Official SQLite 3.46.1 amalgamation header linked privately to installed system `libsqlite3.so.0`; header/runtime identities and in-memory SQL query agree; existing `libffi-dev` 3.4.8-2 headers/library used without system installation changes
- `ssl`, `sqlite3`, `ctypes` and `venv` smoke checks pass
- Fresh dependency-only venv: 25 package versions match immutable owner `uv.lock`, plus ensurepip's pip 26.2.1; dependency compatibility check passes. This verifies versions and dependency provenance, not every wheel byte against lock hashes or full PM dependency parity. Hermes itself was not installed
- Initially resolved `pytz==2026.5` was corrected to locked `2026.3.post1` before any test ran; both install stages remain recorded

The source build lacks nine optional native stdlib modules: `_bz2`, `_curses`, `_curses_panel`, `_dbm`, `_gdbm`, `_lzma`, `_tkinter`, `_uuid`, `readline`. No focused test skipped or encountered a missing-module collection/import error because of them. UUID operations use CPython's fallback where relevant. Other module-dependent paths remain unverified; this is not complete distribution parity.

Unrelated optional-plugin warnings for missing `requests` remain in the canonical output: browser-browser-use, browser-browserbase, browser-firecrawl, krea and xai. IRC and strict-target contract fixtures load. Absence of pytest collection errors is not a claim that every optional plugin imports successfully.

The original PM standalone download reported a proxy tunnel 403 at its GitHub asset URL. That URL was not retried or worked around. Official python.org source was separately reachable; no general installation denial or user cancellation was verified. The full PM cold builder was not invoked.

## Portable focused reproduction

Use a fresh disposable checkout for each immutable source state, and an isolated CPython 3.14.7 test interpreter. Prepare it through the supported workflow in `CONTRIBUTING.md`, or explicitly label a focused dependency-only environment as done here. `requirements.txt` records the final 25 locked versions; it does not install Hermes or establish full dependency parity.

Copy the frozen supplemental test unchanged from the prior evidence revision into the main snapshot. The owner evidence revision already includes it. In the disposable owner checkout, copy the explicitly unshipping global control to `cron_policy_control.py` only for the experiment:

```sh
cp reviews/cron-native-irc/pass_unresolved_control.py ./cron_policy_control.py
```

Point `HERMES_PYTHON` at the isolated interpreter. The recorded launcher only bounded the runner's `compileall -j0` prepass to one worker and routed bytecode caches privately; pytest execution stayed on the canonical per-file runner. Use one test worker, zero file retries and unique temporary basetemp paths. Run these seven commands from their indicated source snapshots:

```sh
export HERMES_PYTHON=/path/to/isolated/python3.14-test-env/bin/python
export HERMES_TEST_FILE_RETRIES=0

# Main checkout
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_cron_deferred_delivery_validation.py --basetemp="$HOME/cron-review-main-frozen"
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_cronjob_job_args.py tests/tools/test_cronjob_tools.py --basetemp="$HOME/cron-review-main-adjacent"

# Owner checkout, unchanged implementation
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_cron_deferred_delivery_validation.py --basetemp="$HOME/cron-review-owner-frozen"
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_cronjob_job_args.py tests/tools/test_cronjob_tools.py --basetemp="$HOME/cron-review-owner-adjacent"
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_send_message_target_parse.py -k 'test_parserless_plugin_target_passes_through_when_requested or test_plugin_parser_stays_authoritative_despite_fallback' --basetemp="$HOME/cron-review-owner-resolver"

# Owner checkout, global diagnostic control only
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_cron_deferred_delivery_validation.py -p cron_policy_control --basetemp="$HOME/cron-review-control-frozen"
scripts/run_tests.sh -j 1 --file-retries 0 tests/tools/test_cronjob_job_args.py tests/tools/test_cronjob_tools.py -p cron_policy_control --basetemp="$HOME/cron-review-control-adjacent"
```

The main supplement, owner supplement and control adjacent commands intentionally exit 1 with the documented failures. These are reproduction outcomes, not an overall passing-fix matrix. The control defaults `pass_unresolved_references=True` globally for omitted arguments; it is not validator-only and must not ship as a production fix.

## Receipt integrity

The independently audited source receipt SHA-256 is `4b547fb7526388589f89c14b1ba0243fc959ef9d991462805d193b3245b70ac4`. The portable receipt preserves provenance, exact outcomes, failure node IDs and raw-log hashes while replacing absolute sandbox paths and excluding private build state. Selected canonical logs also normalize trailing whitespace; assertions, failures, warnings and counts remain intact. No interpreter, binaries, source archives, caches, private build directories or live state are published.

The original worktrees' heads/status and relevant source/test/runner hashes were equal before and after runtime qualification. Independent audit verified all 24 recorded artifact hashes and all 24 main/owner relevant file hashes. It reviewed retained evidence without another build, install, test run or API query.

Full suite, full PM/standalone installation, complete dependency/distribution parity, absent optional stdlib paths, real transport, credentials and providers remain unverified. Upstream feedback remains unsent.
