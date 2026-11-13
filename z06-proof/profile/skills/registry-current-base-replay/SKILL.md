---
name: registry-current-base-replay
description: Use when replaying a conflicted canonical registry PR.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, registry, preservation, testing]
    related_skills: [upstream-contribution, test-driven-development]
---

# Canonical registry replay

## When to Use

Use for a local-only current-base replay of an existing registry carrier, preserving newer entries and original authorship.

- Refresh the full existing carrier, original commit, current default head, project claims and canonical policy before creating a local candidate. If an active owner is repairing the same mechanism, qualify their artifact rather than compete.
- Pin current main in an isolated store or worktree. Preserve owner refs and default refs; local replay permission is not remote rewrite permission.
- Run the exact existing topology test command and official JSON Schema with date formats before edits. Add a routing assertion to the existing test file and require absence-specific RED before replaying registration.
- Replay only the original project object and required district. Compare the whole expected document, not a whitelist of known fields; remove only exact inserted byte sequences and require byte-for-byte baseline reconstruction. This preserves unknown metadata, canonical City fields, new projects and formatting.
- Validate supplemental examples against the official schema before routing them. Canonical City fixtures require name and purpose; districts require name and function. Exercise unknown-field tolerance through the actual consumer without adding a second operational registry.
- Preserve original Git author/date and genuine existing trailers. Separate newly authored tests into an agent-attributed commit. Git commit -C may add a terminal newline to a message originally lacking one; compare raw objects and disclose normalization instead of asserting byte identity.
- Deliver the original commit, pinned base and candidate refs in a standalone bundle. Fetch the restore into a distinct non-checked-out ref—even an unborn checked-out branch rejects a direct fetch—then checkout, fsck, verify tree and execute gates anew.
- Independently restore the immutable bundle into a new object store before reviewing a replay. Re-derive inserted byte ranges from the complete baseline/head comparison, reject replacement or deletion ranges, and require exact baseline reconstruction in addition to full-object equality. Distinguish older shared policy-registry snapshots from the pinned preservation base; equal policy documents do not establish equal registry revisions.
- For independent RED evidence, overlay only the new test onto a pristine baseline snapshot and require its explicit missing-registration assertion while every original case passes. Run mutations in scratch copies and byte-restore/retest after each; a missing district may fail several existing consumer tests, so do not attribute all failures to the new regression.
- Keep a replay's missing original-head ancestry explicit. An existing-carrier update would be non-fast-forward and requires explicit owner authorization plus a fresh exact-head lease; an unsent body is not permission. Read back protected default-head and policy/registry bytes before completion.
- For an ancestry-preserving no-merge continuation, replay each missing main commit onto the original carrier and retain separate provenance rather than copying the entire main tree into a bulk commit. Compare every intermediate registry, with only the original registration removed, against that replay's source revision; preserve unrelated blobs and modes. Prefer direct conflict-resolved replays over a redundant registration revert/reapply when both yield the same required tree.
- Prove carrier fast-forwardability and integration mergeability separately. Cherry-picking main preserves content, not its ancestry. If main is not an ancestor and the exact required final tree still conflicts under `git merge-tree --write-tree MAIN CANDIDATE`, adding revert/replay commits cannot fix the unchanged merge-base/main/final-tree inputs. Retain a local content-qualified bundle but explicitly hold integration; do not claim a no-force push resolves the PR. An experimentally executed revert/replay alternative can confirm the same conflict without creating any merge commit.
- Review replayed commit messages as well as source. Relative phrases such as 'preceding commit' can become false after rearranging history; correct only unpublished metadata while retaining the original source SHA and author, then refreeze, restore, test and independently review the final object. A source-review PASS must remain separate from publication holds and must fail closed when the verdict contains unresolved security or logic findings.
