---
name: git-lineage-recovery
description: Use when recovering local Git commits absent from GitHub.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, recovery, github, worktrees]
    related_skills: [git-evidence-preservation]
---

# Git lineage recovery

## When to Use

Use when the user wants local branches, worktrees, or uncommitted work found and preserved, and wants proof of whether that history is already on a remote. Do not rewrite history.

Read-only inventory stays in `git-evidence-preservation`. This skill starts when the user also authorizes a safety branch and a non-force push of commits that are actually absent.

## Procedure

1. Resolve the real checkout before trusting a named path. `readlink -f` symlinks. A product alias that points at another tree is the same checkout, not a second repo. Run every git read with `GIT_OPTIONAL_LOCKS=0`.

2. Inventory from the repo, not a home-wide `.git` crawl. `git worktree list --porcelain`, `git for-each-ref refs/heads`, `git stash list`, remotes. Record missing worktree paths. Do not prune them, and do not reset, rebase, clean, delete worktrees, drop stashes, or merge.

3. Prove remote presence before creating any recovery branch.
   - `git ls-remote <url> refs/heads/<name>` must equal the local tip SHA for that branch to count as already published. `ls-remote` does not update local refs.
   - `gh api repos/<owner>/<repo>/commits/<sha>` HTTP 200 means the object resolves through that repository's fork network, not that its default branch adopted it. Prove publication with the advertised named ref, and adoption separately with ancestry or exact relevant blob comparisons. HTTP 422 with "No commit found" means the supplied locator does not resolve through that endpoint.
   - `gh repo view <old-name>` that returns a different `full_name` is a rename redirect. Treat both URLs as one repo.
   - Local `origin/*` refs and `git branch -r --contains` are not proof. They can be stale, or they can show the SHA under a different branch name.

4. Rank lineages by commit ancestry and file bytes, not by worktree count. A detached worktree whose HEAD is an ancestor of the published tip, with source files that differ only as the older draft, is superseded WIP. Do not commit those diffs onto a recovery branch. That would regress the tip.

5. If the named tip SHA already matches the remote branch, do not create a duplicate recovery branch and do not push. Report remaining dirty and untracked files. Commit untracked source only when the user asked to commit intended tracked work and the files are source, not generated databases, inventories, evidence logs, build output, or editor backups.

6. If valuable commits are absent from the remote: add a sibling worktree from that exact SHA and commit only there. Do not `git checkout -b` in the canonical worktree — that moves the published checkout off its branch even when the old branch ref is unchanged. Commit only the intended tracked source, push to the user's remote only, no force-push, no merge to main or dev. Push each useful divergent lineage on its own branch. Do not combine them first. Follow-on work reads untracked research from the canonical tree and writes the new branch in the sibling.

7. Run the repo's existing test, typecheck, and build on the canonical worktree after the inventory decision, without staging. If there is no typecheck script, use the existing `tsconfig.json` (`tsc --noEmit`) and say the npm script was absent. Record exit codes and the summary line. Confirm HEAD did not move.

## Transfer-artifact recovery

- When an exact prepared SHA is required, locate the original object store, Git bundle, or archive retaining `.git` before rebuilding files. A format-patch replay generally changes committer metadata and does not establish preservation of the requested commit; verify the recovered object with `git cat-file` and `git rev-parse` before publication.
- Treat a pasted success report as a lead, not the source artifact. Search bounded checkout/worktree roots, transfer/download locations and the actual profile's read-only history; exclude current-task echoes when determining whether an earlier workspace path or attachment exists. Inspect archive manifests before extraction, and keep unrelated experiment bundles out of the recovery.
- If the user explicitly authorizes an original standalone format-patch as an alternative to the missing commit object, verify the supplied cryptographic hash before application. A Library identifier is a retrieval lead, not downloadable bytes; when no connector or local artifact exists, report that prerequisite rather than recreating a patch from the description. Keep reverse/forward applicability and patch-equivalence unassessed until the real artifact is available. Preserve its author metadata, and bind review/tests/CI to the actual replayed final SHA rather than claiming that git am preserved the original commit hash.
- Compare local branches against the freshly advertised union of remote heads as well as same-name tips. A branch can be many commits ahead of its named remote while fewer commits are unpublished anywhere. Record missing local remote objects as a coverage limitation, and preserve concurrent wiring/receipt/CLI changes rather than importing a whole experimental stack.
- When the exact object is absent locally and GitHub returns `422 No commit found`, record the checked roots, missing ref, exact-SHA CI response and artifact gap. Do not recreate a lookalike branch or claim tests/review on unavailable source; request the original testing workspace or a bundle retaining the commit.
- Trace a surviving evidence-only branch through its provenance log to the tested source SHA, not its documentation tip or a later review's summary counts. Earlier native failures prove the baseline, not a missing repair's GREEN result. Check receipt-named workspace paths for host migration, and distinguish a missing source/artifact gate from an actual publication-approval hold.
- Deduplicate discovered worktrees by resolved common Git directory before probing missing objects, and print aggregate counts plus unique object-store paths rather than the complete worktree inventory. Save the full bounded inventory separately so output truncation cannot hide a second store or an unresolved path.
- Validate object type and repository provenance before expanding a supplied short commit prefix. A cross-store scan can find an unrelated tree or blob with the same prefix; reject that collision rather than reporting a recovered commit. Verify the required tree independently when the brief supplies one.
- Read original parent headers with `git cat-file commit SHA` in shallow evidence stores; pretty-format `%P` hides shallow-boundary parents and must not be interpreted as an originally root commit. Verify raw object identity separately from API metadata and leave existing checkouts untouched.
- Separate recovered normalized execution logs from declared hashes of missing original streams. Recompute hashes from raw bytes, bind production/test hashes to the candidate, and label owner-attested tested-tree equality separately when the original tested commit is unavailable; a matching receipt is not a fresh test run.
- Do not infer fork absence from an owner search that omitted `fork:true`; confirm the expected fork directly through repository metadata, including parent/source identities and advertised heads. When a cached local inventory is topic-filtered, broaden once through its unfiltered seed and bounded roots, deduplicate common stores, and reuse previous negative probes rather than repeating only the filtered stores.

## Report

Canonical path, branch, full SHA, remote branch URL, commits newly pushed (zero if the tip was already remote), test results, remaining dirty and untracked files, and any other branches whose SHAs are still absent from GitHub. Do not start the next feature.

## Pitfalls

- Do not treat a dirty side worktree as a newer lineage because its files differ from the tip. Difference plus an ancestor HEAD means the draft was left behind when the later commit landed on the main worktree.
- Do not absorb a generated database or audit dump just because it is the only tracked modification on the canonical worktree.
- Do not check out a recovery or follow-on branch in the canonical worktree. A sibling worktree from the exact SHA keeps that checkout on the published branch while the new commit is made elsewhere.
- A commit that `git branch -r --contains` misses can still be on GitHub under another ref. Check the SHA with the commits API before calling a branch local-only, and check the named branch with `ls-remote` before calling a tip unpublished.
