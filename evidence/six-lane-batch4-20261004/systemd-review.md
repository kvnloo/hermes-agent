# Independent review: owner PR124082 systemd integration

Reviewer lane H4; 2026-10-04. Read-only inspection; no test reruns or service commands.
Previous turn-proof worktree/ref remains untouched at72f212b2d8.

## Current owner/source evidence

GitHub PR124082 remains open, head `fad747a451c27ecddfe77fb3e9e707160a6a7464`,
author happy5318, last updated2026-10-01T21:02:40Z. Original commits:

- `799edfd165a916f50f5452e7982134c127ddf587`
- `c315d15c9b50ca4232598919ccbf485e65c02a67`
- `fad747a451c27ecddfe77fb3e9e707160a6a7464`

Verified final original raw commit has `author happy5318 <>`; preserve that empty email
exactly, do not synthesize a GitHub noreply address or add invented coauthors.
Parent commit is c315d15. PR current base metadata is a0fe806c46e729894c60e5dd25154400d179b231.

Issue132565 is the same user-manager not-found/default90s shadowing the actual system
manager timeout already owned by124082. No new competing implementation warranted.
Kevin's existing2026-10-01 comment already reviewed that narrow behavior; repeating
helper-only cases would not add a useful deliverable.

## Distinct qualification scope

The owner tests directly call `_systemd_timeout_stop_us`; the requested current-source
consumer instead carries real parsing and real budget calculation through
`check_systemd_timing_alignment`. Two outcomes matter: aligned system timeout does not
produce a mismatch, and a genuinely short system timeout still does. A fake nonexistent
user-manager response must not shadow either outcome.

Read current `gateway/run_startup.py::_start_log_systemd_timing_alignment`: it checks the
returned dict's `mismatch` flag before logging. Although the alignment function docstring
says None when aligned, actual source returns a dict with mismatchFalse. The consumer
should assert real behavior, not encode the inaccurate docstring.

All unit discovery/property data must be synthetic (INVOCATION_ID, module-local open for
cgroup, subprocess.run returning CompletedProcess). No actual systemctl/service action.
Existing shutdown-forensics tests include real diagnostic shell ps/journalctl; explicitly
asked author to select only owner stub tests and the new consumer, never full file.

Fresh base `ea81748579ee1732d214ccb75f91d22208ed623d` adds localruntime/PM changes beyond
20bd004; no shutdown-related source or instructions changed in that delta.

## Final independent review

**No blocking finding** in integrated head
`fba7a46a454a004e8fc1966d3bde1dbb2c3c5588` on fresh baseea817485.
Added consumer is33 lines, two parameterized cases, no source-code-text assertions or
runtime OS impersonation. It calls the real alignment function and budget resolver;
the subprocess and cgroup doors are fully synthetic. It does not directly call the
startup logger; logging consequence follows from inspected caller source, not a tested
log capture or real systemd deployment.

Original → preserved cherry-pick identities and stable patch IDs verified independently:

| Original | Cherry-pick | Equal stable patch ID |
|---|---|---|
|799edfd165a916f50f5452e7982134c127ddf587|7d0c2982a539347af3416aec0e68410b8abb325a|0793794ddded73facf8c7054567e223bdc13f2e7|
|c315d15c9b50ca4232598919ccbf485e65c02a67|02b01e4631aece86c6bb6fcaaf060906cd33543a|6342df032ca84284eb4861fcfce07d3513e061b4|
|fad747a451c27ecddfe77fb3e9e707160a6a7464|085db941e7b35784c0dbbb8a97459b31716c0179|74cb2b8f23c64b86072fc63e600f504b67b1f57f|

All author names/emails/dates preserved exactly, including final empty email. New consumer
commit credits happy5318 PR124082 and Borisov-Hermes issue132565. No conflict adaptation or
competing implementation found.

Inspected `/workspace/receipts/batch4-systemd/base-red.log`: **2 failed**, both on incorrect
90s rather than actual210/209s; not infrastructure/collection failures. Inspected
`final-tests.log`: **15 passed**, comprised13 owner helper cases and2 new outer consumer
cases. No reviewer rerun. Worktree clean and commit whitespace check passes.

The runner emits a generic macOS note from file inventory; this is not a claim that the
live macOS diagnostic test ran. Verified author's exact selector:
`-k 'manager or present_load_states or missing_loadstate or absent_load_state or alignment_uses_loaded_system_unit'`
over `test_shutdown_forensics.py` and `test_systemd_timing_alignment_consumer.py` with
`scripts/run_tests.sh -j 2` and the installed test interpreter. That selects only mocked
property helpers and the new consumer; no live diagnostic test matches.
No actual systemctl/service/diagnostic command needed or run by reviewer.
Hosted CI not qualified here. This review approves local downstream integration evidence,
not upstream publication, merge, service installation or restart.

## Additional CUA factual check

Read `/workspace/receipts/batch4-cua.md` and its stored GitHub responses. Confirmed published
ref9846bb67a927ef1320bce577c4bbae1ea2974c12, one successful `validate` check on executable
code019c26f65e0e59f8a8661321d63c5fb1fb105000, zero check runs on the documentation head.
Independently queried run37174772647: completed/success, push event, exact019c26f head,
workflow `CI: Image API`, `.github/workflows/ci-image-api.yml`.
Inspected that exact workflow at019c26f: its focused tests are cua-sandbox Image API tests,
not `scripts/images/tests/test_lag_scope.py`, and it is not the repaired image-lag workflow.
Agree with the receipt's distinction: another hosted job is green, but targeted hosted
qualification remains unobserved. No CUA suite or workflow rerun performed. This check
does not diagnose or clear the original carrier's13 failed checks.
