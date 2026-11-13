---
name: git-subdirectory-extraction
description: Use when moving a repo subfolder to its own repo.
---

# Extract a subdirectory into its own repo (history preserved)

Applies to cases like splitting an app out of dotfiles: split the folder with its history, publish it, then remove it from the host repo safely.

## Procedure

1. Inspect the host repo first:
   - `git status --short | wc -l`, the current branch, and `git status -sb` ahead/behind. A dirty tree or unpushed commits change step 6.
   - `git log --format='%h %ad %s' --date=short -- <dir>` gives the history that will carry over.
   - `git grep -n '<dir>' -- ':!<dir>'` finds references from the host (units, scripts, docs).
   - Inside the dir, grep for absolute paths that point back into the host checkout. Paths to host config still resolve after the split. Paths into the subdir itself (venvs, caches) break, so tell the user about them.
   - Look for untracked or ignored content (`ls -a`, `du -sh`, `find -type f` minus tracked). The final `rm -rf` destroys it.
2. Split into a fresh clone. Never filter the live checkout.
   ```sh
   git clone -q --no-local <host> /workspace/<name> && cd /workspace/<name>
   git checkout -q <working-branch>
   git filter-repo --subdirectory-filter <dir> --force
   git branch -m main
   for b in $(git branch --format='%(refname:short)' | grep -v '^main$'); do git branch -D -q "$b"; done
   git tag | xargs -r git tag -d; git reflog expire --expire=now --all && git gc -q --prune=now
   ```
   `--no-local` stops the clone from hardlinking objects. The clone imports every host branch, so delete them or the new repo carries unrelated branches.
3. Add a short README: what the app is, how to run it, where it was split from, and any remaining coupling to the host. Commit as the user (noreply email).
4. Scan the history for secrets before publishing: `gitleaks git .` if installed, otherwise grep `git log -p --all` for key/token/password assignments.
5. Publish with `gh repo create <owner>/<name> --private --source . --remote origin --push --description ...`. Default to private and mention that switching to public is one command. Verify with `gh repo view ... --json url,visibility` and `git ls-remote origin main` matching the local HEAD.
6. Remove the dir from the host:
   ```sh
   git rm -r -q <dir>; rm -rf <dir>
   git commit -q -m "<dir>: move to <owner>/<name> (history preserved via filter-repo)" -- <dir>
   ```
   Use the pathspec on `commit` so the user's other uncommitted edits stay out of the commit.
   Do not push the host branch on your own when it already carries unpushed commits. List them (`git log origin/<b>..<b>`) and get a go-ahead. If the user guesses what those commits are, check the guess against the log before acting on it.

## Report

Give the new repo URL and visibility, the commit count carried over, the host removal commit, whether the host was pushed, and leftover couplings (config that stays in the host, broken self-paths).
