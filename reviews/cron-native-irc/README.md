# Native IRC cron validation review evidence

Tests and diagnostic evidence only for [PR #135952](https://github.com/NousResearch/hermes-agent/pull/135952), implementing [issue #135942](https://github.com/NousResearch/hermes-agent/issues/135942). No production fix is included. Implementation credit remains with liuhao1024; original report: clckmedia; independent partial-target corroboration: aron-intframe.

**Supported-series follow-up:** the same focused matrices now reproduce on actual CPython 3.14.7. See [the portable supported-runtime receipt](supported-runtime/README.md). This closes the focused interpreter gap, while full PM/standalone distribution, dependency parity, the full suite and real transport remain unverified. The original Python 3.12 results and logs below are preserved.

## Narrow finding

On reviewed owner head `d310978d039e479d1df5f0de8752adf6e64adea2`, `tools/cronjob_job_args.py:306` uses the strict default target resolver. It rejects the valid native IRC destination `irc:#future-room` when no channel-directory entry exists. The bundled IRC plugin has no target parser, but uses `#future-room` as the native channel `chat_id`; the existing cron fire-time path resolves it using `pass_unresolved_references=True` (`cron/scheduler_delivery.py:652-653`).

Actual `cronjob_manage` registry dispatch reproduces this create/update regression in both `deliver` and `failure_deliver`. Tests use a temporary on-disk home and paused store, cold enabled-plugin discovery, and no live transport. The strict test plugin's adapter factory fails if called; network connection attempts are guarded; lazy dependency installs are disabled. This is evidence of valid native syntax, not proof of successful delivery on a configured IRC network. It does not require preserving every arbitrary unresolved reference under an intentionally stricter upfront policy.

The review requests a native IRC parser or deliberately scoped compatibility policy that retains valid channel syntax while keeping upfront validation authoritative. It does not recommend the broad diagnostic monkeypatch as an implementation.

## Exact snapshots and results

This evidence branch is based on the owner's exact head, not upstream main. The actual owner parent is `5ba559c9e4b1c8397df7788e319ab634144ca728`; the tested main snapshot is `dce1e9b37581dd62e480a9064dc04a709c2940d3`. The parent and main are byte-identical for the relevant cron tool, resolver, delivery and IRC adapter files. No test run on the actual parent is claimed.

The frozen supplemental test SHA-256 is `d247b3bbc75b5bbc12c9a949ac34ae7e7b743ea69ba6ac90b99ba7fbf4c2dc95`. Its two parametrized invariants produce twelve cases:

- Four valid native IRC cases: create/update in both delivery fields
- Eight strict-plugin atomic rejection cases: create/update, both fields, malformed parser grammar or a post-resolution validator rejection; a valid first destination followed by an invalid second destination must leave the store byte-identical

All results below were independently reproduced:

| Diagnostic state | Frozen supplement | Adjacent cron argument/tool tests |
| --- | --- | --- |
| Main snapshot | 4 passed, 8 failed | 74 passed, 2 skipped |
| Unchanged owner head | 8 passed, 4 failed (native IRC) | 77 passed, 2 skipped |
| Owner + shared-resolver flag experiment | 12 passed | 76 passed, 1 failed, 2 skipped |

The experiment's adjacent failure is the owner's intended `telegram:not-a-chat` upfront rejection. Its 12-case pass does not supersede that failure. Two existing resolver controls also pass: parserless pass-through when requested and strict plugin parser authority despite fallback.

## Runtime qualification

The original runs documented below are **unsupported-runtime diagnostics on Linux Python 3.12.14** in a separate dependency-only environment. Hermes requires Python `>=3.14,<3.15`. The separate linked follow-up qualifies the focused matrices on CPython 3.14.7; the PM-supported complete dependency environment, the full suite and real transport remain unverified. Neither receipt certifies a production fix.

The repository's `scripts/run_tests.sh` was used with one worker and retries disabled. The independent replay additionally bounded its `compileall` prepass to one worker through a disposable interpreter launcher, without changing pytest execution. An earlier missing declared `httpx` dependency was recovered in the diagnostic-only environment; those initial results are not reported as product failures. All final adjacent results below include that dependency.

## Reproduction

From a fresh checkout containing this evidence, point `HERMES_PYTHON` at an isolated test interpreter with the declared relevant dependencies. Preparing a supported environment is described in `CONTRIBUTING.md`; these recorded results did not use one.

```bash
export HERMES_PYTHON=/path/to/isolated/test-env/bin/python
export HERMES_TEST_FILE_RETRIES=0
scripts/run_tests.sh tests/tools/test_cron_deferred_delivery_validation.py -j 1 -q
scripts/run_tests.sh tests/tools/test_cronjob_job_args.py tests/tools/test_cronjob_tools.py -j 1 -q
```

Expected diagnostic supplement result on this branch: four IRC failures and eight strict-plugin passes. The branch intentionally carries the reproduction; it is not a passing fix branch.

For the **unshipping global flag experiment only**, in a fresh disposable checkout:

```bash
cp reviews/cron-native-irc/pass_unresolved_control.py ./cron_policy_control.py
scripts/run_tests.sh tests/tools/test_cron_deferred_delivery_validation.py -j 1 -q -p cron_policy_control
scripts/run_tests.sh tests/tools/test_cronjob_job_args.py tests/tools/test_cronjob_tools.py -j 1 -q -p cron_policy_control
```

The control monkeypatches `tools.send_message_targets.resolve_send_target` globally in the test process, defaulting the fallback flag to `True` whenever a caller omits it. It is not validator-only. The scheduler already supplies `True`, so that path's flag is unchanged. Only the control's explanatory docstring was corrected after the recorded execution; its executable body is unchanged. Expected diagnostics: twelve supplement passes, then the adjacent Telegram negative failure.

`receipt.json` records original and independent summaries plus SHA-256 hashes. Selected logs replace absolute sandbox and temporary-directory paths with placeholders and normalize trailing whitespace; assertions, errors, counts and warnings are preserved. The frozen test bytes are unmodified. No owner production source or existing test was changed.
