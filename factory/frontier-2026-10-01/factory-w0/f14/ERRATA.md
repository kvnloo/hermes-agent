# F14 set errata

`f14_set.json` (rev 1, set sha256 `aba79fe8f09dabc62950aacd0a53c2fdc30bc58746f405f9aa050bf474d739b9`) stays pinned and unedited so that maps stay comparable. Corrections to its prose go here. Judges, argv and markers are unchanged; only the stated reasons and expected verdicts are corrected.

## E1. context_cap_probe: wrong reason for the expected PASS (recorded 2026-10-01)

**Set text.** `postmortem/context_cap_probe` has `expect_on_base = PASS` with the reason "#103513 merged (e5f8420be8)". The `pinned_if_readmitted` block of the excluded `postmortem/subagent_context_cap` gives the same reason for its `trigger=200,000` marker.

**Correction.** The merged #103513 (`e5f8420be8`) made `delegation.compression_threshold_tokens` opt-in, with a default of `0` (no cap for subagents). The probe's 200,000 criterion comes from #103513's first draft, where the default was `200000`. So on main, "#103513 merged" explains a FAIL under the probe's default config, not a PASS. On any main that contains `e5f8420be8`, the pinned argv should be expected to FAIL. The judge (`cap: 200000`) and the argv stay as they are. The `match: false` in the receipts for this probe comes from this erratum. It is not a product regression. The stable FAIL (its verdict, marker and fingerprint) still works as a guard: if any of them changes, the comparison shows a diff.

**Evidence (OBSERVED from git objects in the mirror; gh used read-only).**

| Commit | Date | Subject | `compression_threshold_tokens` default in `hermes_cli/config_defaults.py` |
|---|---|---|---|
| `40da0fd52f` | 2026-09-05 01:07 -0700 | feat(delegation): subagents compress at an absolute context cap (delegation.compression_threshold_tokens, default 200K) | `200000` |
| `ec4c1e0c98` | 2026-09-05 06:29 -0700 | fix(delegation): validate compression_threshold_tokens; state that it caps the trigger, not the payload | `200000` |
| `dcdbc0093d` | 2026-09-06 10:36 -0700 | fix(delegation): compression_threshold_tokens is opt-in (default 0); keep the value validation | `0` |
| `e5f8420be8` | 2026-09-06 12:02 -0700 | Merge pull request #103513 (merge-commit text: "compression_threshold_tokens is opt-in (default off, children keep the 500K ratio trigger); validate the value") | `0` |
| `34f8ec3b40`, `af7287ed22` | | old and new F14 bases | `0` |

- What the merge brings in (`git diff 3d5831fa59...dcdbc0093d`): it adds `"compression_threshold_tokens": 0` with the comment "0 (default) = no subagent-specific cap". In `tools/delegate_tool.py`, `_child_compression_cap_tokens` returns `None` for `0`, and the `_apply_child_compression_cap` docstring says "Off by default: a 1M-window child compacts at 500K like its parent". `website/docs/user-guide/features/delegation.md` says "(default `0`, off)".
- `evals/postmortem/review_probes/context_cap_probe.py` was added by `a8ca904922` (2026-09-05 09:13 -0700, "feat(evals): post-mortem harness ... review probes for the #102117 run fixes"). At that time #103513's head was `ec4c1e0c98`, whose default was `200000`. That was about 25 hours before `dcdbc0093d`. The probe's docstring says: "It reproduced a defect in the first version of the PR; the fixed head must pass it." In `evals/postmortem/README.md`, the row for `live_ab/subagent_context_cap.py` says "child trigger `200,000` on a 1M model".
- The probe writes `delegation: {}` (no key), so it runs with the default. It sets the key only when given a third argument, and in that mode it prints `SPAWN` and exits before any `CYCLE` line (probe lines 40-41). The pinned `context_cap` judge needs `CYCLE` lines with `cap == 200000`. So on a main with the opt-in behaviour, the pinned set cannot reach PASS, whether or not the cap is opted in.
- OBSERVED (sandboxed, at `af7287ed22`, pinned argv, default config): `SPAWN child 850000 cap null`, four `CYCLE` lines with trigger 850000 and cap null, then `DONE f14`. The marker and the fingerprint `56dabc3674684245` are the same as on `34f8ec3b40` in all four runs (base-r1, base-r2, base2-r1, base2-r2).
- OBSERVED (side cell at `af7287ed22`, outside the set, the same probe with a third argument `200000`): `SPAWN child 200000 cap 200000`, rc 0, exit right after SPAWN. Run dirs: `<runs>/base2-erratum-context-cap/none` and `<runs>/base2-erratum-context-cap/200000`.
- MODELED (not run): on `40da0fd52f` or `ec4c1e0c98`, the probe's default config would give a child trigger of 200000, and the judge would pass. These commits do not contain the probe file, so it was not run there.

## E2. cache_estimator_probe: "#103476 is OPEN" no longer holds (recorded 2026-10-01)

**Set text.** `postmortem/cache_estimator_probe` has `expect_on_base = FAIL` with the reason "#103476 is OPEN upstream (gh read 2026-10-01), so the fix it guards is not on main: red on base". That was correct for the set's pinned base `34f8ec3b40`. It was not an authoring error.

**What changed (gh read-only, 2026-10-01).** #130645 ("fix: preserved Anthropic thinking survives rejection and resume (salvage #129620)") was MERGED at 2026-10-01T18:48:03Z. Its merge commit is `5d077106b8`. Its 32 commits were rebased linearly as `41201bf215..5d077106b8`, and `git rev-list --count` also gives 32. #103476 was CLOSED unmerged at 2026-10-01T18:49:11Z as superseded by #130645.

**Correction.** On any main that contains `5d077106b8`, the expected verdict is PASS.

**Evidence (OBSERVED, sandboxed, `--only` partial maps that are never compared).** The probe file is the same at all three commits.

| Commit | Verdict | preflight | wire estimate | preflight_should_compress |
|---|---|---|---|---|
| `41201bf215` (parent of #130645) | FAIL | 9,265 | 9,613 | false |
| `5d077106b8` (#130645 merged) | PASS | 326,510 | 327,662 | true |
| `af7287ed22` (base2-r1, base2-r2) | PASS | 326,510 | 327,662 | true |

Partial maps: `<runs>/base2-attr-pre130645.json` and `<runs>/base2-attr-post130645.json`.

## E3. notice_delivery_probe: red for a probe-side reason (recorded 2026-10-01)

**Set text.** `postmortem/notice_delivery_probe` is expected FAIL on base. It FAILs on both baselines (`34f8ec3b40`, `af7287ed22`) and on every item arm, with the same marker and fingerprint.

**Cause (OBSERVED, from the probe's own output in the baseline runs).** `TypeError: _Batch.__init__() missing 1 required positional argument: 'overall_start'`, followed by `KeyError: 'task_failure_notice'`. The probe calls a private batch helper with the signature it had when the probe was written; main has since added `overall_start`. So the red verdict says nothing about notice delivery itself: it stays a valid guard (any arm that changes it is flagged), but it is not evidence that the notice defect is still present on main.

**Correction.** None to the pinned expectation (FAIL stays FAIL on both bases). Re-admit it as a behavioural probe only after the probe is updated upstream for the new `_Batch` signature.
