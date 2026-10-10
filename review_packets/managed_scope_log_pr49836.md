# Managed-scope parse-warning review evidence for PR #49836

Local, tests-only downstream review packet. No production fix or upstream publication is included. The original contribution is [sprmn24's PR #49836](https://github.com/NousResearch/hermes-agent/pull/49836); [egilewski's August review](https://github.com/NousResearch/hermes-agent/pull/49836#issuecomment-5241901978) correctly requested a native-path regression before treating the old file-object behavior as established. This packet tests the later `read_text` implementation on current main. It makes no external-exfiltration claim.

## Exact manifest

Base: `NousResearch/hermes-agent` main `66605471e9f0b0832abbefaf625ce08e948ca540` (verified 2026-10-10 18:43 UTC). Branch: `review/managed-log-pr49836-evidence-20261010`.

Only packet files to track:

- `tests/hermes_cli/test_managed_scope_log_confidentiality.py` — native-loader RED and controls; SHA-256 `e2092e73f4fb5497744fe07d90af2f0aa91dc47290051f12771a96678cbc5712`
- `review_packets/managed_scope_log_pr49836.md` — this sanitized review summary

No source, dependency, generated file, or fixture changes are part of this branch. The separate adapted-transform worktree is uncommitted and outside this manifest.

## Current native path and result

`hermes_cli.managed_scope.load_managed_config()` reads the file with `Path.read_text(encoding="utf-8-sig")`, then `utils.fast_safe_load` calls `hermes_yaml.safe_load` (ruamel YAML). `_cached_read` logs the full parse exception at WARNING. The tests provide a real temporary `HERMES_MANAGED_DIR`, actual malformed YAML, and an ordinary log capture. There is no parser mock, logger suppression, or global monkeypatch.

Command, with `<isolated-test-python>` standing for the already prepared test interpreter in this workspace:

```sh
HERMES_PYTHON=<isolated-test-python> scripts/run_tests.sh -j 1 --file-retries 0 tests/hermes_cli/test_managed_scope_log_confidentiality.py -q
```

On unmodified `66605471`: **3 failed, 1 passed**. All three failures are the `sentinel not in warning` assertion: an unterminated quoted scalar copies its YAML source line into the WARNING; an undefined alias and unknown tag include their synthetic names in both the source line and the first exception line. The passing control checks absent-file silence, fail-open parse behavior, repeat failures not being cached, recovery after repair, and independence of valid returned data. It does not prove a valid cache hit, because reparsing would also satisfy the latter assertion.

Environment: Python 3.12.14, pytest 9.1.1, ruamel.yaml 0.18.16, Linux. Hermes declares Python 3.14 for its supported runtime; Python 3.14 and the full suite were not run. The local raw runner receipt is retained separately as `hermes-managed-log-red-1844.log`; its temporary test directories are intentionally omitted here.

## Exact owner-transform evaluation, adapted to current main

PR #49836's original diff applies to an older file-object/PyYAML implementation, so its historical head was not executed here. In a separate detached, uncommitted current-main worktree, only its proposed logging-argument transform was adapted:

```diff
 except Exception as exc:
+    exc_summary = str(exc).split("\n", 1)[0]
     logger.warning(
         "managed scope: failed to parse %s: %s — IGNORING this managed file. "
         "Admin policy from this file is NOT being applied. Fix and restart.",
-        path, exc)
+        path, exc_summary)
```

Adapted source SHA-256: `37caf7ca9da81eb70f211b3ceb6f58c989452835882a4181ad3da73c3f11c90f`. The unchanged test file SHA-256 remains `e2092e73f4fb5497744fe07d90af2f0aa91dc47290051f12771a96678cbc5712`. The same canonical runner produced **2 failed, 2 passed**: quoted-scalar confidentiality and the control pass, while alias and tag names still appear in the first-line WARNING. Raw local receipt retained separately as `hermes-managed-log-owner-transform-1846.log`.

Exploratory parser control, outside the official suite: the system Python 3.12.14 interpreter (outside the isolated Hermes test environment) has PyYAML 6.0.3. PyYAML omits the quoted-scalar source snippet when given a `StringIO` file object, consistent with the August review's narrow observation. The isolated Hermes test interpreter has ruamel.yaml 0.18.16 and does not have PyYAML installed; its current parser retains that snippet for both string and `StringIO` inputs. Alias/tag names appear in the first line under both parsers/input forms. This control was not a run of the original stale PR head. Sanitized local receipt retained separately as `hermes-managed-historical-pyyaml-control-1848.txt` (SHA-256 `5b071bc23ae0d09625f9cca3ff39e902b437e7562ce012b2c9346d411bad9580`).

Independent critic evidence is separate from this branch's two-file manifest. Its native current-main confidentiality cases were **3 failed**; three stronger controls passed, including a counted real-parser cache-hit test, invalid-read retries, valid-file repair, absent files, and managed `.env` decode recovery. Its module-origin test passed, confirming imports came from the selected worktree. Against the adapted-current-base owner transform, the unchanged critic cases and controls yielded **2 failed, 5 passed**. The critic's exploratory exception-projection matrix is not included in those native-loader counts. Critic receipts are retained separately and are not proposed for upstream publication.

## Review implication

The native-path RED establishes a current local-log confidentiality gap. PR #49836's first-line strategy removes the quoted-source snippet but is insufficient for alias and tag error classes. A candidate fix needs to preserve the file path and loud fail-open notice while deriving diagnostic details without serializing exception text or source values. This packet contains no such production candidate or GREEN claim, and is offered for the existing owner/review conversation rather than as a competing fix.
