# Batch 3 H1: #132565 is existing owned systemd work

Disposition: **no new implementation or duplicate test run**. Published `lane/h2-gateway` at `40b59b21440c6e9c723c49e4f74dfbaf019b455d` remains unchanged; no new worktree.

## Exact current-source evidence

Fresh issue https://github.com/NousResearch/hermes-agent/issues/132565 reports that a nonexistent user-manager unit returns default `TimeoutStopUSec=90s` with rc0, hiding the loaded system-manager unit's 210s timeout.

Fetched current upstream `20bd00439cfc2e8d6d296f28fba0cdeeb6cdda49` still has the user-first, timeout-only query at `gateway/shutdown_forensics.py:226`: no LoadState test before returning the timeout. The production file blob is `2812c3034020d499c7e5344a6a08a940c8abe24b`, identical to prior base `24b9f0f8c5df5ec6d3d5c10ad9b27c3346bbc925`. Existing owner #124082's diff applies to that exact same production blob. Source and existing test file are unchanged across these two upstream snapshots.

## Existing owner and prior Kevin review

https://github.com/NousResearch/hermes-agent/pull/124082 by happy5318 has head `fad747a451c27ecddfe77fb3e9e707160a6a7464`. It queries LoadState alongside the timeout and falls through on not-found/error without changing user→system precedence. Head commits: `799edfd165a916f50f5452e7982134c127ddf587`, `c315d15c9b50ca4232598919ccbf485e65c02a67`, `fad747a451c27ecddfe77fb3e9e707160a6a7464`.

Kevin already reviewed this exact approach on 2026-10-01:
https://github.com/NousResearch/hermes-agent/pull/124082#issuecomment-5933737019
The API marks this comment `viewerDidAuthor: true`. It approves the narrow LoadState fix and finds no blocker. Another contributor independently exercised six scenarios; the owner reports 20 passed and 1 skip. Those are **historical owner/reviewer reports, not fresh tests executed in this workspace**.

Current query returns zero status check rollups and `mergeStateStatus: UNKNOWN`. Historical owner comments report fork workflow approval required; this receipt does not treat that historical diagnosis as a current check result.

Other exact or strongly overlapping open owners found: #93913, #108072 (head `a6d7a7a9660c86eb223f7fcc30fa4b543b459e46`), #113750, #121785, #103086, #36766; #54396 addresses scope preference. Issue-number-only search for #132565 returned none, but semantic search exposed this existing ownership.

## Actionable next choice

Reuse the already reviewed #124082 owner path if a maintainer chooses to integrate this class; preserve original authorship and refresh focused tests on that selected candidate at integration time. New #132565 does not justify another competing implementation. No upstream comment, PR, push, systemctl invocation, service/config modification, installation or hosted CI run was performed. Parent concurred with the no-duplicate disposition.
