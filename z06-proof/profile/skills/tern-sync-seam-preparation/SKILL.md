---
name: tern-sync-seam-preparation
description: Use when preparing Tern preview sync and upstream seams.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, tern, hermes, qualification]
---

# Tern sync and seam preparation

## When to Use

Use for fork-only preview-to-main integration candidates and bounded upstream-base Tern adapter drafts.

Prepare two separate fork-only candidates; never confuse permission to prepare a draft with permission to merge main or post upstream.

1. Read the current fork RFC promotion policy and exact upstream review comment. Preserve preview history and peer worktrees. Create owned worktrees from current fork main and current upstream main, respectively.
2. Inspect remote fetch refspecs. Narrow/shallow worktrees may fetch a named branch into FETCH_HEAD without updating `origin/main`. Fetch explicit `refs/heads/NAME:refs/remotes/origin/NAME`, verify full SHAs, and use `--no-tags` when fetching only upstream main.
3. Merge preview without committing on the sync branch. Persist the complete unmerged path list before resolution. Categorize every conflict and also review auto-merged shared launchers, generated contracts, Ink sources and docs. Keep current main's non-Tern behavior; do not accept old shared files wholesale.
4. Regenerate shared contracts from the Python generator, not manual conflict edits. If an explicitly supplied Python interpreter imports incompatible native packages, remove inherited PYTHONPATH before diagnosing/installing dependencies. Run the canonical test wrapper with the specified HERMES_PYTHON.
5. Use the supplied Node executable and dependency-link helper. Build the owned hermes-ink workspace before Ink renderer tests; a linked donor's node_modules does not provide the new worktree's generated dist. Never mutate the dependency donor.
6. Keep upstream scope bounded. A native composer adapter can reuse the existing Ink submission/history/runtime path without importing the full preview frontend. Specify activation precedence, default off, multiplexer/noTTY guards and exit-75-only fallback. Prefer config settings and existing SDK overrides to introducing new HERMES_* behavior variables.
7. Bind native actions to live owner, execution, readiness, busy, modal and draft revisions. Rotate node ids and invalidate retained handlers before send. Send the complete buffered multiline text once through the existing dispatcher. Do not advertise native undo without implementation.
8. Prove SDK negotiation/ACK behavior with actual SDK fixture traffic, including credits=1, many coalesced views and duplicate ACKs. Label fixtures separately from real-host qualification. Test built no-hello entry in a private pseudo-TTY and verify exit 75 before session files are created.
9. Compare unexpected full-suite failures on a pristine archive of the exact base using the same dependency donor and Node binary. Document baseline failures; do not silently waive them as green or broaden the patch to unrelated repairs.
10. Publish explicit fork refs only. Use a dated fork base branch pinned to upstream main for the seam comparison; create both PRs as drafts. Read back remote SHAs, base/head repository metadata, draft state and complete PR bodies before reporting success. Leave native E2E, maintainer approval and main promotion as separate gates.
