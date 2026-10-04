# Batch 2 H4: independent review and bounded owner triage

No new worktree or implementation branch created. Published H2 commit `40b59b21440c6e9c723c49e4f74dfbaf019b455d` remains untouched.

## CUA independent review — approved

Candidate `019c26f65e0e59f8a8661321d63c5fb1fb105000`, `/workspace/lanes/cua`, base `0335d5a5e0fd197522365fef3487a279be94ad4f`.

Reviewed exact two-file diff: `.github/workflows/ci-images-spacesd-lag.yml` and `scripts/images/tests/test_lag_scope.py`. No correctness findings.

- Successful base fetch remains mandatory; invalid/unavailable revision is not silently accepted.
- A valid historical base missing `libs/cua-spacesd/VERSION` is interpreted as introducing the component, so the workflow skips the lag check and reports its existing release-following notice.
- Existing unchanged/changed VERSION decisions remain intact; missing current-head VERSION still fails at `cat`.
- New tests execute the shipped shell block against disposable local Git history, including invalid-base exact exit 128. No live registry, credentials, release, or deployment.
- Existing `ci-check-image-refs.yml` discovers `scripts/images/tests` on every PR, so test placement is covered.
- Author's focused evidence: missing-base regression fails 128 before fix; final 3 new + 23 existing tests pass. Reviewed evidence and code without redundant test reruns.

This is an independent CI reliability fix, not a claim that CUA guarded completion #111 is integrated. Hosted CI remains separately unrun on the candidate.

## Hermes H5 review — evidence approved

Initial review identified source-only assertions; author revised the probe to assert generated `_core_release_quarantine` policy equality, preserving existing reviewed dated values. Independently inspected current PR #130838 and #132300 guard diffs: both enumerate core/optional/build requirements and omit dependency-groups. Final canonical probe reports two expected failures and one passing control: current main fails; the two owners' seven-entry policy deltas still produce `distlib = "14 days"` for group:test; adding the group pin in the synthetic control yields `false` and passes.

Approve this bounded evidence. It simulates policy deltas in memory, not full owner-commit qualification, `uv lock`, or a live mirror installation. No production policy file edited; no competing implementation. Evidence: `/workspace/receipts/batch2-h5-quarantine-probe.log`, `/workspace/receipts/batch2-h5.md`.

## Gateway owner triage

Bounded latest-source searches found no qualified unowned implementation. Skipped:

- #132371 explicit `/steer` attachment loss: broader search found exact older open #57946, despite issue-number search returning none.
- #132422 and #132517: kokhlo publicly claimed implementations.
- #132359 -> #132501.
- #131786 -> #131824 / #131830.
- #131738 -> #131770; #131688 -> #131866.
- #131614 -> #132295 (also related #132288 / #131243).
- #131778: active #132153 diagnostic work; independent real-mautrix reproduction already cannot break dispatch; needs reporter evidence.
- #131875 -> #131938; #131520 -> #131526.
- #131783 -> #131799.
- #132200 Google Chat attachments/deps -> #132226 and credited external branch86c3a81ea9; also #132245 deps.
- #131658 claimed by bakdauletbaktygaliyev; exact once-per-request fix already #124071.

No upstream comments, issues, PRs, merges, deployments, paid calls, dependencies installed, or policy bypasses. Parent redirected H4 to actual independent review rather than further broad owner searching.

## Final CUA documentation child — approved

Reviewed exact docs-only child `9846bb67a927ef1320bce577c4bbae1ea2974c12` over code `019c26f65e0e59f8a8661321d63c5fb1fb105000`: one README, 25 added lines, 13 failed-job rows; executable files unchanged.

Cross-checked every job URL/name/head SHA/failed step against `failure-details.json`, `jobs.json`, and each raw `*-job.json`. All 13 rows match head `b2ae7cb934403f2585c7d3ed23a188b44264f293`; each saved direct-log response contains Forbidden. Nine underlying causes remain explicitly unknown. The baseline row reports only the available missing-ledger annotation and leaves offending refs unknown. Missing-VERSION and title rows label their evidence local reproductions rather than inferred inaccessible hosted stderr. Documentation Sync is correctly an aggregate gate, not an invented generator root cause.

No findings; approve publication of the documentation child with existing local/hosted evidence distinction. No tests rerun because this child changes documentation only.
