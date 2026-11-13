---
name: fork-squash-reconciliation
description: Use when reconciling a fork after squash merges.
version: 0.1.0
author: Kevin (kvnloo), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, reconciliation, skills, compatibility]
---

# Reconcile divergent fork histories

## When to Use

A new method or skill branch descends from pre-squash commits, while fork main has unique capabilities or fixes. Especially important when the checkout is also an installed skill symlink.

## Procedure

1. Through `terminal`, record clean/dirty status, original tips, remotes and `git worktree list`. Verify the intended remote base with `git ls-remote`; a feature tracking counter does not establish the correct base.
2. Keep an installed checkout unchanged while working. Create an owned feature branch/worktree from fork main. Merge the old feature with `--no-commit --no-ff` to preserve both histories; do not force, reset or rewrite existing branches.
3. Compare complete source trees, not just conflict markers. Squashes can leave important safety fixes in main even when the old feature appears newer. Resolve method/core documents intentionally; retain newer main helper implementations and tests unless a proven superset replaces them.
4. Account for every main path in a file/fate/reason/destination ledger. Link retained references from the new index. Keep stable public script/schema paths where relocation would break consumers. Distinguish retiring historical policy authority from deleting a capability.
5. Cross-test stateful compatibility modules both ways: old/new implementations against both original suites, in temporary directories outside the checkout. Inspect byte differences; a trailing newline is not a semantic divergence. Preserve old persisted-state formats and document sidecars/migrations explicitly.
6. Run all helper tests plus link/schema/frontmatter lint. Include old documentation in lint rather than suppressing broken paths. Add behavioral coverage for newly retained untested helpers; document supported input limits without pretending those tests prove general visual quality.
7. Verify the upstream license notice and retain attribution. Describe current project identity independently of the GitHub fork badge. Prepare publication commands with explicit `gh pr create --repo OWNER/FORK --base main --head BRANCH`; the implicit fork target can be the upstream parent.
8. Commit only owned changes, verify both parent tips remain ancestors, then detach the temporary worktree to free the new branch. Switch the original clean checkout only after tests pass. Verify the installed symlink resolves to the expected files and frontmatter; preserve the old branch for rollback.

## Pitfalls

- Never equate a merge conflict resolution or a green subset with full capability preservation.
- Historical workflow recipes need explicit current owner/safety precedence; an old default service permission must not silently survive as authority.
- Fork-network detachment is separate authorization. Consult current GitHub documentation: eligible forks may expose Leave fork network, whose metadata-loss warnings matter. Do not promise stars, issues or PR links survive; ask Support before destructive recreation.
- Prepare-only means no push, PR, release or settings edits. A skill branch switch is not remote publication.

## Verification

Require a complete source-file ledger, all test/lint exit codes, compatibility cross-tests, preserved ancestry/license, clean working trees, exact installed version, and an explicit list of remaining external actions. Store receipts outside the repository when they contain host-local paths.
